from src.class_scheduling.sample.cp_solver import SimpleCPSolver
from src.class_scheduling.sample.data import load_input


def print_report(solver: SimpleCPSolver):
    print("hello")

def run_cp_solver():
    scheduling_input = load_input("input.json")
    simple_cp_solver = SimpleCPSolver(scheduling_input)
    result = simple_cp_solver.solve()

    print(result)


if __name__ == '__main__':
    run_cp_solver()

