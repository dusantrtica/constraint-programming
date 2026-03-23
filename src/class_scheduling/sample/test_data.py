import os
import sys
import pytest
from src.class_scheduling.sample.data import load_input
from src.class_scheduling.sample.model import Settings


def test_parse_sample_input():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input.json")

    result = load_input(path)
    assert result is not None

    assert result.settings == Settings(**{
        "working_days": ["Ponedeljak", "Utorak", "Sreda", "Četvrtak", "Petak"],
        "start_hour": 8,
        "end_hour": 20,
        "duration": 1,
    })

    assert result.locations[0].id == 1
    assert result.locations[0].name == 'Studentski trg'


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
