from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from typing import Tuple, Optional
import time

def get_coordinates_from_pincode(pincode: str, city: Optional[str] = None, state: Optional[str] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Converts a pincode into latitude and longitude using OpenStreetMap Nominatim API.
    Enforces local geocoding bias by appending ', India'.
    If pincode geocoding fails or is empty, falls back to City and State geocoding.
    """
    if not pincode and not city and not state:
        return None, None
    
    try:
        # User agent is required by Nominatim terms of service
        geolocator = Nominatim(user_agent="ats_ai_pincode_locator")
        
        # 1. Try Pincode first
        if pincode:
            pincode_str = str(pincode).strip()
            if pincode_str:
                query = f"{pincode_str}, India"
                # Adding a timeout of 5 seconds to prevent hangs
                location = geolocator.geocode(query, timeout=5)
                if location:
                    return float(location.latitude), float(location.longitude)
    except Exception as e:
        print(f"Geocoding error for pincode {pincode}: {e}")

    # 2. Try City + State fallback
    if city and state:
        city_str = str(city).strip()
        state_str = str(state).strip()
        if city_str and state_str:
            try:
                geolocator = Nominatim(user_agent="ats_ai_pincode_locator")
                query = f"{city_str}, {state_str}, India"
                location = geolocator.geocode(query, timeout=5)
                if location:
                    return float(location.latitude), float(location.longitude)
            except Exception as e:
                print(f"Geocoding error for city/state fallback ({city_str}, {state_str}): {e}")

    # 3. Try City only fallback
    if city:
        city_str = str(city).strip()
        if city_str:
            try:
                geolocator = Nominatim(user_agent="ats_ai_pincode_locator")
                query = f"{city_str}, India"
                location = geolocator.geocode(query, timeout=5)
                if location:
                    return float(location.latitude), float(location.longitude)
            except Exception as e:
                print(f"Geocoding error for city fallback ({city_str}): {e}")
        
    return None, None

def calculate_distance(candidate_coords: Tuple[float, float], job_coords: Tuple[float, float]) -> Optional[float]:
    """
    Calculates geodesic distance in kilometers between two coordinates.
    Safely returns None if either coordinates tuple is invalid or incomplete.
    """
    if not candidate_coords or not job_coords:
        return None
        
    try:
        lat1, lon1 = candidate_coords
        lat2, lon2 = job_coords
        
        if None in (lat1, lon1, lat2, lon2):
            return None
            
        distance = geodesic((lat1, lon1), (lat2, lon2)).km
        return float(distance)
    except Exception as e:
        print(f"Error calculating geodesic distance: {e}")
        
    return None

def get_location_score(distance_km: float) -> float:
    """
    Converts a distance in KM into a location recommendation score.
    Logic:
    * Distance <= 10 KM -> 100
    * Distance <= 50 KM -> 70
    * Distance <= 200 KM -> 40
    * Distance > 200 KM -> 0
    """
    if distance_km is None:
        return 0.0
        
    try:
        dist = float(distance_km)
        if dist <= 10.0:
            return 100.0
        elif dist <= 50.0:
            return 70.0
        elif dist <= 200.0:
            return 40.0
        else:
            return 0.0
    except Exception:
        return 0.0
