import pytest
import sys

from src.algorithms.simple_lp_product_mix import (
    Capacity,
    Product,
    product_mix,
    parametrized_product_mix,
)


def test_product_mix():

    products = product_mix()
    assert products["tables"] == 190
    assert products["desks"] == 883


def test_parametrized_product_mix():
    desk = Product(
        name="desk",
        wood_units_needed=3,
        labor_time=1,
        machine_time=50,
        selling_price=700,
    )
    table = Product(
        name="table",
        wood_units_needed=5,
        labor_time=2,
        machine_time=20,
        selling_price=900,
    )

    daily_capacity = Capacity(
        workers=200, num_machines=50, single_machine_runtime=16, supply_of_woods=3600
    )

    products = parametrized_product_mix([desk, table], daily_capacity)
    assert products["table"] == 190
    assert products["desk"] == 883


if __name__ == '__main__':
    sys.exit(pytest.main())