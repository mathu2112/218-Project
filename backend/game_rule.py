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

def allocate_request(request, allocated, hub_resources):
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

    return check_request_fulfilment(required, allocated)

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

game_requests = get_requests(requests)
daily_stock = get_stock(stock, "2025-10-01")
daily_flights = get_flights(flights, "2025-10-01")

print("Emergency requests:", len(game_requests))
print("\nAvailable stock:")
print(daily_stock)

print("\nAvailable transport:")
print(daily_flights)

print("\nSupply hubs:")
print(hubs[["hub_id", "hub_name"]].to_string(index=False))

print("\nHubs assigned to emergency requests:")
print(requests["supply_hub"].value_counts())

hub_stock, hub_flights = get_hub_resources(
    daily_stock, daily_flights, "HUB-ARI"
)

print("\nEl Arish stock:")
print(hub_stock.to_string(index=False))

print("\nEl Arish transport:")
print(hub_flights.to_string(index=False))


# Select the first emergency request
request = requests.iloc[0]

print("\nSelected emergency request:")
print("Request ID:", request["request_id"])
print("Location:", request["location"])
print("Assigned hub:", request["supply_hub"])

# Get resources from the assigned hub
hub_stock, hub_flights = get_hub_resources(
    daily_stock,
    daily_flights,
    request["supply_hub"]
)

print("\nAvailable stock for this request:")
print(hub_stock.to_string(index=False))

print("\nAvailable transport for this request:")
print(hub_flights.to_string(index=False))

# Get the resources required by the selected request
required = [
    int(request["medicine_required_kits"]),
    int(request["shelter_required_kits"]),
    int(request["nutrition_required_parcels"])
]

# Get available resources from the assigned hub
available = [
    int(hub_stock.iloc[0]["medicine_stock_kits"]),
    int(hub_stock.iloc[0]["shelter_stock_kits"]),
    int(hub_stock.iloc[0]["nutrition_stock_parcels"])
]

print("\nRequired resources:", required)
print("Available resources:", available)

# Player allocates approximately half of each resource
allocated = [
    required[0] // 2,
    required[1] // 2,
    required[2] // 2
]

capacity = float(hub_flights.iloc[0]["total_capacity_tonnes"])
slots = int(hub_flights.iloc[0]["flight_slots_available"])

reset_game()
start_game()

result = allocate_resources(required, available, allocated, capacity, slots)

print("\nAllocated resources:", allocated)
print("Allocation result:", result)

if result is not None:
    remaining_stock, remaining_capacity, remaining_slots = result

    print("Remaining stock:", remaining_stock)
    print("Remaining capacity:", remaining_capacity)
    print("Remaining slots:", remaining_slots)
    print("Request status:", check_request_fulfilment(required, allocated))


selected_date = "2025-10-01"

daily_requests = get_requests_by_date(requests, selected_date)

print("\nRequests for", selected_date)
print("Number of requests:", len(daily_requests))
print(daily_requests[["request_id", "request_datetime", "supply_hub"]].head())

print("\nDaily emergency requests:")

columns = [
    "request_id",
    "supply_hub",
    "medicine_required_kits",
    "shelter_required_kits",
    "nutrition_required_parcels",
    "urgency_level",
    "severity_level"
]

print(daily_requests[columns].to_string(index=False))

# Store available resources for each hub
hub_resources = {}

for _, row in daily_stock.iterrows():
    hub_id = row["hub_id"]

    transport = daily_flights[
        daily_flights["hub_id"] == hub_id
    ].iloc[0]

    hub_resources[hub_id] = {
        "stock": [
            int(row["medicine_stock_kits"]),
            int(row["shelter_stock_kits"]),
            int(row["nutrition_stock_parcels"])
        ],
        "capacity": float(transport["total_capacity_tonnes"]),
        "slots": int(transport["flight_slots_available"])
    }

print("\nResources by hub:")

for hub_id, resources in hub_resources.items():
    print(hub_id, resources)


reset_game()
start_game()

request = daily_requests[
    daily_requests["request_id"] == "REQ-00003"
].iloc[0]

allocated = [100, 50, 100]

status = allocate_request(request, allocated, hub_resources)

print("\nRequest:", request["request_id"])
print("Allocation:", allocated)
print("Status:", status)
print("Remaining HUB-ARI resources:", hub_resources["HUB-ARI"])

request2 = daily_requests[
    daily_requests["request_id"] == "REQ-00001"
].iloc[0]

allocated2 = [2, 4, 200]

status2 = allocate_request(request2, allocated2, hub_resources)

print("\nRequest:", request2["request_id"])
print("Allocation:", allocated2)
print("Status:", status2)
print("Remaining HUB-ARI resources:", hub_resources["HUB-ARI"])

allocation_history = []

record1 = record_allocation(request, allocated, status)
record2 = record_allocation(request2, allocated2, status2)

allocation_history.append(record1)
allocation_history.append(record2)

print("\nAllocation History:")

for record in allocation_history:
    print(record)