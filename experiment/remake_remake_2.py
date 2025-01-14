import json
import time
import os
import torch
import gc

torch.random.manual_seed(0)
torch.cuda.manual_seed(0)

from evogp.tree import Forest, MAX_STACK
from evogp.algorithm import (
    GeneticProgramming,
    DefaultSelection,
    DefaultMutation,
    DefaultCrossover,
)
from evogp.problem import SymbolicRegression

OUTPUT_FILE = os.path.join(
    "./experiment/data", os.path.splitext(os.path.basename(__file__))[0] + ".json"
)
REPEAT_TIMES = 10


def func(x):
    val = x[0] ** 4 / (x[0] ** 4 + 1) + x[1] ** 4 / (x[1] ** 4 + 1)
    return val.reshape(-1)


output_data = []


def run_once(popsize, data_size, execution_code=0):
    problem = SymbolicRegression(
        func=func, num_inputs=2, num_data=data_size, lower_bounds=-5, upper_bounds=5
    )
    print("generate dataset success")
    algorithm = GeneticProgramming(
        crossover=DefaultCrossover(),
        mutation=DefaultMutation(
            mutation_rate=0.2,
            generate_configs=Forest.random_generate_check(
                pop_size=1,
                gp_len=400,
                input_len=2,
                output_len=1,
                const_prob=0.5,
                out_prob=0,
                func_prob={
                    "+": 3,
                    "-": 3,
                    "*": 3,
                    "/": 3,
                    "sin": 1,
                    "cos": 1,
                    "tan": 1,
                },
                const_range=(-5, 5),
                sample_cnt=100,
                layer_leaf_prob=0.2,
                max_layer_cnt=3,
            ),
        ),
        selection=DefaultSelection(survival_rate=0.4, elite_rate=0.1),
    )
    forest = Forest.random_generate(
        pop_size=popsize,
        gp_len=400,
        input_len=2,
        output_len=1,
        const_prob=0.5,
        out_prob=0.0,
        func_prob={
            "+": 3,
            "-": 3,
            "*": 3,
            "/": 3,
            "sin": 1,
            "cos": 1,
            "tan": 1,
        },
        layer_leaf_prob=0.2,
        const_range=(-5, 5),
        sample_cnt=100,
        max_layer_cnt=5,
    )

    info = {
        "popsize": popsize,
        "data_size": data_size,
        "execution_code": execution_code,
    }

    algorithm.initialize(forest)
    fitness = problem.evaluate(forest)
    torch.cuda.synchronize()
    total_sr_time = 0
    total_time_tic = time.time()
    for i in range(50):
        print(i)
        forest = algorithm.step(fitness, args_check=False)
        torch.cuda.synchronize()
        SR_tic = time.time()
        fitness = problem.evaluate(
            forest, execute_code=execution_code, args_check=False
        )
        torch.cuda.synchronize()
        total_sr_time += time.time() - SR_tic

    torch.cuda.synchronize()
    info["SR_time"] = total_sr_time
    info["total_time"] = time.time() - total_time_tic
    info["max_fitness"] = float(fitness.max())
    info["mean_fitness"] = float(fitness.mean())
    # write file

    output_data.append(info)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_data, f, indent=4)


def main():

    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w") as f:
            json.dump([], f)

    # create file
    for d in [64, 256, 1024, 4096]:
        for p in [
            1000000,
        ]:
            for _ in range(REPEAT_TIMES):
                gc.collect()
                torch.cuda.empty_cache()
                run_once(p, d, execution_code=3)  # advanced


if __name__ == "__main__":
    main()
