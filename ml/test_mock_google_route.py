from unittest.mock import patch, MagicMock
from backend.services.google_route_service import compute_google_route

def test_mock_google_routes_api():
    print("=== TESTING MOCK GOOGLE ROUTES API RESPONSE ===")

    mock_routes_response = {
        "routes": [
            {
                "duration": "19140s",
                "distanceMeters": 273500,
                "polyline": {
                    "encodedPolyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
                }
            }
        ]
    }

    with patch("backend.services.google_route_service.GOOGLE_MAPS_API_KEY", "MOCK_TEST_KEY"):
        with patch("requests.post") as mock_post:
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.json.return_value = mock_routes_response
            mock_post.return_value = mock_res

            res = compute_google_route(
                source="Hyderabad",
                destination="Vijayawada",
                departure_datetime_str="2026-09-03T09:00:00",
                travel_mode="DRIVE"
            )

            print(f"Mock Response Result: {res}")
            assert res["success"] is True
            assert "google_route" in res
            gr = res["google_route"]
            assert gr["duration_seconds"] == 19140.0
            assert gr["duration_minutes"] == 319.0
            assert gr["duration_text"] == "5h 19m"
            assert gr["distance_km"] == 273.5
            assert gr["departure_time"] == "09:00 AM"
            assert gr["estimated_arrival_time"] == "02:19 PM"
            print("[SUCCESS] Mock Google Routes API response parsing verified!")

if __name__ == "__main__":
    test_mock_google_routes_api()
