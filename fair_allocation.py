from mip import Model, minimize, INTEGER


def fair_allocation():
    amount = 1000
    model = Model()
    x1 = model.add_var(name="x1", lb=0, ub=amount, var_type=INTEGER)

    w = model.add_var("", lb=0, ub=amount, var_type=INTEGER)

    model.add_constr(amount - 2 * x1 <= w)
    model.add_constr(2 * x1 - amount <= w)

    model.add_constr(x1 >= 0)

    model.objective = minimize(w)
    model.optimize()

    return [x1.x, amount - x1.x]


def test_fair_allocation():
    assert fair_allocation() == [500, 500]
