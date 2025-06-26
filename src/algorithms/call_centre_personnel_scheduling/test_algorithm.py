import sys
import pytest
from src.algorithms.call_centre_personnel_scheduling.algorithm import solve_single_day
from src.algorithms.call_centre_personnel_scheduling.model import Settings, Shift


def test_solve_single_day():
    demands = [0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 4, 4, 4, 4, 4, 3, 3, 3, 2, 2, 0, 0, 0]
    settings_dict = {
        "earliest_start": 9*60,
        "latest_start": 10*60,
        "earliest_break_start_from_shift_start": 3*60,
        "latest_break_start_from_shift_start": 4*60,
        "bucket_size": 60,
        "min_shift_duration": 9*60,
        "max_shift_duration": 9*60,
        "demands_single_day": demands
    }

    result = solve_single_day(Settings(**settings_dict))

    assert result == []

if __name__ == '__main__':
    sys.exit(pytest.main(["-v", __file__]))