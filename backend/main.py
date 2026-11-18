import copy
import random

from fastapi import FastAPI

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
requests, locations, hubs, stock, flights = load_data()

# Store player allocations and the current hub resources
allocation_history = []
hub_resources = {}
original_hub_resources = {}

# Choose a date that contains emergency requests
available_dates = requests["request_datetime"].str[:10].dropna().unique().tolist()
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
        }

    # Keep the original values for AI simulation and resets
    original_hub_resources.update(copy.deepcopy(hub_resources))


def get_daily_requests():
    # Return only requests from the selected date
    return requests[
        requests["request_datetime"].str[:10] == selected_date
    ].copy()


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
            resources["capacity"],
            resources["slots"],
        )

        # Only use stock and a flight slot when something is sent
        if resources["slots"] > 0 and any(amount > 0 for amount in suggested):
            for i in range(3):
                resources["stock"][i] -= suggested[i]

            resources["capacity"] -= calculate_weight(suggested)
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
    matching = requests[requests["request_id"] == request_id]
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

    # Only recommend for the selected game's requests
    request_date = str(request["request_datetime"])[:10]
    if request_date != selected_date:
        return {"error": "Request is not for the selected game date"}

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
        resources["capacity"],
        resources["slots"],
    )

    # Explain the final recommended quantities
    explanation = explain_recommendation(priority, required, suggested)

    # Check whether transport is available
    capacity = resources["capacity"]
    slots = resources["slots"]
    transport_ok = check_suggestion_transport(suggested, capacity, slots)

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

    allocated = [
        int(data["medicine"]),
        int(data["shelter"]),
        int(data["nutrition"]),
    ]

    # Reject empty or negative allocations
    if allocated == [0, 0, 0]:
        return {"error": "You must allocate at least one resource"}

    if any(amount < 0 for amount in allocated):
        return {"error": "Resource quantities cannot be negative"}

    # Find the request in the dataset
    matching = requests[requests["request_id"] == request_id]
    if matching.empty:
        return {"error": "Request not found"}

    # A request can only be allocated once
    for record in allocation_history:
        if record["request_id"] == request_id:
            return {"error": "This request has already been allocated"}

    request = matching.iloc[0].to_dict()

    # Only accept requests from the current game date
    request_date = str(request["request_datetime"])[:10]
    if request_date != selected_date:
        return {"error": "Request is not for the selected game date"}

    if request["supply_hub"] not in hub_resources:
        return {"error": "Supply hub not found"}

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
