import json
from pathlib import Path
from pydantic import TypeAdapter
from src.class_scheduling.sample.model import SchedulingInput

def load_input(path: str) -> SchedulingInput:
    raw = Path(path).read_text(encoding='utf-8')
    adapter = TypeAdapter(SchedulingInput)
    return adapter.validate_python(json.loads(raw))

