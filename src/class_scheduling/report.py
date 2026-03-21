from __future__ import annotations

from typing import TYPE_CHECKING

from .common import (
    DAY_NAMES,
    NUM_DAYS,
    SLOT_LABELS,
    SLOTS_PER_DAY,
    Assignment,
    SolverResult,
)

if TYPE_CHECKING:
    from .data import Classroom, SchedulingInput, Session


# ---------------------------------------------------------------------------
# Solution quality helpers
# ---------------------------------------------------------------------------

def compute_quality_metrics(
    result: SolverResult,
    sessions: list[Session],
    classrooms: list[Classroom],
) -> dict:
    """Derive per-cohort gap and load statistics from a solved assignment."""
    if not result.assignments:
        return {"total_gaps": None, "max_daily_load": None, "avg_gap_per_day": None}

    sess_map = {s.id: s for s in sessions}
    asgn_map = {a.session_id: a for a in result.assignments}

    cohort_day_slots: dict[tuple, dict[int, list[int]]] = {}
    for a in result.assignments:
        s = sess_map[a.session_id]
        bucket = cohort_day_slots.setdefault(s.cohort, {})
        bucket.setdefault(a.day, []).append(a.slot)

    total_gaps = 0
    max_load = 0
    active_days = 0

    for _cohort, day_slots in cohort_day_slots.items():
        for _d, slots in day_slots.items():
            slots_sorted = sorted(slots)
            span = slots_sorted[-1] - slots_sorted[0] + 1
            gap = span - len(slots_sorted)
            total_gaps += gap
            active_days += 1
            if len(slots_sorted) > max_load:
                max_load = len(slots_sorted)

    avg_gap = total_gaps / active_days if active_days else 0.0
    return {
        "total_gaps": total_gaps,
        "max_daily_load": max_load,
        "avg_gap_per_day": round(avg_gap, 2),
    }


# ---------------------------------------------------------------------------
# Timetable
# ---------------------------------------------------------------------------

def _short_name(name: str, max_len: int = 18) -> str:
    return name if len(name) <= max_len else name[: max_len - 2] + ".."


def print_timetable(
    result: SolverResult,
    sessions: list[Session],
    classrooms: list[Classroom],
    input_data: SchedulingInput,
) -> None:
    if not result.assignments:
        print("  (no solution)")
        return

    sess_map = {s.id: s for s in sessions}
    asgn_map = {a.session_id: a for a in result.assignments}

    dep_name = {d.id: d.name for d in input_data.departments}
    enroll = {
        (e.dep_id, e.semester): e.count for e in input_data.students_enrolled
    }

    cohort_ids: dict[tuple, list[int]] = {}
    for s in sessions:
        cohort_ids.setdefault(s.cohort, []).append(s.id)

    col_w = 22
    for cohort, sids in sorted(cohort_ids.items()):
        dep_id, sem = cohort
        header = (
            f"{dep_name.get(dep_id, '?')}, Sem {sem} "
            f"({enroll.get(cohort, '?')} students)"
        )
        print(f"\n  Cohort: {header}")
        print("  " + "-" * (8 + col_w * NUM_DAYS))

        header_row = f"  {'Slot':<8}"
        for dn in DAY_NAMES:
            header_row += f"{dn:<{col_w}}"
        print(header_row)
        print("  " + "-" * (8 + col_w * NUM_DAYS))

        grid: dict[tuple[int, int], str] = {}
        for sid in sids:
            if sid not in asgn_map:
                continue
            a = asgn_map[sid]
            s = sess_map[sid]
            tag = "T" if s.session_type == "theory" else "P"
            room_name = classrooms[a.room_index].name
            cell = f"{_short_name(s.course_name)} ({tag})"
            cell += f"\n{'':8}{'@' + room_name:<{col_w}}"
            grid[(a.slot, a.day)] = cell

        for sl in range(SLOTS_PER_DAY):
            line1 = f"  {SLOT_LABELS[sl]:<8}"
            line2 = f"  {'':8}"
            for d in range(NUM_DAYS):
                raw = grid.get((sl, d), "")
                if raw:
                    parts = raw.split("\n")
                    line1 += f"{parts[0]:<{col_w}}"
                    line2 += f"{'@' + parts[1].strip().lstrip('@'):<{col_w}}" if len(parts) > 1 else " " * col_w
                else:
                    line1 += " " * col_w
                    line2 += " " * col_w
            print(line1)
            print(line2)

        print("  " + "-" * (8 + col_w * NUM_DAYS))


# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------

def _fmt_val(v, fmt=".4f"):
    if v is None:
        return "N/A"
    if isinstance(v, float):
        if v == float("inf"):
            return "inf"
        return f"{v:{fmt}}"
    return str(v)


def print_comparison_table(
    cp_result: SolverResult,
    mip_result: SolverResult,
    cp_quality: dict,
    mip_quality: dict,
) -> None:
    col = 22
    sep = "+" + "-" * 32 + "+" + "-" * col + "+" + "-" * col + "+"
    hdr = f"|{'Metric':^32}|{'CP (OR-Tools)':^{col}}|{'MIP (SCIP)':^{col}}|"

    rows = [
        ("Status", cp_result.status, mip_result.status),
        ("Objective value", _fmt_val(cp_result.objective_value, ".1f"), _fmt_val(mip_result.objective_value, ".1f")),
        ("Solve time (s)", _fmt_val(cp_result.solve_time_seconds), _fmt_val(mip_result.solve_time_seconds)),
        ("Time to 1st solution (s)", _fmt_val(cp_result.time_to_first_solution), _fmt_val(mip_result.time_to_first_solution)),
        ("Variables", cp_result.num_variables, mip_result.num_variables),
        ("Constraints", cp_result.num_constraints, mip_result.num_constraints),
        ("Peak memory (MB)", _fmt_val(cp_result.peak_memory_bytes / 1e6, ".2f"), _fmt_val(mip_result.peak_memory_bytes / 1e6, ".2f")),
        ("Optimality gap", _fmt_val(cp_result.optimality_gap, ".4f"), _fmt_val(mip_result.optimality_gap, ".4f")),
        ("Total gaps", _fmt_val(cp_quality.get("total_gaps")), _fmt_val(mip_quality.get("total_gaps"))),
        ("Max daily load", _fmt_val(cp_quality.get("max_daily_load")), _fmt_val(mip_quality.get("max_daily_load"))),
        ("Avg gap / active day", _fmt_val(cp_quality.get("avg_gap_per_day"), ".2f"), _fmt_val(mip_quality.get("avg_gap_per_day"), ".2f")),
    ]

    print(sep)
    print(hdr)
    print(sep)
    for label, cv, mv in rows:
        print(f"|{label:<32}|{str(cv):^{col}}|{str(mv):^{col}}|")
    print(sep)


# ---------------------------------------------------------------------------
# Scalability chart
# ---------------------------------------------------------------------------

def plot_scalability(
    results: dict[int, dict],
    save_path: str = "scalability.png",
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[warning] matplotlib not installed -- skipping chart")
        return

    scales = sorted(results.keys())
    cp_times = []
    mip_times = []
    session_counts = []

    for s in scales:
        cp_times.append(results[s]["cp"].solve_time_seconds)
        mip_times.append(results[s]["mip"].solve_time_seconds)
        session_counts.append(results[s]["num_sessions"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.plot(scales, cp_times, "o-", label="CP (OR-Tools)")
    ax1.plot(scales, mip_times, "s-", label="MIP (Python-MIP)")
    ax1.set_xlabel("Scale factor")
    ax1.set_ylabel("Solve time (s)")
    ax1.set_title("Solve Time vs Problem Scale")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(scales, [results[s]["cp"].peak_memory_bytes / 1e6 for s in scales], "o-", label="CP")
    ax2.plot(scales, [results[s]["mip"].peak_memory_bytes / 1e6 for s in scales], "s-", label="MIP")
    ax2.set_xlabel("Scale factor")
    ax2.set_ylabel("Peak memory (MB)")
    ax2.set_title("Memory vs Problem Scale")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    print(f"  Scalability chart saved to {save_path}")
    plt.close(fig)
