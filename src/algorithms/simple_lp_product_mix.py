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

from mip import Model, INTEGER, maximize, xsum

from pydantic import BaseModel, Field, StrictInt, StrictFloat

from typing import List


class Product(BaseModel):
    name: str
    wood_units_needed: int
    labor_time: StrictInt = Field(ge=0, le=24)
    machine_time: StrictInt = Field(ge=0, le=3600)
    selling_price: StrictFloat = Field(ge=0)


class Capacity(BaseModel):
    workers: int
    num_machines: int
    single_machine_runtime: int
    supply_of_woods: int


def product_mix():
    model = Model()

    tables = model.add_var("tables", lb=0, var_type=INTEGER)
    desks = model.add_var("desks", lb=0, var_type=INTEGER)

    model.add_constr(desks * 3 + tables * 5 <= 3600)
    model.add_constr(desks + tables * 2 <= 200 * 8)
    model.add_constr(desks * 50 + tables * 20 <= 50 * 16 * 60)

    model.objective = maximize(700 * desks + 900 * tables)

    model.optimize()

    return {"tables": tables.x, "desks": desks.x}


def parametrized_product_mix(products_specs: List[Product], capacity: Capacity):
    model = Model()

    products = []

    for product_spec in products_specs:
        products.append(model.add_var(product_spec.name, var_type=INTEGER, lb=0))

    model.add_constr(
        xsum(
            [products[i] * p_spec.labor_time for i, p_spec in enumerate(products_specs)]
        )
        <= capacity.workers * 200 * 8
    )
    model.add_constr(
        xsum(
            [
                products[i] * p_spec.machine_time
                for i, p_spec in enumerate(products_specs)
            ]
        )
        <= capacity.num_machines * capacity.single_machine_runtime * 60
    )
    model.add_constr(
        xsum(
            [
                products[i] * p_spec.wood_units_needed
                for i, p_spec in enumerate(products_specs)
            ]
        )
        <= capacity.supply_of_woods
    )

    model.objective = maximize(
        xsum(
            [
                products[i] * p_spec.selling_price
                for i, p_spec in enumerate(products_specs)
            ]
        )
    )

    model.optimize()

    return {product.name: product.x for product in products}
