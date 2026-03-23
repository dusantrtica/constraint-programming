import json
from pathlib import Path
from src.class_scheduling.sample.model import SchedulingInput, Settings

def load_input(path: str) -> SchedulinInput:
    raw = Path(path).read_text(encoding='utf-8')
    return SchedulingInput.model_validate(json.load(raw))

