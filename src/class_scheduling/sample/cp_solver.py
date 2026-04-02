import math
from collections import defaultdict
from src.class_scheduling.sample.model import SchedulingInput, Settings, Course, Classroom
from src.class_scheduling.sample.data import Session, generate_sessions, GROUP_SIZE
from ortools.sat.python import cp_model
from typing import List


class SimpleCPSolver:
    """
    Constraint Programming solver for university class scheduling.

    Each session (a single lecture/practice for a specific student group)
    gets three integer variables: day, time slot, and room.
    The solver finds an assignment that satisfies all hard constraints
    and minimizes the latest hour used on any day.
    """

    def __init__(self, scheduling_input: SchedulingInput, sessions: List[Session] = None,
                 max_time_seconds: float = 30.0, log_progress: bool = True):
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.solver.parameters.max_time_in_seconds = max_time_seconds
        self.solver.parameters.log_search_progress = log_progress
        self.init_input(scheduling_input)
        # Use provided sessions, or generate them from enrollment data
        self.sessions = sessions if sessions is not None else generate_sessions(
            scheduling_input, GROUP_SIZE
        )
        self.create_assignment_variables()
        self.create_hard_constraints()
        self.set_objective()

    def init_input(self, scheduling_input: SchedulingInput):
        self.settings: Settings = scheduling_input.settings
        self.classrooms = scheduling_input.classrooms
        self.courses: List[Course] = scheduling_input.courses
        self.departments = scheduling_input.departments
        self.students_enrolled = scheduling_input.students_enrolled
        self.working_hours = [
            hour for hour in range(self.settings.start_hour, self.settings.end_hour)
        ]

    def create_assignment_variables(self):
        """
        For each session s, create:
          day_var[s]       -- which day (0..D-1)
          slot_var[s]      -- which hour slot (0..H-1)
          room_var[s]      -- which room index (0..R-1)
          flat_time_var[s] -- day * H + slot  (unique time slot in the week)
          room_time_var[s] -- room * D*H + flat_time  (unique room+time combo)
        """
        D = len(self.settings.working_days)
        H = len(self.working_hours)
        R = len(self.classrooms)
        total_slots = D * H

        self.day_var: dict[int, cp_model.IntVar] = {}
        self.slot_var: dict[int, cp_model.IntVar] = {}
        self.room_var: dict[int, cp_model.IntVar] = {}
        self.flat_time_var: dict[int, cp_model.IntVar] = {}
        self.room_time_var: dict[int, cp_model.IntVar] = {}

        for s in range(len(self.sessions)):
            self.day_var[s] = self.model.NewIntVar(0, D - 1, f"day_{s}")
            self.slot_var[s] = self.model.NewIntVar(0, H - 1, f"slot_{s}")
            self.room_var[s] = self.model.NewIntVar(0, R - 1, f"room_{s}")

            # flat_time linearizes (day, slot) into a single index:
            #   Ponedeljak slot 0 -> 0, Ponedeljak slot 1 -> 1, ...
            #   Utorak slot 0 -> H, Utorak slot 1 -> H+1, ...
            self.flat_time_var[s] = self.model.NewIntVar(
                0, total_slots - 1, f"flat_time_{s}"
            )
            self.model.Add(
                self.flat_time_var[s] == self.day_var[s] * H + self.slot_var[s]
            )

            # room_time linearizes (room, day, slot) into a single index
            # so that AllDifferent can enforce no two sessions share a room+time
            self.room_time_var[s] = self.model.NewIntVar(
                0, R * total_slots - 1, f"room_time_{s}"
            )
            self.model.Add(
                self.room_time_var[s]
                == self.room_var[s] * total_slots + self.flat_time_var[s]
            )

    def create_hard_constraints(self):
        """
        Hard constraint 1: No two sessions in the same room at the same time.
        Hard constraint 2: No two sessions for the same student group at the same time.
        Hard constraint 3: Sessions needing computers go to rooms that have them.
        """
        if not self.sessions:
            return

        # 1) No room-time overlap: each room_time value must be unique
        self.model.AddAllDifferent(list(self.room_time_var.values()))

        # 2) No group-time overlap: within each group, all flat_time values
        #    must differ (a group can't be in two places at once)
        groups = defaultdict(list)
        for s, session in enumerate(self.sessions):
            groups[session.group_id].append(s)

        for group_id, session_indices in groups.items():
            self.model.AddAllDifferent(
                [self.flat_time_var[s] for s in session_indices]
            )

        # 3) Computer room eligibility: if a session needs computers,
        #    its room_var can only take indices of rooms that have computers
        computer_room_indices = [
            i for i, room in enumerate(self.classrooms) if room.has_computers
        ]
        for s, session in enumerate(self.sessions):
            if session.needs_computers:
                self.model.AddAllowedAssignments(
                    [self.room_var[s]],
                    [[idx] for idx in computer_room_indices],
                )

    def set_objective(self):
        """
        Minimize the latest hour slot used on any day.
        This encourages the solver to spread sessions across days
        rather than packing one day until late evening.

        We also add a computed lower bound: the group with the most sessions
        needs at least ceil(num_sessions / num_days) hour slots, so
        max_slot >= ceil(max_group_sessions / D) - 1. This helps the solver
        prove optimality much faster.
        """
        if not self.sessions:
            return

        D = len(self.settings.working_days)
        H = len(self.working_hours)

        # Compute a tight lower bound from group sizes
        groups = defaultdict(int)
        for session in self.sessions:
            groups[session.group_id] += 1
        max_group_sessions = max(groups.values()) if groups else 0
        lower_bound = math.ceil(max_group_sessions / D) - 1 if D > 0 else 0

        self.max_slot = self.model.NewIntVar(lower_bound, H - 1, "max_slot")
        for s in range(len(self.sessions)):
            self.model.Add(self.max_slot >= self.slot_var[s])
        self.model.Minimize(self.max_slot)

    def solve(self):
        status = self.solver.Solve(self.model)
        return status

    def get_solution_variables(self):
        """
        After solve(), extract the assigned day, hour slot, and room index
        for each session. Returns raw indices so the caller can map them
        to names using settings.working_days, working_hours, and classrooms.
        """
        result = []
        for s in range(len(self.sessions)):
            day_index = self.solver.Value(self.day_var[s])
            slot_index = self.solver.Value(self.slot_var[s])
            room_index = self.solver.Value(self.room_var[s])
            result.append({
                "day": day_index,
                "hour": slot_index,
                "room": room_index,
            })
        return result
