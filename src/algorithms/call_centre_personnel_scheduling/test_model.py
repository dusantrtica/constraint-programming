import pytest
import sys
from src.algorithms.call_centre_personnel_scheduling.model import generate_shifts, Settings, Shift

def test_settings_from_dict():
    settings_dict = {
        "earliest_start": 9*60,
        "latest_start": 11*60,
        "earliest_break_start_from_shift_start": 4*60,
        "latest_break_start_from_shift_start": 6*60,
        "bucket_size": 60,
        "min_shift_duration": 8*60,
        "max_shift_duration": 8*60,
    }
    settings = Settings(**settings_dict)

    assert settings.bucket_size == 60
    assert settings.earliest_break_start_from_shift_start == 4*60
    assert settings.latest_break_start_from_shift_start == 6*60
    assert settings.earliest_start == 9*60
    assert settings.latest_start == 11*60

def test_generate_shifts():
    settings_dict = {
        "earliest_start": 9*60,
        "latest_start": 10*60,
        "earliest_break_start_from_shift_start": 3*60,
        "latest_break_start_from_shift_start": 4*60,
        "bucket_size": 60,
        "min_shift_duration": 9*60,
        "max_shift_duration": 9*60,
    }

    shifts = generate_shifts(Settings(**settings_dict))

    assert len(shifts) == 4
    assert shifts[0] == Shift(start=9*60, end=18*60, start_break=12*60, end_break=13*60)
    assert shifts[1] == Shift(start=9*60, end=18*60, start_break=13*60, end_break=14*60)
    assert shifts[2] == Shift(start=10*60, end=19*60, start_break=13*60, end_break=14*60)
    assert shifts[3] == Shift(start=10*60, end=19*60, start_break=14*60, end_break=15*60)
    

        

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))