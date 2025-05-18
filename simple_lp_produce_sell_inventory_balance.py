"""
We produce and sell a product.
For the coming 4 days, the marketing manager has promised to
fulfill the following amount of demands:
 - Days 1,2,3,4 :100, 150, 200, 170 units
 - The unit pdouctions costs are different for different days:
    Days 1,2,3,4: 9, 12 10 and 12 USD per unit

The selling prices are all fixed - So maximing profits is the same as minimizing costs

We may store a product and sell it later:
 - The inventory cost is $1 per unit per day.

For example, we may decide to produce all 620 products on day 1
so the cost is:
$9 * 620 + $1 * 150 + $2 * 200 + $3 * 170 = $6640
"""

from mip import Model, minimize


def minimize_costs():
    model = Model()
    demands = [100, 150, 200, 170]
    production_cost_day = [9, 12, 10, 12]
    inventory_cost = [1, 1, 1, 1]

    n_days = 4

    # TOOD: implement

    pass
