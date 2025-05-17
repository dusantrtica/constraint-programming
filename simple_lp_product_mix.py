"""
We produce desks and tables.
Producing a desk requires 3 units of wood, one hour of labor and 50 minutes of machine time
Producing a table requires 5 units of wood, 2 hours of labor and 20 minuts of machine work

For each day we have 
 - 200 workers that each work 8 hours
 - 50 machines, each runs for 16 hours
 - a supply of 3600 units of wood.

Desks and tables are sold for $700 and $900 per unit

Objective - find how much of each should be produced to maximise the profit
"""

from mip import Model, INTEGER, maximize

def product_mix():

    model = Model()

    tables = model.add_var("tables", lb=0, var_type=INTEGER)
    desks = model.add_var("desks", lb=0, var_type=INTEGER)

    model.add_constr(desks*3 + tables *5 <= 3600)
    model.add_constr(desks + tables * 2 <= 200*8)
    model.add_constr(desks * 50 + tables * 20 <= 50*16*60)

    model.objective = maximize(700*desks + 900*tables)

    model.optimize()

    return {
        'tables': tables.x,
        'desks': desks.x
    }

def test_product_mix():
    products = product_mix()
    assert products['tables'] == 190
    assert products['desks'] == 883