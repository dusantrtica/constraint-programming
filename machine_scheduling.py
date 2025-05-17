from mip import Model, minimize, xsum, BINARY, INTEGER, OptimizationStatus

def machine_scheduling(jobs: list):
    model = Model()
    n = len(jobs)

    M = sum(jobs) + 1
    print(M)

    x = [model.add_var("{}".format(job), var_type=INTEGER, lb=0, ub=M) for job in jobs]

    z = [[model.add_var("{}_{}".format(i, j), var_type=BINARY) for i in range(n)] for j in range(n)]

    for i in range(n):
        for j in range(i+1, n):
            model.add_constr(x[i] + jobs[j] - x[j] <= M * z[i][j])
            model.add_constr(x[j] + jobs[i] - x[i] <= M * (1 - z[i][j]))
        model.add_constr(x[i] >= jobs[i])
        model.add_constr(x[i] >= 0)

    model.objective = minimize(xsum(x))
    status = model.optimize()

    if status == OptimizationStatus.INFEASIBLE:
        return None
        
    return [job.x for job in x]

def test_machine_scheduling():
    # for jobs which durations are 30, 15, 25, the optimal schedule is
    # 15 goes first, then 25, and then 30, hence their completion times are:
    # 15 -> 15
    # 25 -> 40 (we have to wait first job to finish and then job of 25 mins to complete)
    # 30 -> 70 (40 for prev 2 jobs and 30 for itself to complete)
    assert machine_scheduling([30, 15, 25]) == [70, 15, 40]