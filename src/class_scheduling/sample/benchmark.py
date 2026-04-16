"""
Benchmark harness for comparing CP-SAT vs MIP/SCIP solvers on class scheduling.

Runs both solvers on identical inputs of varying sizes, collects quantitative
metrics (model size, time, memory, solution quality), validates solutions,
and prints a structured comparison report.

Usage:
    python -m src.class_scheduling.sample.benchmark
    python -m src.class_scheduling.sample.benchmark --json report.json
"""

import argparse
import gc
import json
import math
import resource
import time
import tracemalloc
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from ortools.linear_solver import pywraplp
from ortools.sat.python import cp_model

from src.class_scheduling.sample.cp_solver import SimpleCPSolver
from src.class_scheduling.sample.data import GROUP_SIZE, Session, generate_sessions
from src.class_scheduling.sample.mip_solver import SimpleMIPSolver
from src.class_scheduling.sample.model import (
    Classroom,
    Course,
    Department,
    Location,
    Quota,
    SchedulingInput,
    Settings,
    StudentsEnrolled,
)

# ---------------------------------------------------------------------------
# 1. Scaled input generation
# ---------------------------------------------------------------------------

COURSE_NAMES = [
    "Analiza", "Algebra", "Geometrija", "Programiranje",
    "Baze podataka", "Operativni sistemi", "Mreze", "Vestacka inteligencija",
    "Statistika", "Diskretna matematika", "Numericki metodi", "Logika",
    "Algoritmi", "Strukture podataka", "Softversko inzenjerstvo",
    "Racunarska grafika",
]


def generate_scaled_input(
    n_departments: int = 1,
    students_per_dep: int = 30,
    courses_per_dep: int = 2,
    n_rooms: int = 3,
    n_computer_rooms: int = 1,
    n_days: int = 5,
    hours_per_day: int = 6,
    theory_quota: int = 2,
    practice_quota: int = 2,
    computer_course_ratio: float = 0.3,
) -> SchedulingInput:
    """Build a SchedulingInput of configurable size without reading JSON."""

    day_names = ["Ponedeljak", "Utorak", "Sreda", "Cetvrtak", "Petak",
                 "Subota", "Nedelja"][:n_days]
    start_hour = 8
    end_hour = start_hour + hours_per_day

    settings = Settings(
        working_days=day_names,
        start_hour=start_hour,
        end_hour=end_hour,
        duration=1,
    )

    locations = [Location(id=1, name="Trg")]

    classrooms = []
    for i in range(n_rooms):
        has_computers = i < n_computer_rooms
        classrooms.append(
            Classroom(
                id=i + 1,
                name=f"Room_{i + 1}",
                loc_id=1,
                has_computers=has_computers,
                capacity=40,
            )
        )

    departments = []
    courses = []
    students_enrolled = []
    course_id = 1

    for dep_idx in range(n_departments):
        dep_id = dep_idx + 1
        departments.append(Department(id=dep_id, name=f"Dep_{dep_id}"))
        students_enrolled.append(
            StudentsEnrolled(dep_id=dep_id, semester=1, count=students_per_dep)
        )
        for c_idx in range(courses_per_dep):
            name = COURSE_NAMES[c_idx % len(COURSE_NAMES)]
            needs_pc = c_idx < int(courses_per_dep * computer_course_ratio)
            courses.append(
                Course(
                    id=course_id,
                    name=f"{name} (D{dep_id})",
                    semester=1,
                    dep_id=dep_id,
                    quota=Quota(theory=theory_quota, practice=practice_quota),
                    needs_computers=needs_pc,
                )
            )
            course_id += 1

    return SchedulingInput(
        settings=settings,
        locations=locations,
        classrooms=classrooms,
        departments=departments,
        courses=courses,
        students_enrolled=students_enrolled,
    )


# ---------------------------------------------------------------------------
# 2. BenchmarkResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    solver_name: str
    scale_label: str
    num_sessions: int
    num_variables: int
    num_constraints: int
    construction_time_s: float
    solve_time_s: float
    total_time_s: float
    peak_memory_kb: float
    model_memory_kb: float
    status: str
    objective_value: Optional[float]
    optimality_gap: Optional[float]
    solution_valid: Optional[bool]


# ---------------------------------------------------------------------------
# 3. Solution validator
# ---------------------------------------------------------------------------

