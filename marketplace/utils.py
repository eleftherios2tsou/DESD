import math
import csv
import os

POSTCODE_CACHE = {}

def harversine(lat1, lon1, lat2, lon2):
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def load_postcodes():
    global POSTCODE_CACHE
    if POSTCODE_CACHE:
        return 
    filepath = os.path.join(os.path.dirname(__file__), 'data','postcodes.csv')
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pc = row.get('Postcode', '').replace(' ', '').upper()
            try:
                POSTCODE_CACHE[pc] = (float(row['Latitude']), float(row['Longitude']))
            except (ValueError, KeyError):
                continue

def get_coordinates(postcode):
    load_postcodes()
    pc = postcode.replace(' ', '').upper()
    return POSTCODE_CACHE.get(clean)

def calculate_food_distance(customer_postcode, producer_postcode):
    customer_coords = get_coordinates(customer_postcode)
    producer_coords = get_coordinates(producer_postcode)
    if not customer_coords or not producer_coords:
        return None
    return round(harversine(customer_coords[0], customer_coords[1], producer_coords[0], producer_coords[1]), 1)