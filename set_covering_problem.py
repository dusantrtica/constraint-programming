from mip import Model, minimize, xsum, BINARY, maximize

"""
We have a set of locations and set of facilities.
Locations are given as a dict which keys are locations and value is a list
of facilities accessible from that location.

The goal is to allocate as few facilities as possible to cover all the locations.
"""


def set_covering(locations: dict, facilities):
    loc_len = len(locations.keys())
    fac_len = len(facilities)

    model = Model()

    # Out of all facilities, some might be build, some not, hence binary values
    x = [
        model.add_var("{}".format(facility), var_type=BINARY) for facility in facilities
    ]

    A = [[None for _ in range(fac_len)] for _ in range(loc_len)]
    for loc, fac_list in locations.items():
        for fac_idx, facility in enumerate(facilities):
            # Constants indicating if location loc(i) is connected to facility(j)
            A[int(loc)][fac_idx] = 1 if facility in fac_list else 0

    # For every location, there has to be at least one facility connected to it
    for idx, _ in enumerate(locations.keys()):
        model.add_constr(xsum(A[idx][j] * x[j] for j in range(fac_len)) >= 1)

    # Minimize number of facilites needed
    model.objective = minimize(xsum(x))
    model.optimize()

    return [selected_loc.name for selected_loc in x if selected_loc.x == 1]


def maximum_covering(locations: dict, facilities: list, p: int) -> list:
    """
    We are restricted to cover at most P facilities and still to provide
    maximal covering
    """
    loc_len = len(locations.keys())
    fac_len = len(facilities)

    model = Model()

    # Out of all facilities, some might be build, some not, hence binary values
    x = [
        model.add_var("{}".format(facility), var_type=BINARY) for facility in facilities
    ]

    # Out of all locations (demands), some might be covered and some not
    # y variable indicates whether location is covered
    y = [
        model.add_var("{}".format(location), var_type=BINARY)
        for location in locations.keys()
    ]

    A = [[None for _ in range(fac_len)] for _ in range(loc_len)]
    for loc, fac_list in locations.items():
        for fac_idx, facility in enumerate(facilities):
            # Constants indicating if location loc(i) is connected to facility(j)
            A[int(loc)][fac_idx] = 1 if facility in fac_list else 0

    # For every location, there has to be at least one facility connected to it
    for idx, _ in enumerate(locations.keys()):
        model.add_constr(xsum(A[idx][j] * x[j] for j in range(fac_len)) >= y[idx])

    model.add_constr(xsum(x) <= p)

    # Maximize number of covered facilities
    model.objective = maximize(xsum(y))
    model.optimize()

    return [selected_loc.name for selected_loc in x if selected_loc.x == 1]


def test_set_covering():
    locations = {0: ["a", "b"], 1: ["a", "b", "c"], 2: ["b"], 3: ["c"]}

    facilities = ["a", "b", "c"]

    assert set_covering(locations, facilities) == ["b", "c"]


def test_maximum_covering():
    locations = {0: ["a", "b"], 1: ["a", "b", "c"], 2: ["b"], 3: ["c"]}

    facilities = ["a", "b", "c"]

    assert maximum_covering(locations, facilities, 1) == ["b"]
