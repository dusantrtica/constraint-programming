import sys
import os

from ortools.linear_solver import pywraplp

from src.class_scheduling.sample.data import load_input
from src.class_scheduling.sample.mip_solver import SimpleMIPSolver
from src.class_scheduling.sample.model import SchedulingInput


def print_table(rows, headers):
    cols = len(headers)
    col_widths = [
        max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
        for i, h in enumerate(headers)
    ]
    format_str = " | ".join(["{:<%d}" % w for w in col_widths])
    header_line = format_str.format(*headers)
    sep_line = "-+-".join(["-" * w for w in col_widths])
    print(header_line)
    print(sep_line)
    for row in rows:
        print(format_str.format(*row))


if __name__ == "__main__":
    input_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input.json")

    print("Loading input...", flush=True)
    scheduling_input: SchedulingInput = load_input(input_path)
    print(
        f"Loaded {len(scheduling_input.courses)} courses, "
        f"{len(scheduling_input.classrooms)} rooms",
        flush=True,
    )

    print("Creating MIP solver (60s limit)...", flush=True)
    solver = SimpleMIPSolver(scheduling_input, max_time_seconds=60.0)
    print(f"Model has {len(solver.sessions)} sessions to schedule.", flush=True)
    print(
        f"Variables: {solver.solver.NumVariables()}, "
        f"Constraints: {solver.solver.NumConstraints()}",
        flush=True,
    )

    print("Solving...", flush=True)
    status = solver.solve()

    status_names = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
        pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
        pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
        pywraplp.Solver.ABNORMAL: "ABNORMAL",
        pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
    }
    print(f"\nSolver finished with status: {status_names.get(status, status)}", flush=True)

    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        print("No feasible solution found.")
        sys.exit(2)

    variables = solver.get_solution_variables()
    if not variables:
        print("No assignment found.")
        sys.exit(2)

    print(f"max_slot = {solver.max_slot.solution_value()}", flush=True)

    headers = [
        "Session",
        "Group",
        "Department",
        "Course",
        "SessionType",
        "NeedsPC",
        "Day",
        "Hour",
        "Room",
    ]
    rows = []
    day_list = scheduling_input.settings.working_days
    classroom_id_map = {i: c for i, c in enumerate(scheduling_input.classrooms)}
    courses_id_map = {c.id: c for c in scheduling_input.courses}

    for v, session in zip(variables, solver.sessions):
        room = classroom_id_map.get(v["room"])
        course = courses_id_map.get(session.course_id)
        row = [
            session.id,
            session.group_id,
            session.department_id,
            course.name if course else session.course_id,
            session.session_type,
            "YES" if session.needs_computers else "NO",
            day_list[v["day"]],
            v["hour"] + scheduling_input.settings.start_hour,
            f"{room.name} (id={room.id})" if room else v["room"],
        ]
        rows.append(row)

    print_table(rows, headers)
