import copy
import random
from fractions import Fraction
from math import isnan

from fastapi import FastAPI

from backend.evaluation.experiments import (
    compare_strategies,
    run_current_backend_evaluation,
)
from backend.evaluation.metrics import get_request_status
from backend.load_data import load_data, get_requests
from backend.game_rule import (
    check_request_fulfilment,
    calculate_weight,
    start_game,
    reset_game,
    end_game,
    allocate_request,
    can_allocate,
    get_game_state,
)
from backend.fuzzy_logic import (
    suggest_allocation,
    explain_recommendation,
    check_suggestion_transport,
    adjust_for_transport,
)


# --------------------------------------------------
# 1. BACKEND SETUP AND GAME DATA
# --------------------------------------------------

app = FastAPI()

# Load the dataset once when the backend starts
requests, _, hubs, stock, flights = load_data()

# Store player allocations and the current hub resources
allocation_history = []
hub_resources = {}
original_hub_resources = {}

# Choose a date that contains emergency requests
active_requests = requests.loc[requests["fulfilment_status"].ne("Cancelled")]
available_dates = active_requests["request_datetime"].str[:10].dropna().unique().tolist()
slot_capacity_by_hub = hubs.set_index("hub_id")["aircraft_capacity_tonnes"].to_dict()
SUPPLY_FIELDS = (
    ("medicine_required_kits", "medicine_allocated"),
    ("shelter_required_kits", "shelter_allocated"),
    ("nutrition_required_parcels", "nutrition_allocated"),
)
selected_date = random.choice(available_dates)


# --------------------------------------------------
# 2. GAME DATA HELPER FUNCTIONS
# --------------------------------------------------

def load_hub_resources():
    # Load stock and flights for the current game date
    daily_stock = stock[stock["date"] == selected_date]
    daily_flights = flights[flights["date"] == selected_date]

    # Clear resources from the previous game
    hub_resources.clear()
    original_hub_resources.clear()

    for _, hub in daily_stock.iterrows():
        hub_id = hub["hub_id"]

        # Find the matching flight data for this hub
        hub_flight = daily_flights[daily_flights["hub_id"] == hub_id]
        if hub_flight.empty:
            continue

        hub_flight = hub_flight.iloc[0]

        # Save the stock and transport limits
        hub_resources[hub_id] = {
            "stock": [
                int(hub["medicine_stock_kits"]),
                int(hub["shelter_stock_kits"]),
                int(hub["nutrition_stock_parcels"]),
            ],
            "capacity": float(hub_flight["total_capacity_tonnes"]),
            "slots": int(hub_flight["flight_slots_available"]),
            "slot_capacity": float(slot_capacity_by_hub[hub_id]),
        }

    # Keep the original values for AI simulation and resets
    original_hub_resources.update(copy.deepcopy(hub_resources))


def get_daily_requests():
    on_selected_date = active_requests["request_datetime"].str[:10] == selected_date
    return active_requests.loc[on_selected_date].copy()


def get_total_demand(hub_id):
    # Find all requests assigned to the same hub
    daily_requests = get_daily_requests()
    hub_requests = daily_requests[daily_requests["supply_hub"] == hub_id]

    # Total demand for medicine, shelter, and nutrition
    return [
        int(hub_requests["medicine_required_kits"].fillna(0).sum()),
        int(hub_requests["shelter_required_kits"].fillna(0).sum()),
        int(hub_requests["nutrition_required_parcels"].fillna(0).sum()),
    ]


def get_ai_resources():
    # Give the AI its own copy of the starting resources
    return copy.deepcopy(original_hub_resources)


def get_sorted_requests():
    # Process Critical requests before High, Medium, and Low
    daily_requests = get_daily_requests()
    priority_order = {"Critical": 1, "High": 2, "Medium": 3, "Low": 4}

    daily_requests["priority_order"] = (
        daily_requests["expert_priority_label"].map(priority_order)
    )

    # Use request time to break ties within the same priority
    return daily_requests.sort_values(
        by=["priority_order", "request_datetime"],
        na_position="last",
    )


# Load resources for the first randomly selected date
load_hub_resources()


# --------------------------------------------------
# 3. INDEPENDENT AI SIMULATION
# --------------------------------------------------

