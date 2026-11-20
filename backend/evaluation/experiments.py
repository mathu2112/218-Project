
from backend.evaluation.metrics import calculate_metrics


def run_experiment(
    strategy_name,
    allocations,
    available_stock,
    scenario_name="Normal Conditions"
):
    """
    Calculate the performance of one allocation strategy.
    """

    metrics = calculate_metrics(
        allocations,
        available_stock
    )

    return {
        "strategy": strategy_name,
        "scenario": scenario_name,
        "metrics": metrics
    }


def run_current_backend_evaluation(
    ai_allocations,
    human_allocations,
    available_stock,
    baseline_allocations=None,
    scenario_name="Normal Conditions"
):
    results = []

    # Evaluate AI recommendations
    results.append(
        run_experiment(
            strategy_name="AI Recommended Allocation",
            allocations=ai_allocations,
            available_stock=available_stock,
            scenario_name=scenario_name
        )
    )

    # Evaluate human decisions supported by AI
    results.append(
        run_experiment(
            strategy_name="Manual + AI",
            allocations=human_allocations,
            available_stock=available_stock,
            scenario_name=scenario_name
        )
    )

    # Include greedy baseline when available
    if baseline_allocations is not None:
        results.append(
            run_experiment(
                strategy_name="Greedy Baseline",
                allocations=baseline_allocations,
                available_stock=available_stock,
                scenario_name=scenario_name
            )
        )

    return results


def compare_strategies(results):
    """
    Extract important performance metrics for comparing allocation strategies.
    """

    comparison = []

    for result in results:

        metrics = result["metrics"]

        fulfilment = metrics["fulfilment"]

        unmet = metrics["unmet_demand"]

        utilisation = metrics["resource_utilisation"]

        comparison.append({

            "strategy": result["strategy"],

            "scenario": result["scenario"],

            "fulfilment_rate":
                fulfilment["fulfilment_rate"],

            "partial_fulfilment_rate":
                fulfilment["partial_fulfilment_rate"],

            "unfulfilled_rate":
                fulfilment["unfulfilled_rate"],

            "critical_fulfilment_rate":
                metrics["critical_fulfilment"][
                    "critical_fulfilment_rate"
                ],

            "medicine_unmet":
                unmet["medicine"]["unmet"],

            "shelter_unmet":
                unmet["shelter"]["unmet"],

            "nutrition_unmet":
                unmet["nutrition"]["unmet"],

            "medicine_utilisation":
                utilisation["medicine"]["utilisation_rate"],

            "shelter_utilisation":
                utilisation["shelter"]["utilisation_rate"],

            "nutrition_utilisation":
                utilisation["nutrition"]["utilisation_rate"]
        })

    return comparison


def display_results(results):
    """
    Print a readable comparison of the strategies.
    """

    comparison = compare_strategies(results)

    print("\n========== EVALUATION RESULTS ==========")

    for result in comparison:

        print("\nScenario:", result["scenario"])

        print("Strategy:", result["strategy"])

        print(
            "Fulfilment Rate:",
            result["fulfilment_rate"], "%"
        )

        print(
            "Partial Fulfilment Rate:",
            result["partial_fulfilment_rate"], "%"
        )

        print(
            "Unfulfilled Rate:",
            result["unfulfilled_rate"], "%"
        )

        print(
            "Critical Fulfilment Rate:",
            result["critical_fulfilment_rate"], "%"
        )

        print("\nUnmet Demand:")

        print("Medicine:", result["medicine_unmet"])

        print("Shelter:", result["shelter_unmet"])

        print("Nutrition:", result["nutrition_unmet"])

        print("\nResource Utilisation:")

        print(
            "Medicine:",
            result["medicine_utilisation"], "%"
        )

        print(
            "Shelter:",
            result["shelter_utilisation"], "%"
        )

        print(
            "Nutrition:",
            result["nutrition_utilisation"], "%"
        )

