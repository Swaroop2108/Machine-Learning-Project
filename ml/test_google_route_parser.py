import sys
from backend.services.google_route_service import decode_polyline, format_duration, map_travel_mode

def test_google_route_utils():
    print("=== TESTING GOOGLE ROUTE PARSER UTILITIES ===")
    
    # Test polyline decoding
    poly_str = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    decoded = decode_polyline(poly_str)
    print(f"Decoded Polyline Count: {len(decoded)}")
    assert len(decoded) > 0, "Polyline decode failed!"
    print(f"Sample decoded coordinate: {decoded[0]}")
    
    # Test duration formatting
    assert format_duration(19140) == "5h 19m", f"Duration format failed! Got: {format_duration(19140)}"
    assert format_duration(2700) == "45 mins", f"Duration format failed! Got: {format_duration(2700)}"
    print("[SUCCESS] Duration formatting verified: 19140s -> '5h 19m', 2700s -> '45 mins'")
    
    # Test travel mode mapping
    assert map_travel_mode("car") == "DRIVE"
    assert map_travel_mode("bike") == "TWO_WHEELER"
    assert map_travel_mode("transit") == "TRANSIT"
    assert map_travel_mode("walk") == "WALK"
    print("[SUCCESS] Travel mode mapping verified: car -> DRIVE, bike -> TWO_WHEELER, transit -> TRANSIT, walk -> WALK")

if __name__ == "__main__":
    test_google_route_utils()
