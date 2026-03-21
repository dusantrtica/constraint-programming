"""Run CP-SAT and Python-MIP solvers on a class-scheduling instance and
compare performance, solution quality, and (optionally) scalability."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .common import SolverConfig, TIME_LIMIT_SECONDS
from .cp_solver import solve_cp
from .data import SchedulingInput, generate_sessions, load_input
from .instance_generator import generate_scaled_instance
from .mip_solver import solve_mip
from .report import (
    compute_quality_metrics,
    plot_scalability,
    print_comparison_table,
    print_timetable,
)

_DEFAULT_INPUT = os.path.join(
    os.path.dirname(__file__), "sample", "input.json"
)


def _run_single(
    input_data: SchedulingInput,
    config: SolverConfig,
    label: str = "",
) -> dict:
    sessions = generate_sessions(input_data, config.max_group_size)
    n_sess = len(sessions)
    n_rooms = len(input_data.classrooms)

    if label:
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"  {n_sess} sessions, {n_rooms} rooms")
        print(f"{'='*60}")

    print("\n>> Running CP solver (OR-Tools CP-SAT) ...")
    cp_result = solve_cp(sessions, input_data.classrooms, config)
    print(f"   status={cp_result.status}  time={cp_result.solve_time_seconds:.3f}s")

    print(">> Running MIP solver (Python-MIP / CBC) ...")
    mip_result = solve_mip(sessions, input_data.classrooms, config)
    print(f"   status={mip_result.status}  time={mip_result.solve_time_seconds:.3f}s")

    cp_q = compute_quality_metrics(cp_result, sessions, input_data.classrooms)
    mip_q = compute_quality_metrics(mip_result, sessions, input_data.classrooms)

    print("\n--- Comparison ---")
    print_comparison_table(cp_result, mip_result, cp_q, mip_q)

    return {
        "cp": cp_result,
        "mip": mip_result,
        "cp_quality": cp_q,
        "mip_quality": mip_q,
        "sessions": sessions,
        "num_sessions": n_sess,
    }


def _run_scalability(
    base_input: SchedulingInput,
    config: SolverConfig,
    scales: list[int],
) -> None:
    results: dict[int, dict] = {}

    for sf in scales:
        scaled = generate_scaled_instance(base_input, sf)
        info = _run_single(scaled, config, label=f"Scale {sf}x")
        results[sf] = {
            "cp": info["cp"],
            "mip": info["mip"],
            "num_sessions": info["num_sessions"],
        }

    print("\n--- Scalability Summary ---")
    col = 14
    hdr = f"{'Scale':>{6}} {'Sessions':>{10}} {'CP time(s)':>{col}} {'MIP time(s)':>{col}} {'CP status':>{col}} {'MIP status':>{col}}"
    print(hdr)
    for sf in scales:
        r = results[sf]
        print(
            f"{sf:>6} {r['num_sessions']:>10} "
            f"{r['cp'].solve_time_seconds:>{col}.3f} "
            f"{r['mip'].solve_time_seconds:>{col}.3f} "
            f"{r['cp'].status:>{col}} "
            f"{r['mip'].status:>{col}}"
        )

    plot_scalability(results)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CP vs MIP university class-scheduling comparison"
    )
    parser.add_argument(
        "--input", default=_DEFAULT_INPUT, help="path to input JSON"
    )
    parser.add_argument(
        "--time-limit",
        type=int,
        default=TIME_LIMIT_SECONDS,
        help="solver time limit in seconds",
    )
    parser.add_argument(
        "--scalability",
        action="store_true",
        help="run scalability comparison over multiple problem sizes",
    )
    parser.add_argument(
        "--scales",
        nargs="+",
        type=int,
        default=[1, 2, 3],
        help="scale factors for scalability test (default: 1 2 3)",
    )
    parser.add_argument(
        "--show-timetable",
        action="store_true",
        help="print the full weekly timetable for each solver",
    )
    args = parser.parse_args()

    config = SolverConfig(time_limit_seconds=args.time_limit)
    input_data = load_input(args.input)

    info = _run_single(input_data, config, label="Base instance")

    if args.show_timetable:
        sessions = info["sessions"]
        rooms = input_data.classrooms
        if info["cp"].assignments:
            print("\n--- CP Timetable ---")
            print_timetable(info["cp"], sessions, rooms, input_data)
        if info["mip"].assignments:
            print("\n--- MIP Timetable ---")
            print_timetable(info["mip"], sessions, rooms, input_data)

    if args.scalability:
        _run_scalability(input_data, config, args.scales)


if __name__ == "__main__":
    main()
