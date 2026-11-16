#GAME ENGINE 

# Initial game state
game_state = "READY"

# Start the simulation
def start_game():
    global game_state

    if game_state == "READY":
        game_state = "ALLOCATING"

    return game_state


# End the simulation
def end_game():
    global game_state

    if game_state == "ALLOCATING":
        game_state = "COMPLETE"

    return game_state


# Reset the game state
def reset_game():
    global game_state

    game_state = "READY"

    return game_state

# Check if the player is allowed to allocate resources
def can_allocate():
    return game_state == "ALLOCATING"



#GAME RULES

#Check is the allocation is valid based on required, available, and amount of resources
def check_allocation(required, available, amount):
    if amount < 0:
        return False

    if amount > required:
        return False

    if amount > available:
        return False

    return True



# Update the stock level based on the amount allocated
def update_stock(available, amount):
    remaining = available - amount
    return remaining


# Check the fulfilment status of a request
def check_fulfilment(required, allocated):
    if allocated == 0:
        return "Unfulfilled"

    if allocated < required:
        return "Partially Fulfilled"

    return "Fulfilled"


# Check the overall fulfilment status of a request
def check_request_fulfilment(required, allocated):
    if all(allocated[i] >= required[i] for i in range(3)):
        return "Fulfilled"

    if all(allocated[i] == 0 for i in range(3)):
        return "Unfulfilled"

    return "Partially Fulfilled"


# Calculate the total weight of allocated resources
def calculate_weight(allocated):
    weights = [0.01, 0.05, 0.02]

    total_weight = 0

    for i in range(3):
        total_weight += allocated[i] * weights[i]

    return total_weight

# Check whether the allocation fits within transport capacity
# Check whether the allocation fits within transport capacity
def check_transport_capacity(allocated, capacity):
    total_weight = calculate_weight(allocated)

    return total_weight <= capacity


# Check if a transport slot is available
def check_transport_slots(available_slots):
    return available_slots > 0


# Update transport slots after a delivery
def update_transport_slots(available_slots):
    return available_slots - 1



""" Allocate resources if stock and transport are available and only 
if player is allowed to allocate and return remaining stock, remaining
transport capacity and remaining slots """
def allocate_resources(required, available, allocated, capacity, slots):
    if not can_allocate():
        return None

    for i in range(3):
        if not check_allocation(required[i], available[i], allocated[i]):
            return None

    if not check_transport_capacity(allocated, capacity):
        return None

    if not check_transport_slots(slots):
        return None

    remaining_stock = []

    for i in range(3):
        remaining = update_stock(available[i], allocated[i])
        remaining_stock.append(remaining)

    remaining_capacity = capacity - calculate_weight(allocated)
    remaining_slots = update_transport_slots(slots)

    return remaining_stock, remaining_capacity, remaining_slots

# Get available stock and transport for a selected hub
def get_hub_resources(daily_stock, daily_flights, hub_id):
    hub_stock = daily_stock[daily_stock["hub_id"] == hub_id]
    hub_flights = daily_flights[daily_flights["hub_id"] == hub_id]

    return hub_stock, hub_flights

    """Process a player's resource allocation for an emergency request.
    Check if the allocation is valid, update the remaining hub
    resources, and automatically record the successful allocation.
    Return the request's fulfilment status or "Allocation Failed"
    if the allocation is invalid. """
def allocate_request(request, allocated, hub_resources, allocation_history):
    hub_id = request["supply_hub"]

    required = [
        int(request["medicine_required_kits"]),
        int(request["shelter_required_kits"]),
        int(request["nutrition_required_parcels"])
    ]

    resources = hub_resources[hub_id]

    result = allocate_resources(
        required,
        resources["stock"],
        allocated,
        resources["capacity"],
        resources["slots"]
    )

    if result is None:
        return "Allocation Failed"

    remaining_stock, remaining_capacity, remaining_slots = result

    resources["stock"] = remaining_stock
    resources["capacity"] = remaining_capacity
    resources["slots"] = remaining_slots

    status = check_request_fulfilment(required, allocated)

    # Automatically save successful allocation
    record = record_allocation(request, allocated, status)
    allocation_history.append(record)

    return status

def record_allocation(request, allocated, status):
    record = {
        "request_id": request["request_id"],
        "supply_hub": request["supply_hub"],
        "medicine_allocated": allocated[0],
        "shelter_allocated": allocated[1],
        "nutrition_allocated": allocated[2],
        "status": status
    }

    return record

from backend.load_data import load_data, get_requests, get_stock, get_flights, get_requests_by_date

requests, locations, hubs, stock, flights = load_data()
