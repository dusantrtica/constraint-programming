from pydantic import BaseModel, StrictInt, Field
from typing import List

class Settings(BaseModel):
    earliest_start: StrictInt = Field(ge=0, le=23*60)
    latest_start: StrictInt = Field(ge=0, le=23*60)
    earliest_break_start_from_shift_start: StrictInt
    latest_break_start_from_shift_start: StrictInt
    bucket_size: StrictInt
    min_shift_duration: StrictInt
    max_shift_duration: StrictInt

class Shift(BaseModel):
    start: StrictInt
    end: StrictInt
    start_break: StrictInt
    end_break: StrictInt



def generate_shifts(settings: Settings) -> List[Shift]:
    earliest_start = settings.earliest_start
    latest_start = settings.latest_start
    bucket_size = settings.bucket_size
    earliest_brk_start = settings.earliest_break_start_from_shift_start
    latest_brk_start = settings.latest_break_start_from_shift_start
    min_shift_duration = settings.min_shift_duration
    max_shift_duration = settings.max_shift_duration

    shifts = []

    for start in range(earliest_start, latest_start+1, bucket_size):        
        for brk_start in range(earliest_brk_start, latest_brk_start+1, bucket_size):    
            for duration in range(min_shift_duration, max_shift_duration+1, bucket_size):                
                end = start + duration
                start_break = start + brk_start
                end_break = start_break + 60
                shift_dict = {
                    "start": start,
                    "end": end,
                    "start_break": start_break,
                    "end_break": end_break
                }
                shifts.append(Shift(**shift_dict))

    return shifts