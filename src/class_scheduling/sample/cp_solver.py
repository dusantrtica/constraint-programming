from src.class_scheduling.sample.model import SchedulingInput, Settings, Course, Classroom
from ortools.sat.python import cp_model
from typing import List, Tuple


def to_tuple_index (day: str, hour: int, course: Course, classroom: Classroom) -> Tuple:
    return (day, hour, course.id, classroom.id,)

class SimpleCPSolver:
    def __init__(self, scheduling_input: SchedulingInput):        
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.init_input(scheduling_input)
        self.create_assignment_variables()
        self.create_constraints()


    def init_input(self, scheduling_input: SchedulingInput):
        self.settings: Settings = scheduling_input.settings
        self.classrooms = scheduling_input.classrooms
        self.courses: List[Course] = scheduling_input.courses
        self.departments = scheduling_input.departments
        self.students_enrolled = scheduling_input.students_enrolled        
        self.working_hours = [hour for hour in range(self.settings.start_hour, self.settings.end_hour)]

    def cohort_iter(self):
        for day in self.settings.working_days:
            for hour in self.working_hours:
                for course in self.courses:
                    for classroom in self.classrooms:
                        yield (day, hour, course, classroom)


    def create_assignment_variables(self):
        self.assignments = {}
        for cohort in self.cohort_iter():
            (day, hour, course, classroom) = cohort
            self.assignments[to_tuple_index(day, hour, course, classroom)] = self.model.NewBoolVar(
                f'assignment_{day}_{hour}_{course.id}_{classroom.id}'
            )

    

    def create_constraints(self):
        # constraint 1: za svaki time slot, u danu, najvise jedan kurs se moze odrzati
        for day in self.settings.working_days:
            for hour in self.working_hours:
                self.model.Add(sum(self.assignments[to_tuple_index(day, hour, course, classroom)] for course in self.courses for classroom in self.classrooms) == 1)
            
        # constraint 2: zasvaki 
        for day in self.settings.working_days:            
                for time in self.working_hours:
                    self.model.Add(
                        sum(self.assignments[to_tuple_index(day, hour, course, classroom)]
                        for classroom in self.classrooms for course in self.courses) == 1
                    )


    def solve(self):        
        status = self.solver.Solve(self.model)
        return status

    def get_solution_variables(self):
        for cohort in self.cohort_iter():
            if self.solver.Value(self.assignments[to_tuple_index(*cohort)]):
                yield cohort
