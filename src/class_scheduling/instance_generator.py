from .data import (
    Classroom,
    Course,
    Department,
    Enrollment,
    Location,
    Quota,
    SchedulingInput,
)


def generate_scaled_instance(
    base: SchedulingInput, scale_factor: int
) -> SchedulingInput:
    """Duplicate departments, courses, classrooms and enrollments to create a
    larger problem instance.  Each copy gets unique IDs so the solver treats
    them as independent cohorts sharing an expanded set of rooms."""

    if scale_factor <= 1:
        return base

    max_dep = max(d.id for d in base.departments)
    max_crs = max(c.id for c in base.courses)
    max_room = max(r.id for r in base.classrooms)
    max_loc = max(loc.id for loc in base.locations) if base.locations else 0

    new_locs = list(base.locations)
    new_rooms = list(base.classrooms)
    new_deps = list(base.departments)
    new_courses = list(base.courses)
    new_enroll = list(base.students_enrolled)

    for s in range(1, scale_factor):
        dep_off = s * max_dep
        crs_off = s * max_crs
        room_off = s * max_room
        loc_off = s * max_loc

        for loc in base.locations:
            new_locs.append(
                Location(id=loc.id + loc_off, name=f"{loc.name} #{s + 1}")
            )

        for dep in base.departments:
            new_deps.append(
                Department(id=dep.id + dep_off, name=f"{dep.name} #{s + 1}")
            )

        for c in base.courses:
            new_courses.append(
                Course(
                    id=c.id + crs_off,
                    name=f"{c.name} #{s + 1}",
                    semester=c.semester,
                    dep_id=c.dep_id + dep_off,
                    quota=Quota(theory=c.quota.theory, practice=c.quota.practice),
                    needs_computers=c.needs_computers,
                )
            )

        for r in base.classrooms:
            new_rooms.append(
                Classroom(
                    id=r.id + room_off,
                    name=f"{r.name}_{s + 1}",
                    loc_id=r.loc_id + loc_off,
                    has_computers=r.has_computers,
                    capacity=r.capacity,
                )
            )

        for e in base.students_enrolled:
            new_enroll.append(
                Enrollment(
                    dep_id=e.dep_id + dep_off,
                    semester=e.semester,
                    count=e.count,
                )
            )

    return SchedulingInput(
        locations=new_locs,
        classrooms=new_rooms,
        departments=new_deps,
        courses=new_courses,
        students_enrolled=new_enroll,
    )
