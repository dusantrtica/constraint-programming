from __future__ import annotations

import resource
import time
from typing import Optional

from ortools.sat.python import cp_model

from .common import (
    NUM_DAYS,
    SLOTS_PER_DAY,
    TOTAL_SLOTS,
    Assignment,
    SolverConfig,
    SolverResult,
)
from .data import Classroom, Session, get_eligible_rooms


class _FirstSolutionCb(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        super().__init__()
        self.first_solution_time = None
        self._start = time.perf_counter()

    def on_solution_callback(self):
        if self.first_solution_time is None:
            self.first_solution_time = time.perf_counter() - self._start


def solve_cp(
    sessions: list[Session],
    classrooms: list[Classroom],
    config: Optional[SolverConfig] = None,
) -> SolverResult:
    if config is None:
        config = SolverConfig()

    if not sessions:
        return SolverResult(status="optimal", objective_value=0)

    model = cp_model.CpModel()
    num_rooms = len(classrooms)

    eligible_map: dict[int, list[int]] = {}
    for s in sessions:
        elig = get_eligible_rooms(s, classrooms)
        if not elig:
            return SolverResult(status="infeasible")
        eligible_map[s.id] = elig

    # -- decision variables --------------------------------------------------
    day_var: dict[int, cp_model.IntVar] = {}
    slot_var: dict[int, cp_model.IntVar] = {}
    room_var: dict[int, cp_model.IntVar] = {}
    flat_time_var: dict[int, cp_model.IntVar] = {}
    room_time_var: dict[int, cp_model.IntVar] = {}

    for s in sessions:
        sid = s.id
        elig = eligible_map[sid]

        day_var[sid] = model.NewIntVar(0, NUM_DAYS - 1, f"d_{sid}")
        slot_var[sid] = model.NewIntVar(0, SLOTS_PER_DAY - 1, f"s_{sid}")
        room_var[sid] = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(elig), f"r_{sid}"
        )

        flat_time_var[sid] = model.NewIntVar(0, TOTAL_SLOTS - 1, f"ft_{sid}")
        model.Add(flat_time_var[sid] == day_var[sid] * SLOTS_PER_DAY + slot_var[sid])

        rt_vals = [r * TOTAL_SLOTS + t for r in elig for t in range(TOTAL_SLOTS)]
        room_time_var[sid] = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(rt_vals), f"rt_{sid}"
        )
        model.Add(
            room_time_var[sid] == room_var[sid] * TOTAL_SLOTS + flat_time_var[sid]
        )

    # -- hard constraints -----------------------------------------------------
    # 1) no room double-booking
    model.AddAllDifferent(list(room_time_var.values()))

    # 2) no student-group clash (all sessions of a cohort at distinct timeslots)
    cohorts: dict[tuple, list[int]] = {}
    for s in sessions:
        cohorts.setdefault(s.cohort, []).append(s.id)

    for sids in cohorts.values():
        if len(sids) > 1:
            model.AddAllDifferent([flat_time_var[sid] for sid in sids])

    # -- soft constraints / objective -----------------------------------------
    is_on_day: dict[tuple[int, int], cp_model.IntVar] = {}
    for s in sessions:
        for d in range(NUM_DAYS):
            b = model.NewBoolVar(f"od_{s.id}_{d}")
            model.Add(day_var[s.id] == d).OnlyEnforceIf(b)
            model.Add(day_var[s.id] != d).OnlyEnforceIf(b.Not())
            is_on_day[(s.id, d)] = b

    max_sessions = max(len(sids) for sids in cohorts.values())
    max_load = model.NewIntVar(0, max_sessions, "max_load")
    gap_terms: list[cp_model.IntVar] = []

    for cohort_key, sids in cohorts.items():
        for d in range(NUM_DAYS):
            day_bools = [is_on_day[(sid, d)] for sid in sids]

            count = model.NewIntVar(0, len(sids), f"cnt_{cohort_key}_{d}")
            model.Add(count == sum(day_bools))
            model.Add(max_load >= count)

            active = model.NewBoolVar(f"act_{cohort_key}_{d}")
            model.Add(count >= 1).OnlyEnforceIf(active)
            model.Add(count == 0).OnlyEnforceIf(active.Not())

            first_s = model.NewIntVar(0, SLOTS_PER_DAY - 1, f"f_{cohort_key}_{d}")
            last_s = model.NewIntVar(0, SLOTS_PER_DAY - 1, f"l_{cohort_key}_{d}")

            for sid in sids:
                model.Add(first_s <= slot_var[sid]).OnlyEnforceIf(is_on_day[(sid, d)])
                model.Add(last_s >= slot_var[sid]).OnlyEnforceIf(is_on_day[(sid, d)])

            model.Add(first_s == SLOTS_PER_DAY - 1).OnlyEnforceIf(active.Not())
            model.Add(last_s == 0).OnlyEnforceIf(active.Not())

            gap = model.NewIntVar(0, SLOTS_PER_DAY, f"g_{cohort_key}_{d}")
            model.Add(
                gap >= last_s - first_s + 1 - count
            ).OnlyEnforceIf(active)
            model.Add(gap == 0).OnlyEnforceIf(active.Not())

            gap_terms.append(gap)

    model.Minimize(
        config.gap_weight * sum(gap_terms) + config.balance_weight * max_load
    )

    # -- solve ----------------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.time_limit_seconds
    solver.parameters.num_workers = 8

    callback = _FirstSolutionCb()

    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    t0 = time.perf_counter()
    status_code = solver.Solve(model, callback)
    elapsed = time.perf_counter() - t0
    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mem = max(0, rss_after - rss_before)

    status_map = {
        cp_model.OPTIMAL: "optimal",
        cp_model.FEASIBLE: "feasible",
        cp_model.INFEASIBLE: "infeasible",
        cp_model.MODEL_INVALID: "invalid",
        cp_model.UNKNOWN: "unknown",
    }

    result = SolverResult(
        status=status_map.get(status_code, "unknown"),
        solve_time_seconds=elapsed,
        time_to_first_solution=callback.first_solution_time or 0.0,
        peak_memory_bytes=peak_mem,
        num_variables=len(model.Proto().variables),
        num_constraints=len(model.Proto().constraints),
    )

    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        obj = solver.ObjectiveValue()
        bound = solver.BestObjectiveBound()
        result.objective_value = obj
        result.optimality_gap = abs(obj - bound) / max(abs(obj), 1e-10)
        result.assignments = [
            Assignment(
                session_id=s.id,
                day=solver.Value(day_var[s.id]),
                slot=solver.Value(slot_var[s.id]),
                room_index=solver.Value(room_var[s.id]),
            )
            for s in sessions
        ]

    return result