def validate_solution(
    sessions: List[Session],
    variables: List[dict],
    classrooms: List[Classroom],
) -> tuple:
    """
    Check that a solution satisfies all hard constraints.
    Returns (is_valid, list_of_violations).
    """
    violations = []

    if len(variables) != len(sessions):
        violations.append(
            f"Session count mismatch: {len(sessions)} sessions vs "
            f"{len(variables)} assignments"
        )
        return False, violations

    room_time_set: set = set()
    group_time_map: Dict[str, set] = defaultdict(set)
    computer_room_indices = {
        i for i, room in enumerate(classrooms) if room.has_computers
    }

    for s, (session, v) in enumerate(zip(sessions, variables)):
        d, h, r = v["day"], v["hour"], v["room"]

        rt_key = (d, h, r)
        if rt_key in room_time_set:
            violations.append(
                f"Room-time collision at day={d} hour={h} room={r} (session {s})"
            )
        room_time_set.add(rt_key)

        gt_key = (d, h)
        if gt_key in group_time_map[session.group_id]:
            violations.append(
                f"Group-time collision: group={session.group_id} "
                f"day={d} hour={h} (session {s})"
            )
        group_time_map[session.group_id].add(gt_key)

        if session.needs_computers and r not in computer_room_indices:
            violations.append(
                f"Computer constraint violated: session {s} needs computers "
                f"but room {r} has none"
            )

    is_valid = len(violations) == 0
    return is_valid, violations


# ---------------------------------------------------------------------------
# 4. Benchmark runner for each solver type
# ---------------------------------------------------------------------------

CP_STATUS_NAMES = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}

MIP_STATUS_NAMES = {
    pywraplp.Solver.OPTIMAL: "OPTIMAL",
    pywraplp.Solver.FEASIBLE: "FEASIBLE",
    pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
    pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
    pywraplp.Solver.ABNORMAL: "ABNORMAL",
    pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
}