def simulate_ai():
    # The AI must not change the player's resources
    ai_resources = get_ai_resources()
    ai_history = []

    # Allocate resources to requests in priority order
    for _, request in get_sorted_requests().iterrows():
        hub_id = request["supply_hub"]

        required = [
            int(request["medicine_required_kits"]),
            int(request["shelter_required_kits"]),
            int(request["nutrition_required_parcels"]),
        ]
        priority = request["expert_priority_label"]

        # Record requests with missing hub data as unfulfilled
        if hub_id not in ai_resources:
            ai_history.append({
                "request_id": request["request_id"],
                "supply_hub": hub_id,
                "expert_priority_label": priority,
                "medicine_allocated": 0,
                "shelter_allocated": 0,
                "nutrition_allocated": 0,
                "status": "Unfulfilled",
            })
            continue

        # Use the AI's remaining resources for this hub
        resources = ai_resources[hub_id]

        # Use fuzzy logic to recommend quantities for this request
        suggested = suggest_allocation(
            required,
            resources["stock"],
            priority,
            get_total_demand(hub_id),
        )

        # Reduce quantities if transport capacity is limited
        suggested = adjust_for_transport(
            suggested,
            min(resources["capacity"], resources["slot_capacity"]),
            resources["slots"],
        )

        # Only use stock and a flight slot when something is sent
        if resources["slots"] > 0 and any(amount > 0 for amount in suggested):
            for i in range(3):
                resources["stock"][i] -= suggested[i]

            resources["capacity"] = round(resources["capacity"] - calculate_weight(suggested), 2)
            resources["slots"] -= 1

        # Record the outcome for evaluation
        status = check_request_fulfilment(required, suggested)
        ai_history.append({
            "request_id": request["request_id"],
            "supply_hub": hub_id,
            "expert_priority_label": priority,
            "medicine_allocated": suggested[0],
            "shelter_allocated": suggested[1],
            "nutrition_allocated": suggested[2],
            "status": status,
        })

    return ai_history


# --------------------------------------------------
# 4. GENERAL GAME ENDPOINTS
# --------------------------------------------------

@app.get("/")
def home():
    # Check that the backend is running
    return {"message": "Gaza Humanitarian Air Bridge Backend is running"}


@app.get("/game-date")
def show_game_date():
    return {"selected_date": selected_date}


@app.get("/game-status")
def show_game_status():
    return {"game_state": get_game_state()}


@app.get("/requests")
def show_requests():
    # Send the current day's requests to the frontend
    request_data = get_requests(get_daily_requests())
    return request_data.fillna("").to_dict(orient="records")


@app.get("/resources")
def show_resources():
    # Send the player's remaining hub resources
    return hub_resources


@app.post("/start")
def start():
    # A completed game must be reset before starting again
    if get_game_state() == "COMPLETE":
        return {"error": "Game is complete. Reset before starting again"}

    return {"game_state": start_game()}


@app.post("/reset")
def reset():
    global selected_date

    # Clear previous allocations and return to READY
    state = reset_game()
    allocation_history.clear()

    # Select a new scenario and load its resources
    selected_date = random.choice(available_dates)
    load_hub_resources()

    return {"game_state": state, "selected_date": selected_date}


@app.post("/finish")
def finish():
    return {"game_state": end_game()}


# --------------------------------------------------
# 5. FUZZY AI RECOMMENDATION ENDPOINT
# --------------------------------------------------

