from dataclasses import dataclass, field

NUM_DAYS = 5
SLOTS_PER_DAY = 9
TOTAL_SLOTS = NUM_DAYS * SLOTS_PER_DAY

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SLOT_LABELS = [f"{h:02d}:00" for h in range(8, 8 + SLOTS_PER_DAY)]

GAP_WEIGHT = 1
BALANCE_WEIGHT = 5
TIME_LIMIT_SECONDS = 120
MAX_GROUP_SIZE = 50


@dataclass
class SolverConfig:
    gap_weight: int = GAP_WEIGHT
    balance_weight: int = BALANCE_WEIGHT
    time_limit_seconds: int = TIME_LIMIT_SECONDS
    max_group_size: int = MAX_GROUP_SIZE


@dataclass
class Assignment:
    session_id: int
    day: int
    slot: int
    room_index: int


@dataclass
class SolverResult:
    status: str
    assignments: list[Assignment] = field(default_factory=list)
    objective_value: float = float("inf")
    solve_time_seconds: float = 0.0
    time_to_first_solution: float = 0.0
    num_variables: int = 0
    num_constraints: int = 0
    peak_memory_bytes: int = 0
    optimality_gap: float = float("inf")
