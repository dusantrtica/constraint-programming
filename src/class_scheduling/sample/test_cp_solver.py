from typing_extensions import deprecated
from src.class_scheduling.sample.cp_solver import SimpleCPSolver

import pytest
import os
import sys
from src.class_scheduling.sample.model import (
    Classroom,
    SchedulingInput,
    Settings,
    Course,
    Quota
)


@pytest.fixture
def scheduling_input():
    # Return a minimal, valid SchedulingInput object.
    # You may need to adjust this when you add required fields to SchedulingInput.
    return SchedulingInput(
        # Fill in minimal required dummy/test data for your SchedulingInput model below.
        settings=Settings(
            **{
                "working_days": ["Ponedeljak", "Utorak", "Sreda"],
                "start_hour": 8,
                "end_hour": 14,
            }
        ),
        classrooms=[
            Classroom(**{"id": 1, "name": "840", "locId": 1, "has_computers": False}),
            Classroom(**{"id": 2, "name": "704", "locId": 1, "has_computers": True}),
            Classroom(**{"id": 3, "name": "841", "locId": 1, "has_computers": False}),
        ],
        courses=[
            Course(
                **{
                    "id": 1,
                    "name": "Analiza 1",
                    "semester": 1,
                    "depId": 1,
                    "quota": Quota(**{"theory": 4, "practice": 4}),
                    "needsComputers": 0,
                }
            ),                    
        ],
        locations=[],
        departments=[],    
        students_enrolled=[]
    )


def test_cp_solver_init_data(scheduling_input):
    solver = SimpleCPSolver(scheduling_input)
    assert solver.settings == scheduling_input.settings
    assert solver.classrooms == scheduling_input.classrooms
    assert solver.courses == scheduling_input.courses    
    assert solver.departments == scheduling_input.departments
    assert solver.students_enrolled == scheduling_input.students_enrolled
    assert solver.working_hours == [8, 9, 10, 11, 12, 13]


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
