from src.class_scheduling.sample.cp_solver import SimpleCPSolver

import pytest
import os
import sys
from src.class_scheduling.sample.model import SchedulingInput

@pytest.fixture
def scheduling_input():
    # Return a minimal, valid SchedulingInput object.
    # You may need to adjust this when you add required fields to SchedulingInput.
    return SchedulingInput(
        # Fill in minimal required dummy/test data for your SchedulingInput model below.
        settings=None,
        classrooms=[],
        courses=[],
        departments=[]
    )


def test_cp_solver_init(scheduling_input):
    solver = SimpleCPSolver(scheduling_input)
    assert solver.settings == None
    assert solver.classrooms == []



if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
