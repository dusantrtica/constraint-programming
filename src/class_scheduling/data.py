import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from pydantic import BaseModel, ConfigDict, Field


class Quota(BaseModel):
    theory: int
    practice: int


class Location(BaseModel):
    id: int
    name: str


class Classroom(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    loc_id: int = Field(alias="locId")
    has_computers: int = Field(alias="hasComputers")
    capacity: int


class Department(BaseModel):
    id: int
    name: str


class Course(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    semester: int
    dep_id: int = Field(alias="depId")
    quota: Quota
    needs_computers: int = Field(default=0, alias="needsComputers")


class Enrollment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dep_id: int = Field(alias="depId")
    semester: int
    count: int


class SchedulingInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    locations: list[Location] = []
    classrooms: list[Classroom]
    departments: list[Department]
    courses: list[Course]
    students_enrolled: list[Enrollment] = Field(alias="studentsEnrolled")


@dataclass
class Session:
    id: int
    course_id: int
    course_name: str
    session_type: str
    cohort: Tuple[int, int]
    required_capacity: int
    needs_computers: bool


def load_input(path: str) -> SchedulingInput:
    raw = Path(path).read_text(encoding="utf-8")
    return SchedulingInput.model_validate(json.loads(raw))


def generate_sessions(
    input_data: SchedulingInput, max_group_size: int = 50
) -> list[Session]:
    sessions: list[Session] = []
    session_id = 0

    enrollment_map: dict[Tuple[int, int], int] = {}
    for e in input_data.students_enrolled:
        enrollment_map[(e.dep_id, e.semester)] = e.count

    for course in input_data.courses:
        cohort = (course.dep_id, course.semester)
        enrolled = enrollment_map.get(cohort, 0)

        for _ in range(course.quota.theory):
            sessions.append(
                Session(
                    id=session_id,
                    course_id=course.id,
                    course_name=course.name,
                    session_type="theory",
                    cohort=cohort,
                    required_capacity=enrolled,
                    needs_computers=False,
                )
            )
            session_id += 1

        if course.quota.practice > 0 and enrolled > 0:
            num_groups = max(1, math.ceil(enrolled / max_group_size))
            group_cap = math.ceil(enrolled / num_groups)
            for _g in range(num_groups):
                for _ in range(course.quota.practice):
                    sessions.append(
                        Session(
                            id=session_id,
                            course_id=course.id,
                            course_name=course.name,
                            session_type="practice",
                            cohort=cohort,
                            required_capacity=group_cap,
                            needs_computers=bool(course.needs_computers),
                        )
                    )
                    session_id += 1

    return sessions


def get_eligible_rooms(session: Session, classrooms: list[Classroom]) -> list[int]:
    eligible: list[int] = []
    for idx, room in enumerate(classrooms):
        if room.capacity < session.required_capacity:
            continue
        if session.needs_computers and not room.has_computers:
            continue
        eligible.append(idx)
    return eligible
