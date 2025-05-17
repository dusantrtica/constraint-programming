"""
We are scheduling employees in a department store
Each employee works 5 days in a row and then takes rest for 2 consecutive days
Demands are:
Mon Tue Wed Thu Fri Sat Sun
110 80  150 30  70  160 120

There are 7 shifts: Mon-Fri, Tue-Sat, ..., Sun-Sat
We want to minimize the number of employees hired
"""

from mip import Model, minimize, xsum, INTEGER

def schedule_personnel():
    demands = [110, 80, 150, 30, 70, 160, 120]
    total_employees_needed = sum(demands)
    model = Model()

    # x - number of employees whose shifts start on Monday, Tuesday, ..., Sunday
    x = [None for _ in range(len(demands))]

    # Add variables
    for i in range(len(demands)):        
        x[i] = model.add_var("day_{}".format(i), lb=0, ub=total_employees_needed, var_type=INTEGER)
    

    # 110 employees are needed on Monday
    model.add_constr(x[0] + x[3] + x[4] + x[5] + x[6] >= 110)

    # 80 employees are needed on Tuesday
    model.add_constr(x[0] + x[1] + x[4] + x[5] + x[6] >= 80)

    # 150 employees are needed on Wednesday
    model.add_constr(x[0] + x[1] + x[2] + x[5] + x[6] >= 150)

    # 30 employees are needed on  Thursday
    model.add_constr(x[0] + x[1] + x[2] + x[3] + x[6] >= 30)

    # 70 employees are needed on Friday
    model.add_constr(x[0] + x[1] + x[2] + x[3] + x[4] >= 70)

    # 160 employees are needed on Saturday
    model.add_constr(x[1] + x[2] + x[3] + x[4] + x[5] >= 160)

    # 120 employees are needed on Sunday
    model.add_constr(x[2] + x[3] + x[4] + x[5] + x[6] >= 120)
    
    model.objective = minimize(xsum(x))

    model.optimize()    

    return [shift.x for shift in x]

def test_personnel_scheduling():
    result = schedule_personnel()    
    print(result)
    assert result == [4, 40, 12, 14, 0, 94, 0]
    