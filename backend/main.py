from fastapi import FastAPI
from backend.load_data import load_data, get_requests
from backend.game_rule import start_game, reset_game, end_game, allocate_request, can_allocate, get_game_state
from backend.fuzzy_logic import calculate_priority, explain_recommendation, suggest_allocation, check_suggestion_transport

# Create the backend API
app = FastAPI()


# Test whether the backend is running
@app.get("/")
def home():
    return {"message": "Gaza Humanitarian Air Bridge Backend is running"}


# Load emergency requests
requests, locations, hubs, stock, flights = load_data()
# Store the player's successful allocations
allocation_history = []
# Store available resources for each supply hub
hub_resources = {}
# Save the original hub resources for resetting
original_hub_resources = {}
# Choose the date for the game
selected_date = "2025-10-01"

# Get stock and flights for the selected date
daily_stock = stock[stock["date"] == selected_date]
daily_flights = flights[flights["date"] == selected_date]

# Store each hub's resources
for _, hub in daily_stock.iterrows():

    hub_id = hub["hub_id"]

    hub_flight = daily_flights[daily_flights["hub_id"] == hub_id]

    if hub_flight.empty:
        continue

    hub_flight = hub_flight.iloc[0]

    hub_resources[hub_id] = {
        "stock": [
            int(hub["medicine_stock_kits"]),
            int(hub["shelter_stock_kits"]),
            int(hub["nutrition_stock_parcels"])
        ],
        "capacity": float(hub_flight["total_capacity_tonnes"]),
        "slots": int(hub_flight["flight_slots_available"])
    }
# Keep a separate copy of the starting resources
for hub_id in hub_resources:
    original_hub_resources[hub_id] = {
        "stock": hub_resources[hub_id]["stock"].copy(),
        "capacity": hub_resources[hub_id]["capacity"],
        "slots": hub_resources[hub_id]["slots"]
    }

# Send emergency requests for the selected game date
@app.get("/requests")
def show_requests():

    # Get only requests for the current game date
    daily_requests = requests[
        requests["request_datetime"].str[:10] == selected_date
    ]

    request_data = get_requests(daily_requests)

    return request_data.fillna("").to_dict(orient="records")

# Send current available resources to the frontend
@app.get("/resources")
def show_resources():
    return hub_resources
    
    
# Start the game
@app.post("/start")
def start():

    if get_game_state() == "COMPLETE":
        return {"error": "Game is complete. Reset before starting again"}

    state = start_game()
    return {"game_state": state}

# Get AI recommendation for a request
@app.get("/recommendation/{request_id}")
def get_recommendation(request_id: str):

    matching = requests[requests["request_id"] == request_id]

    if matching.empty:
        return {"error": "Request not found"}

    request = matching.iloc[0]
    hub_id = request["supply_hub"]

    priority = calculate_priority(
        request["urgency_level"],
        request["severity_level"],
        request["population_affected"]
    )

    explanation = explain_recommendation(priority)

    required = [
        int(request["medicine_required_kits"]),
        int(request["shelter_required_kits"]),
        int(request["nutrition_required_parcels"])
    ]

    # Check that the request belongs to the current game date
    request_date = str(request["request_datetime"])[:10]

    if request_date != selected_date:
        return {"error": "Request is not for the selected game date"}

    # Get the remaining stock from the hub
    if hub_id not in hub_resources:
        return {"error": "Supply hub not found"}

    available = hub_resources[hub_id]["stock"]

    suggested = suggest_allocation(required, available, priority)
    # Get the remaining flight capacity and slots
    capacity = hub_resources[hub_id]["capacity"]
    slots = hub_resources[hub_id]["slots"]
    transport_ok = check_suggestion_transport(suggested, capacity, slots)
    # Explain transport availability
    if slots <= 0:
        transport_message = "No flight slots are available."
    elif not transport_ok:
        transport_message = "Not enough flight capacity for this allocation."
    else:
        transport_message = "Transport is available."


    return {
        "request_id": request_id,
        "supply_hub": hub_id,
        "priority_score": priority,
        "transport_available": transport_ok,
        "transport_message": transport_message,
        "explanation": explanation,
        "suggested_allocation": {
            "medicine": suggested[0],
            "shelter": suggested[1],
            "nutrition": suggested[2]
        }
    }
    
# Reset the game
@app.post("/reset")
def reset():
    state = reset_game()
    allocation_history.clear()

    hub_resources.clear()

    for hub_id in original_hub_resources:
        hub_resources[hub_id] = {
            "stock": original_hub_resources[hub_id]["stock"].copy(),
            "capacity": original_hub_resources[hub_id]["capacity"],
            "slots": original_hub_resources[hub_id]["slots"]
        }

    return {"game_state": state}

# Finish the game
@app.post("/finish")
def finish():
    state = end_game()
    return {"game_state": state}

# Receive the player's allocation
@app.post("/allocate")
def allocate(data: dict):

    # Only allow allocations while the game is running
    if not can_allocate():
        return {"error": "Start the game before allocating resources"}

    request_id = data["request_id"]

    allocated = [
        int(data["medicine"]),
        int(data["shelter"]),
        int(data["nutrition"])
    ]
    # Prevent allocations with no supplies
    if allocated == [0, 0, 0]:
        return {"error": "You must allocate at least one resource"}

    # Prevent negative resource quantities
    if any(amount < 0 for amount in allocated):
        return {"error": "Resource quantities cannot be negative"}

    matching = requests[requests["request_id"] == request_id]

    if matching.empty:
        return {"error": "Request not found"}

    # Prevent allocating the same request twice
    for record in allocation_history:
        if record["request_id"] == request_id:
            return {"error": "This request has already been allocated"}

    request = matching.iloc[0].to_dict()

    # Check that the request belongs to the selected game date
    request_date = str(request["request_datetime"])[:10]

    if request_date != selected_date:
        return {"error": "Request is not for the selected game date"}

    if request["supply_hub"] not in hub_resources:
        return {"error": "Supply hub not found"}

    status = allocate_request(
        request,
        allocated,
        hub_resources,
        allocation_history
    )

    return {
        "request_id": request_id,
        "status": status
    }
    
# Send allocation results to the frontend
@app.get("/results")
def show_results():
    return {
        "total_allocations": len(allocation_history),
        "allocations": allocation_history
    }
    
# Temporary test to check remaining hub resources
@app.get("/hub-resources")
def show_hub_resources():
    return hub_resources

# Send the current game state to the frontend
@app.get("/game-status")
def show_game_status():
    return {"game_state": get_game_state()}

# Send the selected game date to the frontend
@app.get("/game-date")
def show_game_date():
    return {"selected_date": selected_date}