def _get_peak_rss_kb() -> float:
    """Peak resident set size in KB (macOS ru_maxrss is bytes)."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / 1024


def benchmark_cp(
    scheduling_input: SchedulingInput,
    scale_label: str,
    max_time: float = 60.0,
) -> BenchmarkResult:
    gc.collect()
    tracemalloc.start()
    mem_before = tracemalloc.take_snapshot()

    t0 = time.perf_counter()
    solver = SimpleCPSolver(
        scheduling_input, max_time_seconds=max_time, log_progress=False
    )
    t_construct = time.perf_counter()

    mem_after_construct = tracemalloc.take_snapshot()

    num_vars = len(solver.model.Proto().variables)
    num_constraints = len(solver.model.Proto().constraints)

    status_code = solver.solve()
    t_solve = time.perf_counter()

    tracemalloc.stop()

    status = CP_STATUS_NAMES.get(status_code, str(status_code))

    objective_value = None
    gap = None
    solution_valid = None

    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        objective_value = solver.solver.ObjectiveValue()
        best_bound = solver.solver.BestObjectiveBound()
        if objective_value != 0:
            gap = abs(objective_value - best_bound) / abs(objective_value)
        else:
            gap = 0.0

        variables = solver.get_solution_variables()
        valid, _ = validate_solution(
            solver.sessions, variables, scheduling_input.classrooms
        )
        solution_valid = valid

    model_stats = mem_after_construct.compare_to(mem_before, "lineno")
    model_mem_kb = sum(s.size_diff for s in model_stats) / 1024

    return BenchmarkResult(
        solver_name="CP-SAT",
        scale_label=scale_label,
        num_sessions=len(solver.sessions),
        num_variables=num_vars,
        num_constraints=num_constraints,
        construction_time_s=round(t_construct - t0, 4),
        solve_time_s=round(t_solve - t_construct, 4),
        total_time_s=round(t_solve - t0, 4),
        peak_memory_kb=round(_get_peak_rss_kb(), 1),
        model_memory_kb=round(model_mem_kb, 1),
        status=status,
        objective_value=objective_value,
        optimality_gap=round(gap, 6) if gap is not None else None,
        solution_valid=solution_valid,
    )


def benchmark_mip(
    scheduling_input: SchedulingInput,
    scale_label: str,
    max_time: float = 60.0,
) -> BenchmarkResult:
    gc.collect()
    tracemalloc.start()
    mem_before = tracemalloc.take_snapshot()

    t0 = time.perf_counter()
    solver = SimpleMIPSolver(scheduling_input, max_time_seconds=max_time)
    t_construct = time.perf_counter()

    mem_after_construct = tracemalloc.take_snapshot()

    num_vars = solver.solver.NumVariables()
    num_constraints = solver.solver.NumConstraints()

    status_code = solver.solve()
    t_solve = time.perf_counter()

    tracemalloc.stop()

    status = MIP_STATUS_NAMES.get(status_code, str(status_code))

    objective_value = None
    gap = None
    solution_valid = None

    if status_code in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        objective_value = solver.solver.Objective().Value()
        best_bound = solver.solver.Objective().BestBound()
        if objective_value != 0:
            gap = abs(objective_value - best_bound) / abs(objective_value)
        else:
            gap = 0.0

        variables = solver.get_solution_variables()
        valid, _ = validate_solution(
            solver.sessions, variables, scheduling_input.classrooms
        )
        solution_valid = valid

    model_stats = mem_after_construct.compare_to(mem_before, "lineno")
    model_mem_kb = sum(s.size_diff for s in model_stats) / 1024

    return BenchmarkResult(
        solver_name="MIP/SCIP",
        scale_label=scale_label,
        num_sessions=len(solver.sessions),
        num_variables=num_vars,
        num_constraints=num_constraints,
        construction_time_s=round(t_construct - t0, 4),
        solve_time_s=round(t_solve - t_construct, 4),
        total_time_s=round(t_solve - t0, 4),
        peak_memory_kb=round(_get_peak_rss_kb(), 1),
        model_memory_kb=round(model_mem_kb, 1),
        status=status,
        objective_value=objective_value,
        optimality_gap=round(gap, 6) if gap is not None else None,
        solution_valid=solution_valid,
    )


# ---------------------------------------------------------------------------
# 5. Scale definitions and benchmark matrix
# ---------------------------------------------------------------------------

SCALE_CONFIGS = {
    "small": dict(
        n_departments=1, students_per_dep=30, courses_per_dep=2,
        n_rooms=3, n_computer_rooms=1, n_days=5, hours_per_day=6,
        theory_quota=2, practice_quota=2, computer_course_ratio=0.5,
    ),
    "medium": dict(
        n_departments=2, students_per_dep=90, courses_per_dep=4,
        n_rooms=8, n_computer_rooms=3, n_days=5, hours_per_day=10,
        theory_quota=3, practice_quota=3, computer_course_ratio=0.25,
    ),
    "large": dict(
        n_departments=3, students_per_dep=120, courses_per_dep=5,
        n_rooms=12, n_computer_rooms=4, n_days=5, hours_per_day=12,
        theory_quota=3, practice_quota=2, computer_course_ratio=0.2,
    ),
    "xl": dict(
        n_departments=4, students_per_dep=150, courses_per_dep=6,
        n_rooms=15, n_computer_rooms=5, n_days=5, hours_per_day=12,
        theory_quota=2, practice_quota=2, computer_course_ratio=0.17,
    ),
}


def run_benchmark_matrix(
    scales: Optional[List[str]] = None,
    max_time: float = 60.0,
) -> List[BenchmarkResult]:
    if scales is None:
        scales = list(SCALE_CONFIGS.keys())

    results: List[BenchmarkResult] = []

    for scale_label in scales:
        config = SCALE_CONFIGS[scale_label]
        scheduling_input = generate_scaled_input(**config)
        sessions = generate_sessions(scheduling_input, GROUP_SIZE)
        n_sessions = len(sessions)
        n_rooms = len(scheduling_input.classrooms)
        D = len(scheduling_input.settings.working_days)
        H = config["hours_per_day"]

        print(f"\n{'=' * 65}")
        print(
            f"Scale: {scale_label} "
            f"({n_sessions} sessions, {n_rooms} rooms, "
            f"{D} days x {H} hours)"
        )
        print("=" * 65)

        print("  Running CP-SAT...", end="", flush=True)
        cp_result = benchmark_cp(scheduling_input, scale_label, max_time)
        results.append(cp_result)
        print(f" done ({cp_result.status}, {cp_result.total_time_s:.2f}s)")

        print("  Running MIP/SCIP...", end="", flush=True)
        mip_result = benchmark_mip(scheduling_input, scale_label, max_time)
        results.append(mip_result)
        print(f" done ({mip_result.status}, {mip_result.total_time_s:.2f}s)")

        print_comparison_table(cp_result, mip_result)

    return results


# ---------------------------------------------------------------------------
# 6. Report printing
# ---------------------------------------------------------------------------

def _fmt_num(n) -> str:
    if n is None:
        return "N/A"
    if isinstance(n, float):
        if n == int(n):
            return f"{int(n):,}"
        return f"{n:,.4f}"
    return f"{n:,}"


def _fmt_pct(v) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.2f}%"


def _fmt_valid(v) -> str:
    if v is None:
        return "N/A"
    return "PASS" if v else "FAIL"


def print_comparison_table(cp: BenchmarkResult, mip: BenchmarkResult):
    rows = [
        ("Sessions", _fmt_num(cp.num_sessions), _fmt_num(mip.num_sessions)),
        ("Variables", _fmt_num(cp.num_variables), _fmt_num(mip.num_variables)),
        ("Constraints", _fmt_num(cp.num_constraints), _fmt_num(mip.num_constraints)),
        ("Construction time", f"{cp.construction_time_s:.4f}s", f"{mip.construction_time_s:.4f}s"),
        ("Solve time", f"{cp.solve_time_s:.4f}s", f"{mip.solve_time_s:.4f}s"),
        ("Total time", f"{cp.total_time_s:.4f}s", f"{mip.total_time_s:.4f}s"),
        ("Model memory", f"{cp.model_memory_kb:.1f} KB", f"{mip.model_memory_kb:.1f} KB"),
        ("Peak RSS", f"{cp.peak_memory_kb:.0f} KB", f"{mip.peak_memory_kb:.0f} KB"),
        ("Status", cp.status, mip.status),
        ("Objective (max_slot)", _fmt_num(cp.objective_value), _fmt_num(mip.objective_value)),
        ("Optimality gap", _fmt_pct(cp.optimality_gap), _fmt_pct(mip.optimality_gap)),
        ("Solution valid", _fmt_valid(cp.solution_valid), _fmt_valid(mip.solution_valid)),
    ]

    col0_w = max(len(r[0]) for r in rows)
    col1_w = max(len(r[1]) for r in rows)
    col2_w = max(len(r[2]) for r in rows)
    col1_w = max(col1_w, len("CP-SAT"))
    col2_w = max(col2_w, len("MIP/SCIP"))

    header = (
        f"  {'Metric':<{col0_w}}  "
        f"{'CP-SAT':>{col1_w}}  "
        f"{'MIP/SCIP':>{col2_w}}"
    )
    sep = "  " + "-" * (col0_w + col1_w + col2_w + 4)

    print()
    print(header)
    print(sep)
    for label, cp_val, mip_val in rows:
        print(f"  {label:<{col0_w}}  {cp_val:>{col1_w}}  {mip_val:>{col2_w}}")
    print()


def print_summary(results: List[BenchmarkResult]):
    print("\n" + "=" * 65)
    print("THEORETICAL COMPLEXITY COMPARISON")
    print("=" * 65)
    print("""
  CP-SAT (Constraint Programming):
    - Variables:   O(S) -- 5 integer variables per session
    - Constraints: compact global constraints (AllDifferent, AllowedAssignments)
    - Search:      constraint propagation + lazy-clause SAT search
    - Strength:    compact model; powerful inference prunes search space

  MIP/SCIP (Mixed Integer Programming):
    - Variables:   O(S * D * H * R) -- one binary per (session, day, hour, room)
    - Constraints: O(D*H*R + G*D*H) linear inequalities
    - Search:      LP relaxation + branch-and-bound
    - Strength:    LP relaxation gives tight objective bounds

  Key trade-off:
    CP builds a small model but relies on inference for pruning.
    MIP builds a large model but gets strong bounds from LP relaxation.
    As problem size grows, MIP variable count explodes (multiplicative),
    while CP stays linear in the number of sessions.
""")


def write_json_report(results: List[BenchmarkResult], path: str):
    data = [asdict(r) for r in results]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"JSON report written to: {path}")


# ---------------------------------------------------------------------------
# 7. CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark CP-SAT vs MIP/SCIP for class scheduling"
    )
    parser.add_argument(
        "--scales",
        nargs="+",
        choices=list(SCALE_CONFIGS.keys()),
        default=None,
        help="Which scale levels to run (default: all)",
    )
    parser.add_argument(
        "--max-time",
        type=float,
        default=60.0,
        help="Solver time limit in seconds (default: 60)",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Path to write JSON report file",
    )
    args = parser.parse_args()

    print("===== CP-SAT vs MIP/SCIP Benchmark =====")
    results = run_benchmark_matrix(scales=args.scales, max_time=args.max_time)
    print_summary(results)

    if args.json:
        write_json_report(results, args.json)


if __name__ == "__main__":
    main()
