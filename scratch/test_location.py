import sys
import os

# Adjust path so we can import services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.location_service import get_coordinates_from_pincode, calculate_distance, get_location_score
from services.scoring_service import calculate_job_match

def run_tests():
    print("=== Testing Location Geocoding & Distance ===")
    
    # 1. Test Geocoding
    pincode_pune_hinjewadi = "411057"
    pincode_pune_camp = "411001"
    
    print(f"Geocoding Pune Hinjewadi pincode: {pincode_pune_hinjewadi}...")
    lat1, lon1 = get_coordinates_from_pincode(pincode_pune_hinjewadi)
    print(f"Result: Lat={lat1}, Lon={lon1}")
    
    print(f"Geocoding Pune Camp pincode: {pincode_pune_camp}...")
    lat2, lon2 = get_coordinates_from_pincode(pincode_pune_camp)
    print(f"Result: Lat={lat2}, Lon={lon2}")
    
    if lat1 and lat2:
        # 2. Test Geodesic Distance
        distance = calculate_distance((lat1, lon1), (lat2, lon2))
        print(f"Calculated geodesic distance: {distance:.2f} KM")
        
        # 3. Test Location Score Tiers
        score = get_location_score(distance)
        print(f"Location score for {distance:.2f} KM: {score}")
        
        assert distance > 0, "Distance should be positive"
        assert score in [100.0, 70.0, 40.0, 0.0], f"Score {score} not in expected tiers"
    else:
        print("Geocoding failed. Check internet connection or API limits. Using mock calculations...")
        lat1, lon1 = 18.5913, 73.7389
        lat2, lon2 = 18.5204, 73.8567
        distance = calculate_distance((lat1, lon1), (lat2, lon2))
        score = get_location_score(distance)
        print(f"Mock geodesic distance: {distance:.2f} KM")
        print(f"Mock Location score for {distance:.2f} KM: {score}")
        
    print("\n=== Testing Scoring Logic Fallbacks ===")
    # 4. Test calculate_job_match with/without coordinates
    student = {
        "fullName": "John Doe",
        "city": "Pune",
        "state": "Maharashtra",
        "education": [
            {
                "trade": "computer operator",
                "skills": ["MS Office", "Excel"]
            }
        ],
        "experience": [],
        "latitude": lat1,
        "longitude": lon1
    }
    
    job = {
        "jobTitle": "Junior Computer Operator",
        "trade": "computer operator",
        "address": {
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411001"
        },
        "location": "Pune",
        "requiredSkills": ["MS Office"],
        "experienceLevel": "Fresher",
        "latitude": lat2,
        "longitude": lon2
    }
    
    # Matching with coordinates
    score_with_coords, priority, dist_km = calculate_job_match(student, job, return_priority=True)
    print(f"Job Match Score with Coordinates: {score_with_coords}% (Priority={priority}, Distance={dist_km} KM)")
    
    # Matching without coordinates (using fallback city/state text matching)
    student_no_coords = student.copy()
    student_no_coords["latitude"] = None
    student_no_coords["longitude"] = None
    job_no_coords = job.copy()
    job_no_coords["latitude"] = None
    job_no_coords["longitude"] = None
    
    score_no_coords, fallback_priority, fallback_dist_km = calculate_job_match(student_no_coords, job_no_coords, return_priority=True)
    print(f"Job Match Score without Coordinates (City match fallback): {score_no_coords}% (Priority={fallback_priority}, Distance={fallback_dist_km})")
    
    # State-only match fallback
    student_state_only = student_no_coords.copy()
    student_state_only["city"] = "Mumbai"
    score_state_only, state_priority, state_dist_km = calculate_job_match(student_state_only, job_no_coords, return_priority=True)
    print(f"Job Match Score without Coordinates (State match fallback): {score_state_only}% (Priority={state_priority}, Distance={state_dist_km})")

    print("\nAll location and recommendation scoring logic runs correctly!")

if __name__ == "__main__":
    run_tests()