@app.get("/recommendation/{request_id}")
def get_recommendation(request_id: str):
    # Find the requested emergency
    daily_requests = get_daily_requests()
    matching = daily_requests.loc[daily_requests["request_id"] == request_id]
    if matching.empty:
        return {"error": "Request not found"}

    request = matching.iloc[0]
    hub_id = request["supply_hub"]
    priority = request["expert_priority_label"]

    required = [
        int(request["medicine_required_kits"]),
        int(request["shelter_required_kits"]),
        int(request["nutrition_required_parcels"]),
    ]

    if hub_id not in hub_resources:
        return {"error": "Supply hub not found"}

    resources = hub_resources[hub_id]

    # Calculate the fuzzy recommendation using remaining player stock
    suggested = suggest_allocation(
        required,
        resources["stock"],
        priority,
        get_total_demand(hub_id),
    )

    # Fit the recommendation within transport limits
    suggested = adjust_for_transport(
        suggested,
        min(resources["capacity"], resources["slot_capacity"]),
        resources["slots"],
    )

    # Explain the final recommended quantities
    explanation = explain_recommendation(priority, required, suggested)

    # Check whether transport is available
    capacity = min(resources["capacity"], resources["slot_capacity"])
    slots = resources["slots"]
    transport_ok = capacity > 0 and check_suggestion_transport(suggested, capacity, slots)

    if slots <= 0:
        transport_message = "No flight slots are available."
    elif not transport_ok:
        transport_message = "Not enough flight capacity for this allocation."
    else:
        transport_message = "Transport is available."

    return {
        "request_id": request_id,
        "supply_hub": hub_id,
        "expert_priority_label": priority,
        "transport_available": transport_ok,
        "transport_message": transport_message,
        "explanation": explanation,
        "suggested_allocation": {
            "medicine": suggested[0],
            "shelter": suggested[1],
            "nutrition": suggested[2],
        },
    }


# --------------------------------------------------
# 6. PLAYER ALLOCATION ENDPOINT
# --------------------------------------------------

@app.post("/allocate")
def allocate(data: dict):
    # Only allow allocations after the game starts
    if not can_allocate():
        return {"error": "Start the game before allocating resources"}

    # Check that the request ID was provided
    request_id = data.get("request_id")
    if not request_id:
        return {"error": "Request ID is required"}

    # Check that all three resource quantities were provided
    if any(key not in data for key in ("medicine", "shelter", "nutrition")):
        return {"error": "Medicine, shelter and nutrition quantities are required"}

    allocated = [data["medicine"], data["shelter"], data["nutrition"]]
    if any(type(amount) is not int or amount < 0 for amount in allocated):
        return {"error": "Enter a non-negative whole number for each resource."}

    if not any(allocated):
        return {"error": "You must allocate at least one resource"}

    # Find the request in the dataset
    daily_requests = get_daily_requests()
    matching = daily_requests.loc[daily_requests["request_id"] == request_id]
    if matching.empty:
        return {"error": "Request not found"}

    # A request can only be allocated once
    for record in allocation_history:
        if record["request_id"] == request_id:
            return {"error": "This request has already been allocated"}

    request = matching.iloc[0].to_dict()

    if request["supply_hub"] not in hub_resources:
        return {"error": "Supply hub not found"}

    # A single dispatch must fit one slot as well as the hub's daily budget.
    resources = hub_resources[request["supply_hub"]]
    if round(calculate_weight(allocated), 2) > resources["slot_capacity"]:
        return {"error": "The allocation exceeds the capacity of one dispatch"}

    # Apply game rules and save the player's allocation
    status = allocate_request(
        request,
        allocated,
        hub_resources,
        allocation_history,
    )

    if status == "Allocation Failed":
        return {
            "error": "Allocation failed due to insufficient resources or transport capacity"
        }

    return {"request_id": request_id, "status": status}


# --------------------------------------------------
# 7. RESULTS ENDPOINTS
# --------------------------------------------------

@app.get("/ai-results")
def get_ai_results():
    # Run the independent AI simulation for the selected date
    ai_results = simulate_ai()
    return {
        "selected_date": selected_date,
        "total_requests": len(get_sorted_requests()),
        "total_ai_results": len(ai_results),
        "ai_allocations": ai_results,
    }


@app.get("/results")
def show_results():
    # Return the player's recorded allocations
    return {
        "total_allocations": len(allocation_history),
        "allocations": allocation_history,
    }


@app.get("/hub-resources")
def show_hub_resources():
    # Extra endpoint for checking the player's remaining resources
    return hub_resources


# --------------------------------------------------
# 8. EVALUATION OF AI AND PLAYER DECISIONS
# --------------------------------------------------

