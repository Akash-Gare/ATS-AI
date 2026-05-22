import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.location_service import get_coordinates_from_pincode

# Test geocoding with fallbacks
pincodes_and_cities = [
    {"pincode": "400053", "city": "Mumbai", "state": "Maharashtra"},
    {"pincode": "411069", "city": "Pune", "state": "Maharashtra"},
    {"pincode": "411005", "city": "Pune", "state": "Maharashtra"},
    {"pincode": "411001", "city": "Pune", "state": "Maharashtra"},
    {"pincode": "414602", "city": "Ahmadnagar District", "state": "Maharashtra"}
]

for item in pincodes_and_cities:
    lat, lon = get_coordinates_from_pincode(item["pincode"], item["city"], item["state"])
    print(f"Pincode {item['pincode']} ({item['city']}, {item['state']}) -> Lat={lat}, Lon={lon}")
