from pydantic import BaseModel, StrictInt, Field
from pydantic.dataclasses import dataclass
from typing import List

@dataclass
class Location:
    id: int
    name: str

@dataclass
class Classroom:
    id: int
    name: str
    has_computers: bool
    capacity: int

@dataclass
class Department:
    id: int
    name: str

@dataclass
class Quota:
    theory: int
    practice: int

@dataclass
class Course:
    id: int
    name: str
    depId: str
    quota: Quota

@dataclass
class StudentsEnrolled:
    depId: int
    count: int

@dataclass
class Settings:
    working_days: List[str]
    start_hour: int
    end_hour: int


@dataclass
class SchedulingInput:
    settings: Settings
    locations: List[Location]
    classrooms: List[Classroom]
    departments: List[Department]
    couses: List[Course]
    students_enrolled: List[StudentsEnrolled]