def prepare_evaluation_allocations(history):
    """Score every active request, including those that received no aid."""
    recorded = {record["request_id"]: record for record in history}
    evaluated = []

    for _, request in get_daily_requests().iterrows():
        request_id = request["request_id"]
        allocation = recorded.get(request_id, {})
        population = int(request["population_affected"])
        row = {
            "request_id": request_id,
            "supply_hub": request["supply_hub"],
            "expert_priority_label": request["expert_priority_label"],
            "location": request["location"],
            "population_affected": population,
        }

        coverage = []
        dispatched = False
        for required_field, allocated_field in SUPPLY_FIELDS:
            required = int(request[required_field])
            delivered = int(allocation.get(allocated_field, 0))
            row[required_field] = required
            row[allocated_field] = delivered
            dispatched = dispatched or delivered > 0
            if required > 0:
                coverage.append(Fraction(delivered, required))

        # The least fulfilled required supply limits estimated coverage.
        row["beneficiaries_served"] = int(population * min(coverage, default=0))

        # Use the same lateness estimate for all strategies, without a queue model.
        row["delivery_delay_hours"] = None
        if dispatched:
            travel_hours = float(request["estimated_delivery_time_hours"])
            if isnan(travel_hours):
                travel_hours = 6.0
            target_hours = float(request["time_sensitivity_hours"])
            row["delivery_delay_hours"] = max(0.0, travel_hours - target_hours)

        evaluated.append(row)

    return evaluated


def add_scenario_metrics(metrics, allocations):
    """Add the course-specific measures to the shared evaluation output."""
    critical_statuses = [
        get_request_status(row)
        for row in allocations
        if row["expert_priority_label"] == "Critical"
    ]
    critical_total = len(critical_statuses)
    fulfilled = critical_statuses.count("Fulfilled")
    metrics["critical_fulfilment"] = {
        "total_critical_requests": critical_total,
        "fulfilled_critical_requests": fulfilled,
        "partially_fulfilled_critical_requests": critical_statuses.count("Partially Fulfilled"),
        "unfulfilled_critical_requests": critical_statuses.count("Unfulfilled"),
        "critical_fulfilment_rate": round(100 * fulfilled / critical_total, 2)
        if critical_total else 0,
    }

    location_totals = {}
    for row in allocations:
        totals = location_totals.setdefault(row["location"], {"served": 0, "population": 0})
        totals["served"] += row["beneficiaries_served"]
        totals["population"] += row["population_affected"]

    coverage = {
        location: 100 * totals["served"] / totals["population"]
        for location, totals in location_totals.items()
        if totals["population"] > 0
    }
    metrics["location_fairness"] = {
        "coverage_by_location": {
            location: round(rate, 2) for location, rate in coverage.items()
        },
        "coverage_gap_pp": round(max(coverage.values()) - min(coverage.values()), 2)
        if len(coverage) > 1 else None,
    }


def get_initial_stock_totals():
    """Use the same starting stock when evaluating both strategies."""
    totals = {"medicine": 0, "shelter": 0, "nutrition": 0}
    for resources in original_hub_resources.values():
        totals["medicine"] += resources["stock"][0]
        totals["shelter"] += resources["stock"][1]
        totals["nutrition"] += resources["stock"][2]
    return totals


@app.get("/evaluation")
def get_evaluation():
    """Compare the player and fuzzy AI with the dataset's recorded allocations."""
    ai_allocations = prepare_evaluation_allocations(simulate_ai())
    player_allocations = prepare_evaluation_allocations(allocation_history)

    daily_requests = get_daily_requests()
    baseline_history = [
        {
            "request_id": row.request_id,
            "medicine_allocated": int(row.medicine_allocated_kits),
            "shelter_allocated": int(row.shelter_allocated_kits),
            "nutrition_allocated": int(row.nutrition_allocated_parcels),
        }
        for row in daily_requests.itertuples(index=False)
    ]
    baseline_allocations = prepare_evaluation_allocations(baseline_history)

    # Evaluate all three strategies
    results = run_current_backend_evaluation(
        ai_allocations=ai_allocations,
        human_allocations=player_allocations,
        baseline_allocations=baseline_allocations,
        available_stock=get_initial_stock_totals(),
        scenario_name=selected_date,
    )

    # Keep the shared evaluation module compatible with its existing callers.
    for result, name, allocations in zip(
        results,
        ("AI Recommended Allocation", "Player", "Dataset Baseline"),
        (ai_allocations, player_allocations, baseline_allocations),
    ):
        result["strategy"] = name
        add_scenario_metrics(result["metrics"], allocations)

    return {
        "selected_date": selected_date,
        "game_state": get_game_state(),
        "total_requests": len(ai_allocations),
        "player_allocations_completed": len(allocation_history),
        "comparison": compare_strategies(results),
        "detailed_results": results,
    }
