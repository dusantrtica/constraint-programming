"""MIP formulation for class scheduling using OR-Tools linear solver (SCIP).

Uses the same hard/soft constraints as the CP solver but models them as a
mixed-integer program with binary decision variables."""

from __future__ import annotations

import resource
import time
from typing import Optional

from ortools.linear_solver import pywraplp

from .common import (
    NUM_DAYS,
    SLOTS_PER_DAY,
    Assignment,
    SolverConfig,
    SolverResult,
)
from .data import Classroom, Session, get_eligible_rooms

_SOLVER_ID = "SCIP"


def solve_mip(
    sessions: list[Session],
    classrooms: list[Classroom],
    config: Optional[SolverConfig] = None,
) -> SolverResult:
    if config is None:
        config = SolverConfig()

    if not sessions:
        return SolverResult(status="optimal", objective_value=0)

    S = SLOTS_PER_DAY

    eligible_map: dict[int, list[int]] = {}
    sessions_for_room: dict[int, list[Session]] = {
        r: [] for r in range(len(classrooms))
    }
    for s in sessions:
        elig = get_eligible_rooms(s, classrooms)
        if not elig:
            return SolverResult(status="infeasible")
        eligible_map[s.id] = elig
        for r in elig:
            sessions_for_room[r].append(s)

    cohorts: dict[tuple, list[Session]] = {}
    for s in sessions:
        cohorts.setdefault(s.cohort, []).append(s)

    solver = pywraplp.Solver.CreateSolver(_SOLVER_ID)
    if solver is None:
        return SolverResult(status="error")

    solver.SetTimeLimit(config.time_limit_seconds * 1000)
    inf = solver.infinity()

    # -- binary decision variables x[session, day, slot, room] ----------------
    x: dict[tuple[int, int, int, int], pywraplp.Variable] = {}
    for s in sessions:
        for d in range(NUM_DAYS):
            for sl in range(S):
                for r in eligible_map[s.id]:
                    x[(s.id, d, sl, r)] = solver.BoolVar(
                        f"x_{s.id}_{d}_{sl}_{r}"
                    )

    # -- hard constraints -----------------------------------------------------
    # 1) each session assigned exactly once
    for s in sessions:
        solver.Add(
            sum(
                x[(s.id, d, sl, r)]
                for d in range(NUM_DAYS)
                for sl in range(S)
                for r in eligible_map[s.id]
            )
            == 1
        )

    # 2) no room double-booking
    for r in range(len(classrooms)):
        r_sess = sessions_for_room[r]
        if len(r_sess) < 2:
            continue
        for d in range(NUM_DAYS):
            for sl in range(S):
                terms = [
                    x[(s.id, d, sl, r)]
                    for s in r_sess
                    if (s.id, d, sl, r) in x
                ]
                if len(terms) > 1:
                    solver.Add(sum(terms) <= 1)

    # 3) no student-group clash
    for cohort_sessions in cohorts.values():
        if len(cohort_sessions) < 2:
            continue
        for d in range(NUM_DAYS):
            for sl in range(S):
                terms = [
                    x[(s.id, d, sl, r)]
                    for s in cohort_sessions
                    for r in eligible_map[s.id]
                    if (s.id, d, sl, r) in x
                ]
                if len(terms) > 1:
                    solver.Add(sum(terms) <= 1)

    # -- soft constraints / objective -----------------------------------------
    # y[cohort, day, slot] = 1 if cohort has a class there
    y: dict[tuple, pywraplp.Variable] = {}
    for cohort_key, cohort_sessions in cohorts.items():
        for d in range(NUM_DAYS):
            for sl in range(S):
                yvar = solver.BoolVar(f"y_{cohort_key}_{d}_{sl}")
                terms = [
                    x[(s.id, d, sl, r)]
                    for s in cohort_sessions
                    for r in eligible_map[s.id]
                    if (s.id, d, sl, r) in x
                ]
                if terms:
                    solver.Add(yvar == sum(terms))
                else:
                    solver.Add(yvar == 0)
                y[(cohort_key, d, sl)] = yvar

    max_load = solver.IntVar(0, max(len(v) for v in cohorts.values()), "max_load")
    gap_vars: list[pywraplp.Variable] = []

    for cohort_key, cohort_sessions in cohorts.items():
        n_sess = len(cohort_sessions)
        for d in range(NUM_DAYS):
            cnt = solver.IntVar(0, n_sess, f"cnt_{cohort_key}_{d}")
            first = solver.NumVar(0, S - 1, f"f_{cohort_key}_{d}")
            last = solver.NumVar(0, S - 1, f"l_{cohort_key}_{d}")
            active = solver.BoolVar(f"act_{cohort_key}_{d}")
            gap = solver.NumVar(0, S, f"gap_{cohort_key}_{d}")

            day_y = [y[(cohort_key, d, sl)] for sl in range(S)]
            solver.Add(cnt == sum(day_y))

            solver.Add(active <= cnt)
            solver.Add(cnt <= n_sess * active)

            for sl in range(S):
                yv = y[(cohort_key, d, sl)]
                solver.Add(first <= sl + (S - 1) * (1 - yv))
                solver.Add(last >= sl * yv)

            solver.Add(gap >= last - first + 1 - cnt - S * (1 - active))

            solver.Add(max_load >= cnt)
            gap_vars.append(gap)

    solver.Minimize(
        config.gap_weight * sum(gap_vars) + config.balance_weight * max_load
    )

    # -- solve ----------------------------------------------------------------
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    t0 = time.perf_counter()
    status_code = solver.Solve()
    elapsed = time.perf_counter() - t0
    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mem = max(0, rss_after - rss_before)

    status_map = {
        pywraplp.Solver.OPTIMAL: "optimal",
        pywraplp.Solver.FEASIBLE: "feasible",
        pywraplp.Solver.INFEASIBLE: "infeasible",
        pywraplp.Solver.UNBOUNDED: "unbounded",
        pywraplp.Solver.NOT_SOLVED: "not_solved",
        pywraplp.Solver.ABNORMAL: "error",
    }

    result = SolverResult(
        status=status_map.get(status_code, "unknown"),
        solve_time_seconds=elapsed,
        time_to_first_solution=elapsed,
        peak_memory_bytes=peak_mem,
        num_variables=solver.NumVariables(),
        num_constraints=solver.NumConstraints(),
    )

    if status_code in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        result.objective_value = solver.Objective().Value()
        best_bound = solver.Objective().BestBound()
        obj_val = result.objective_value
        if abs(obj_val) > 1e-10:
            result.optimality_gap = abs(obj_val - best_bound) / abs(obj_val)
        else:
            result.optimality_gap = 0.0

        assignments: list[Assignment] = []
        for s in sessions:
            for d in range(NUM_DAYS):
                for sl in range(S):
                    for r in eligible_map[s.id]:
                        v = x[(s.id, d, sl, r)]
                        if v.solution_value() > 0.5:
                            assignments.append(
                                Assignment(
                                    session_id=s.id,
                                    day=d,
                                    slot=sl,
                                    room_index=r,
                                )
                            )
        result.assignments = assignments

    return result
