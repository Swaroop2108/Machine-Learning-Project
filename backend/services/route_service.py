import requests
import math
import json
import urllib.parse
import urllib.request
from typing import Optional, List, Dict, Any, Tuple
from backend.config import ROUTE_API_KEY

# Known coordinates dictionary for fast offline/cache lookup of Indian & international cities
CITY_COORDINATES = {
    "hyderabad": (17.3850, 78.4867),
    "vijayawada": (16.5062, 80.6480),
    "myapur": (17.4968, 78.3614),
    "miyapur": (17.4968, 78.3614),
    "kukatpally": (17.4849, 78.4071),
    "visakhapatnam": (17.6868, 83.2185),
    "vizag": (17.6868, 83.2185),
    "tirupati": (13.6288, 79.4192),
    "guntur": (16.3067, 80.4365),
    "mumbai": (19.0760, 72.8777),
    "pune": (18.5204, 73.8567),
    "delhi": (28.6139, 77.2090),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "mysore": (12.2958, 76.6394),
    "mysuru": (12.2958, 76.6394),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "ahmedabad": (23.0225, 72.5714),
    "jaipur": (26.9124, 75.7873),
    "new york": (40.7128, -74.0060),
    "london": (51.5074, -0.1278),
}

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance between two coordinates in km.
    Applies a 1.25 multiplier to estimate actual driving road distance.
    """
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    straight_dist = R * c
    driving_dist = straight_dist * 1.25
    return round(max(driving_dist, 1.5), 2)

def geocode_location(location_name: str):
    """
    Geocodes location string into (lat, lon, display_name).
    Uses Nominatim API with User-Agent header and falls back to CITY_COORDINATES cache.
    Also handles direct lat,lon coordinate strings (e.g. "17.3850,78.4867").
    """
    clean_name = location_name.replace("📍", "").strip()
    
    # Check if location_name is in coordinate format e.g. "17.3850, 78.4867" or "Current Location (17.3850, 78.4867)"
    raw_coords = clean_name
    if "(" in raw_coords and ")" in raw_coords:
        raw_coords = raw_coords.split("(")[1].split(")")[0]
        
    if "," in raw_coords:
        parts = raw_coords.split(",")
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    disp = clean_name.split("(")[0].strip() if "(" in clean_name else "Current Location"
                    if not disp:
                        disp = "Current Location"
                    return lat, lon, disp
            except ValueError:
                pass

    clean_lower = clean_name.lower()
    if clean_lower in CITY_COORDINATES:
        lat, lon = CITY_COORDINATES[clean_lower]
        return lat, lon, location_name.title()
    
    # Nominatim Geocoding API
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(location_name)}&format=json&limit=1"
        headers = {"User-Agent": "VoyageML-JourneyPredictor/1.0"}
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                disp_name = data[0]["display_name"].split(",")[0]
                return lat, lon, disp_name
    except Exception as e:
        print(f"Geocoding notice for '{location_name}': {e}")

    # If Nominatim cannot find the entered place, raise clear error message
    raise ValueError(f"Place not found: '{clean_name}'. Try entering a more specific name or address.")


def get_traffic_multiplier(traffic_condition: Optional[str]) -> float:
    """
    Returns traffic adjustment multiplier for route travel time estimate.
    Low Traffic: 1.00
    Moderate Traffic: 1.15
    High Traffic: 1.35
    Severe Traffic: 1.50
    """
    if not traffic_condition:
        return 1.00
    clean = str(traffic_condition).lower().strip()
    if clean in ["low", "light"]:
        return 1.00
    elif clean in ["moderate", "medium", "normal"]:
        return 1.15
    elif clean in ["high", "heavy"]:
        return 1.35
    elif clean in ["severe", "jammed"]:
        return 1.50
    return 1.00

def estimate_mode_time(distance_km: float, travel_mode: str, osrm_driving_duration_seconds: float, traffic_condition: Optional[str] = "Moderate") -> tuple:
    """
    Calculates mode-specific estimated travel duration (seconds) and service label
    based on actual route distance (distance_km) and traffic condition adjustment.
    """
    clean_mode = str(travel_mode).upper().strip() if travel_mode else "DRIVE"
    traffic_mult = get_traffic_multiplier(traffic_condition)
    
    if clean_mode in ["CAR", "DRIVE", "DRIVING"]:
        base_sec = osrm_driving_duration_seconds
        label = "OSRM Driving Engine"
    elif clean_mode in ["BIKE", "TWO_WHEELER", "MOTORCYCLE", "TWO-WHEELER"]:
        # two_wheeler_speed = 50 km/h
        time_minutes = (distance_km / 50.0) * 60.0
        base_sec = time_minutes * 60.0
        label = "Two-Wheeler Estimator (50 km/h)"
    elif clean_mode in ["WALK", "WALKING", "PEDESTRIAN"]:
        # walking_speed = 5 km/h
        time_minutes = (distance_km / 5.0) * 60.0
        return time_minutes * 60.0, "Walking Estimator (5 km/h)"
    elif clean_mode in ["TRANSIT", "PUBLIC_TRANSPORT", "BUS"]:
        # transit_average_speed = 40 km/h + 20 mins wait/transfer allowance
        time_minutes = ((distance_km / 40.0) * 60.0) + 20.0
        base_sec = time_minutes * 60.0
        label = "Estimated Transit Time"
    else:
        base_sec = osrm_driving_duration_seconds
        label = "OSRM Driving Engine"

    adjusted_seconds = base_sec * traffic_mult
    return adjusted_seconds, label

def get_compass_direction_from_bearing(bearing: Optional[float]) -> str:
    """Calculates compass cardinal/intercardinal direction name from a bearing degree (0-360)."""
    if bearing is None:
        return ""
    try:
        b = float(bearing) % 360.0
    except (ValueError, TypeError):
        return ""
    directions = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
    idx = int(round(b / 45.0)) % 8
    return directions[idx]

def calculate_compass_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates initial compass bearing from (lat1, lon1) to (lat2, lon2) in degrees (0-360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return round((bearing + 360.0) % 360.0, 1)

def format_distance_text(meters: float) -> str:
    """Formats distance in meters into human-readable string (e.g. '200 m' or '1.2 km')."""
    if meters <= 0:
        return "0 m"
    if meters < 1000:
        return f"{int(round(meters))} m"
    km = meters / 1000.0
    return f"{km:.1f} km"

def get_clean_road_name(step: dict) -> str:
    """Extracts and sanitizes road name and reference number (e.g. 'Main Road', 'NH 65')."""
    name = (step.get("name") or "").strip()
    raw_ref = (step.get("ref") or "").strip()

    clean_ref = ""
    if raw_ref:
        refs = [r.strip() for r in raw_ref.replace(";", ",").split(",") if r.strip()]
        clean_ref = ", ".join(refs)

    if name and clean_ref:
        if clean_ref.lower() in name.lower():
            return name
        return f"{name} ({clean_ref})"
    return name or clean_ref or ""

def format_osrm_step_instruction(step: dict, destination_name: str = "") -> str:
    """
    Converts raw OSRM maneuver information into clear, human-readable turn-by-turn directions.
    Supports maneuvers: depart, turn (left, right, sharp, slight), straight, u-turn, roundabout,
    fork, ramp, exit, arrive, etc. Never invents turns when unsupported.
    """
    maneuver = step.get("maneuver", {})
    m_type = str(maneuver.get("type", "")).lower().strip()
    m_modifier = str(maneuver.get("modifier", "")).lower().strip().replace("_", " ")
    bearing_after = maneuver.get("bearing_after")
    road_name = get_clean_road_name(step)

    compass = get_compass_direction_from_bearing(bearing_after)
    on_road = f" onto {road_name}" if road_name else ""

    if m_type == "depart":
        if compass and road_name:
            return f"Head {compass} on {road_name}"
        elif compass:
            return f"Head {compass}"
        elif road_name:
            return f"Head out on {road_name}"
        return "Head toward destination"

    elif m_type == "arrive":
        if road_name:
            return f"You have arrived at your destination: {road_name}"
        elif destination_name:
            return f"You have arrived at {destination_name}"
        return "You have arrived at your destination"

    elif m_type == "turn":
        if m_modifier == "uturn":
            return f"Make a U-turn{on_road}" if road_name else "Make a U-turn"
        if m_modifier in ["sharp left", "sharp right"]:
            return f"Make a {m_modifier}{on_road}" if road_name else f"Make a {m_modifier} at the next junction"
        if m_modifier in ["slight left", "slight right", "left", "right"]:
            return f"Turn {m_modifier}{on_road}" if road_name else f"Turn {m_modifier} at the next junction"
        if m_modifier == "straight":
            return f"Continue straight{on_road}" if road_name else "Continue straight"
        return f"Turn{on_road}" if road_name else "Turn at the next junction"

    elif m_type in ["continue", "new name", "straight", "notification"]:
        if m_modifier == "uturn":
            return f"Make a U-turn{on_road}" if road_name else "Make a U-turn"
        if m_modifier and m_modifier not in ["straight"]:
            return f"Keep {m_modifier}{on_road}" if road_name else f"Keep {m_modifier}"
        return f"Continue straight{on_road}" if road_name else "Continue straight"

    elif m_type in ["roundabout", "rotary", "roundabout turn", "exit roundabout"]:
        exit_num = maneuver.get("exit")
        if exit_num:
            return f"Take exit {exit_num} at the roundabout{on_road}" if road_name else f"Take exit {exit_num} at the roundabout"
        return f"Take the roundabout exit{on_road}" if road_name else "Take the roundabout exit"

    elif m_type == "fork":
        if "left" in m_modifier:
            return f"Take the left fork{on_road}" if road_name else "Take the left fork"
        elif "right" in m_modifier:
            return f"Take the right fork{on_road}" if road_name else "Take the right fork"
        return f"Keep {m_modifier} at the fork{on_road}" if m_modifier else f"Take the fork{on_road}"

    elif m_type == "end of road":
        if m_modifier:
            return f"At the end of the road, turn {m_modifier}{on_road}" if road_name else f"Turn {m_modifier} at the end of the road"
        return f"Turn at the end of the road{on_road}"

    elif m_type in ["off ramp", "ramp", "exit"]:
        if road_name:
            return f"Take the exit toward {road_name}"
        return "Take the exit toward the destination"

    elif m_type == "on ramp":
        if road_name:
            return f"Take the ramp onto {road_name}"
        return "Take the ramp"

    elif m_type == "merge":
        if "left" in m_modifier:
            return f"Merge left{on_road}"
        elif "right" in m_modifier:
            return f"Merge right{on_road}"
        return f"Merge{on_road}"

    elif m_type == "use lane":
        if m_modifier:
            return f"Use the {m_modifier} lane{on_road}"
        return f"Keep straight{on_road}"

    else:
        if m_modifier == "uturn":
            return f"Make a U-turn{on_road}" if road_name else "Make a U-turn"
        elif m_modifier in ["left", "right", "slight left", "slight right", "sharp left", "sharp right"]:
            return f"Turn {m_modifier}{on_road}" if road_name else f"Turn {m_modifier} at the next junction"
        elif road_name:
            return f"Continue onto {road_name}"
        return "Continue straight"

def parse_osrm_steps(legs: list, destination_name: str = "") -> list:
    """Parses OSRM legs into standardized, detailed turn-by-turn navigation steps."""
    parsed_steps = []
    if not legs:
        return parsed_steps

    raw_steps = legs[0].get("steps", [])
    for idx, s in enumerate(raw_steps):
        instruction = format_osrm_step_instruction(s, destination_name=destination_name)
        maneuver = s.get("maneuver", {})
        m_loc = maneuver.get("location", [0, 0])
        lat_lon_loc = [m_loc[1], m_loc[0]] if isinstance(m_loc, list) and len(m_loc) == 2 else [0, 0]

        step_geom = s.get("geometry", {})
        step_coords = []
        if isinstance(step_geom, dict) and "coordinates" in step_geom:
            step_coords = [[pt[1], pt[0]] for pt in step_geom["coordinates"]]

        dist_m = float(s.get("distance", 0.0))
        dist_txt = format_distance_text(dist_m)
        bearing = maneuver.get("bearing_after")
        compass = get_compass_direction_from_bearing(bearing)
        road_name = get_clean_road_name(s)

        if maneuver.get("type") == "arrive":
            full_instruction = instruction
        elif dist_m > 0:
            full_instruction = f"{instruction} for {dist_txt}"
        else:
            full_instruction = instruction

        parsed_steps.append({
            "step_index": idx,
            "instruction": instruction,
            "full_instruction": full_instruction,
            "road_name": road_name,
            "maneuver_type": maneuver.get("type", ""),
            "maneuver_modifier": maneuver.get("modifier", ""),
            "bearing_after": bearing,
            "bearing_before": maneuver.get("bearing_before"),
            "compass_direction": compass,
            "distance_meters": dist_m,
            "distance_km": round(dist_m / 1000.0, 3),
            "distance_text": dist_txt,
            "duration_seconds": float(s.get("duration", 0.0)),
            "location": lat_lon_loc,
            "step_geometry": step_coords
        })
    return parsed_steps

def decode_polyline6(encoded: str) -> List[List[float]]:
    """Decodes polyline6 encoded string (precision 1e6) into [[lat, lon], ...] coordinate pairs."""
    coords = []
    index = 0
    lat = 0
    lng = 0
    factor = 1000000.0
    while index < len(encoded):
        b = 0
        shift = 0
        result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1f) << shift
            shift += 5
            if byte < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        shift = 0
        result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1f) << shift
            shift += 5
            if byte < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        coords.append([round(lat / factor, 6), round(lng / factor, 6)])
    return coords

VALHALLA_TYPE_MAP = {
    0: ("none", ""),
    1: ("depart", "straight"),
    2: ("depart", "right"),
    3: ("depart", "left"),
    4: ("arrive", ""),
    5: ("arrive", "right"),
    6: ("arrive", "left"),
    7: ("continue", "straight"),
    8: ("continue", "straight"),
    9: ("turn", "slight right"),
    10: ("turn", "right"),
    11: ("turn", "sharp right"),
    12: ("turn", "uturn"),
    13: ("turn", "uturn"),
    14: ("turn", "sharp left"),
    15: ("turn", "left"),
    16: ("turn", "slight left"),
    17: ("ramp", "straight"),
    18: ("ramp", "right"),
    19: ("ramp", "left"),
    20: ("exit", "right"),
    21: ("exit", "left"),
    22: ("continue", "straight"),
    23: ("fork", "right"),
    24: ("fork", "left"),
    25: ("merge", "straight"),
    26: ("roundabout", "enter"),
    27: ("roundabout", "exit"),
}

def query_valhalla_routing(lat1: float, lon1: float, lat2: float, lon2: float, dest_name: str) -> Optional[Tuple[List[List[float]], List[Dict[str, Any]], float, float]]:
    """
    Queries OpenStreetMap Valhalla Routing Server (FOSSGIS e.V.).
    Returns (coordinates, parsed_steps, distance_meters, duration_seconds) or None on failure.
    """
    try:
        req_data = {
            "locations": [{"lat": lat1, "lon": lon1}, {"lat": lat2, "lon": lon2}],
            "costing": "auto",
            "directions_options": {"units": "kilometers"}
        }
        url = "https://valhalla1.openstreetmap.de/route?json=" + urllib.parse.quote(json.dumps(req_data))
        req = urllib.request.Request(url, headers={"User-Agent": "WayVista-VoyageML/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.getcode() == 200:
                data = json.loads(resp.read().decode("utf-8"))
                trip = data.get("trip", {})
                summary = trip.get("summary", {})
                legs = trip.get("legs", [])
                if not legs:
                    return None
                leg = legs[0]
                shape_str = leg.get("shape", "")
                if not shape_str:
                    return None

                pts = decode_polyline6(shape_str)
                if not pts:
                    return None

                dist_m = float(summary.get("length", 0.0)) * 1000.0
                dur_s = float(summary.get("time", 0.0))

                parsed_steps = []
                raw_maneuvers = leg.get("maneuvers", [])
                for idx, m in enumerate(raw_maneuvers):
                    t_code = m.get("type", 0)
                    m_type, m_mod = VALHALLA_TYPE_MAP.get(t_code, ("turn", ""))
                    instr = (m.get("instruction") or "").strip()
                    street_names = m.get("street_names") or []
                    road_name = street_names[0] if street_names else ""
                    b_after = m.get("bearing_after")
                    b_before = m.get("bearing_before")
                    compass = get_compass_direction_from_bearing(b_after)
                    dist_step_m = float(m.get("length", 0.0)) * 1000.0
                    dur_step_s = float(m.get("time", 0.0))
                    b_idx = m.get("begin_shape_index", 0)
                    e_idx = m.get("end_shape_index", b_idx)
                    loc = pts[b_idx] if b_idx < len(pts) else pts[-1]
                    step_geom = pts[b_idx : e_idx + 1] if b_idx < len(pts) else [loc]
                    dist_txt = format_distance_text(dist_step_m)

                    if m_type == "arrive" or idx == len(raw_maneuvers) - 1:
                        final_instr = f"You have arrived at your destination: {dest_name}" if dest_name else "You have arrived at your destination"
                        full_instr = final_instr
                    elif dist_step_m > 0:
                        final_instr = instr
                        full_instr = f"{instr} ({dist_txt})"
                    else:
                        final_instr = instr
                        full_instr = instr

                    parsed_steps.append({
                        "step_index": idx,
                        "instruction": final_instr,
                        "full_instruction": full_instr,
                        "road_name": road_name,
                        "maneuver_type": m_type,
                        "maneuver_modifier": m_mod,
                        "bearing_after": b_after,
                        "bearing_before": b_before,
                        "compass_direction": compass,
                        "distance_meters": dist_step_m,
                        "distance_km": round(dist_step_m / 1000.0, 3),
                        "distance_text": dist_txt,
                        "duration_seconds": dur_step_s,
                        "location": loc,
                        "step_geometry": step_geom
                    })
                return pts, parsed_steps, dist_m, dur_s
    except Exception as e:
        print(f"Valhalla routing notice: {e}")
    return None

def query_brouter_routing(lat1: float, lon1: float, lat2: float, lon2: float, dest_name: str) -> Optional[Tuple[List[List[float]], List[Dict[str, Any]], float, float]]:
    """
    Queries BRouter OpenStreetMap Routing Engine as secondary backup.
    Returns (coordinates, parsed_steps, distance_meters, duration_seconds) or None on failure.
    """
    try:
        url = f"https://brouter.de/brouter?lonlats={lon1},{lat1}|{lon2},{lat2}&profile=car-eco&alternativeidx=0&format=geojson&timode=3"
        req = urllib.request.Request(url, headers={"User-Agent": "WayVista-VoyageML/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.getcode() == 200:
                data = json.loads(resp.read().decode("utf-8"))
                features = data.get("features", [])
                if not features:
                    return None
                feat = features[0]
                props = feat.get("properties", {})
                dist_m = float(props.get("track-length", 0.0))
                dur_s = float(props.get("total-time", 0.0))
                raw_coords = feat.get("geometry", {}).get("coordinates", [])
                pts = [[pt[1], pt[0]] for pt in raw_coords]
                if not pts:
                    return None

                voicehints = props.get("voicehints", [])
                parsed_steps = []
                
                # Depart step
                first_bearing = calculate_compass_bearing(lat1, lon1, pts[min(5, len(pts)-1)][0], pts[min(5, len(pts)-1)][1])
                first_compass = get_compass_direction_from_bearing(first_bearing)
                parsed_steps.append({
                    "step_index": 0,
                    "instruction": f"Head {first_compass} on your route" if first_compass else "Head out on your route",
                    "full_instruction": f"Head {first_compass} on your route" if first_compass else "Head out on your route",
                    "road_name": "",
                    "maneuver_type": "depart",
                    "maneuver_modifier": "straight",
                    "bearing_after": first_bearing,
                    "bearing_before": None,
                    "compass_direction": first_compass,
                    "distance_meters": float(voicehints[0][3]) if voicehints else dist_m,
                    "distance_km": round((float(voicehints[0][3]) if voicehints else dist_m) / 1000.0, 3),
                    "distance_text": format_distance_text(float(voicehints[0][3]) if voicehints else dist_m),
                    "duration_seconds": dur_s / (len(voicehints) + 1) if voicehints else dur_s,
                    "location": pts[0],
                    "step_geometry": pts[:max(1, voicehints[0][0])] if voicehints else pts
                })

                BROUTER_CMD_MAP = {
                    1: ("continue straight", "continue", "straight"),
                    2: ("turn left", "turn", "left"),
                    3: ("turn slightly left", "turn", "slight left"),
                    4: ("turn sharply left", "turn", "sharp left"),
                    5: ("turn right", "turn", "right"),
                    6: ("turn slightly right", "turn", "slight right"),
                    7: ("turn sharply right", "turn", "sharp right"),
                    8: ("keep left", "fork", "left"),
                    9: ("keep right", "fork", "right"),
                    10: ("make a U-turn", "turn", "uturn"),
                    11: ("enter roundabout", "roundabout", "enter"),
                }

                for v_idx, vh in enumerate(voicehints):
                    node_idx = vh[0] if len(vh) > 0 else 0
                    cmd_code = vh[1] if len(vh) > 1 else 1
                    dist_step_m = float(vh[3]) if len(vh) > 3 else 0.0
                    action_txt, m_type, m_mod = BROUTER_CMD_MAP.get(cmd_code, ("turn", "turn", ""))
                    loc = pts[node_idx] if node_idx < len(pts) else pts[-1]
                    dist_txt = format_distance_text(dist_step_m)
                    instr = f"{action_txt.capitalize()} at the junction"

                    parsed_steps.append({
                        "step_index": v_idx + 1,
                        "instruction": instr,
                        "full_instruction": f"{instr} ({dist_txt})" if dist_step_m > 0 else instr,
                        "road_name": "",
                        "maneuver_type": m_type,
                        "maneuver_modifier": m_mod,
                        "bearing_after": None,
                        "bearing_before": None,
                        "compass_direction": "",
                        "distance_meters": dist_step_m,
                        "distance_km": round(dist_step_m / 1000.0, 3),
                        "distance_text": dist_txt,
                        "duration_seconds": dur_s / len(voicehints),
                        "location": loc,
                        "step_geometry": pts[node_idx : min(len(pts), node_idx + 20)]
                    })

                # Arrive step
                parsed_steps.append({
                    "step_index": len(parsed_steps),
                    "instruction": f"You have arrived at your destination: {dest_name}" if dest_name else "You have arrived at your destination",
                    "full_instruction": f"You have arrived at your destination: {dest_name}" if dest_name else "You have arrived at your destination",
                    "road_name": dest_name,
                    "maneuver_type": "arrive",
                    "maneuver_modifier": "",
                    "bearing_after": None,
                    "bearing_before": None,
                    "compass_direction": "",
                    "distance_meters": 0.0,
                    "distance_km": 0.0,
                    "distance_text": "0 m",
                    "duration_seconds": 0.0,
                    "location": pts[-1],
                    "step_geometry": [pts[-1]]
                })

                return pts, parsed_steps, dist_m, dur_s
    except Exception as e:
        print(f"BRouter routing notice: {e}")
    return None

def get_route_details(source: str, destination: str, travel_mode: str = "DRIVE", traffic_condition: Optional[str] = "Moderate"):
    """
    Obtains route details: coordinates, distance (km), duration (minutes), route geometry path, and turn-by-turn steps.
    Uses multi-tier OpenStreetMap routing:
      1. OSRM Routing Engine (router.project-osrm.org)
      2. Valhalla OpenStreetMap Routing Server (valhalla1.openstreetmap.de)
      3. BRouter OpenStreetMap Engine (brouter.de)
      4. Safe Haversine Distance & Bearing Estimator (Offline fallback)
    Applies mode-specific & traffic-adjusted duration logic.
    """
    if not source or not destination:
        raise ValueError("Source and destination location names cannot be empty.")

    clean_mode = str(travel_mode).upper().strip() if travel_mode else "DRIVE"
    source_lat, source_lon, source_clean = geocode_location(source)
    dest_lat, dest_lon, dest_clean = geocode_location(destination)

    # 1. Tier 1: Query public OSRM Routing Engine
    try:
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{source_lon},{source_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson&steps=true"
        res = requests.get(osrm_url, timeout=(1.5, 2.5))
        if res.status_code == 200:
            data = res.json()
            routes = data.get("routes", [])
            if routes and "geometry" in routes[0] and "coordinates" in routes[0]["geometry"]:
                distance_meters = float(routes[0]["distance"])
                osrm_duration_seconds = float(routes[0]["duration"])
                dist_km = round(distance_meters / 1000.0, 2)

                mode_duration_sec, service_label = estimate_mode_time(dist_km, clean_mode, osrm_duration_seconds, traffic_condition)
                duration_mins = round(mode_duration_sec / 60.0, 1)

                coords = routes[0]["geometry"]["coordinates"]
                leaflet_coords = [[pt[1], pt[0]] for pt in coords]
                steps = parse_osrm_steps(routes[0].get("legs", []), destination_name=dest_clean)

                if len(leaflet_coords) >= 2 and len(steps) > 0:
                    return {
                        "success": True,
                        "source": source_clean,
                        "destination": dest_clean,
                        "distance_km": dist_km,
                        "distance_meters": distance_meters,
                        "duration_seconds": mode_duration_sec,
                        "route_duration_minutes": duration_mins,
                        "source_coordinates": [source_lat, source_lon],
                        "destination_coordinates": [dest_lat, dest_lon],
                        "route_geometry": leaflet_coords,
                        "steps": steps,
                        "service_used": service_label
                    }
    except Exception as err:
        print(f"OSRM Routing notice (trying next provider): {err}")

    # 2. Tier 2: Query OpenStreetMap Valhalla Routing Engine (FOSSGIS e.V.)
    valhalla_res = query_valhalla_routing(source_lat, source_lon, dest_lat, dest_lon, dest_clean)
    if valhalla_res:
        leaflet_coords, steps, distance_meters, valhalla_dur_s = valhalla_res
        dist_km = round(distance_meters / 1000.0, 2)
        
        # Estimate realistic duration based on distance & mode
        base_dur_s = (dist_km / 65.0) * 3600.0 if dist_km > 30 else valhalla_dur_s
        mode_duration_sec, service_label = estimate_mode_time(dist_km, clean_mode, base_dur_s, traffic_condition)
        duration_mins = round(mode_duration_sec / 60.0, 1)

        return {
            "success": True,
            "source": source_clean,
            "destination": dest_clean,
            "distance_km": dist_km,
            "distance_meters": distance_meters,
            "duration_seconds": mode_duration_sec,
            "route_duration_minutes": duration_mins,
            "source_coordinates": [source_lat, source_lon],
            "destination_coordinates": [dest_lat, dest_lon],
            "route_geometry": leaflet_coords,
            "steps": steps,
            "service_used": f"{service_label} (OpenStreetMap)"
        }

    # 3. Tier 3: Query BRouter OpenStreetMap Engine
    brouter_res = query_brouter_routing(source_lat, source_lon, dest_lat, dest_lon, dest_clean)
    if brouter_res:
        leaflet_coords, steps, distance_meters, brouter_dur_s = brouter_res
        dist_km = round(distance_meters / 1000.0, 2)
        mode_duration_sec, service_label = estimate_mode_time(dist_km, clean_mode, brouter_dur_s, traffic_condition)
        duration_mins = round(mode_duration_sec / 60.0, 1)

        return {
            "success": True,
            "source": source_clean,
            "destination": dest_clean,
            "distance_km": dist_km,
            "distance_meters": distance_meters,
            "duration_seconds": mode_duration_sec,
            "route_duration_minutes": duration_mins,
            "source_coordinates": [source_lat, source_lon],
            "destination_coordinates": [dest_lat, dest_lon],
            "route_geometry": leaflet_coords,
            "steps": steps,
            "service_used": f"{service_label} (OpenStreetMap BRouter)"
        }

    # 4. Tier 4: Fallback Haversine Calculation (Offline safe)
    dist_km = calculate_haversine_distance(source_lat, source_lon, dest_lat, dest_lon)
    fallback_osrm_sec = (dist_km / 50.0) * 3600.0
    mode_duration_sec, service_label = estimate_mode_time(dist_km, clean_mode, fallback_osrm_sec, traffic_condition)
    est_duration_mins = round(mode_duration_sec / 60.0, 1)

    # Generate multi-point interpolated waypoints (at least 15 points)
    steps_count = 16
    waypoints = []
    for i in range(steps_count + 1):
        frac = i / steps_count
        interp_lat = source_lat + frac * (dest_lat - source_lat)
        interp_lon = source_lon + frac * (dest_lon - source_lon)
        waypoints.append([round(interp_lat, 6), round(interp_lon, 6)])

    fallback_bearing = calculate_compass_bearing(source_lat, source_lon, dest_lat, dest_lon)
    fallback_compass = get_compass_direction_from_bearing(fallback_bearing)

    depart_text = f"Head {fallback_compass} from {source_clean}" if fallback_compass else f"Head toward {dest_clean}"
    continue_text = f"Continue straight toward {dest_clean}"
    dist_text = f"{dist_km} km"

    fallback_steps = [
        {
            "step_index": 0,
            "instruction": depart_text,
            "full_instruction": depart_text,
            "road_name": "",
            "maneuver_type": "depart",
            "maneuver_modifier": "straight",
            "bearing_after": fallback_bearing,
            "bearing_before": None,
            "compass_direction": fallback_compass,
            "distance_meters": 0.0,
            "distance_km": 0.0,
            "distance_text": "0 m",
            "duration_seconds": 0.0,
            "location": [source_lat, source_lon],
            "step_geometry": waypoints[:3]
        },
        {
            "step_index": 1,
            "instruction": continue_text,
            "full_instruction": f"{continue_text} for {dist_text}",
            "road_name": "",
            "maneuver_type": "continue",
            "maneuver_modifier": "straight",
            "bearing_after": fallback_bearing,
            "bearing_before": fallback_bearing,
            "compass_direction": fallback_compass,
            "distance_meters": dist_km * 1000.0,
            "distance_km": dist_km,
            "distance_text": dist_text,
            "duration_seconds": mode_duration_sec,
            "location": waypoints[len(waypoints)//2],
            "step_geometry": waypoints
        },
        {
            "step_index": 2,
            "instruction": "You have arrived at your destination",
            "full_instruction": f"You have arrived at your destination: {dest_clean}",
            "road_name": dest_clean,
            "maneuver_type": "arrive",
            "maneuver_modifier": "",
            "bearing_after": None,
            "bearing_before": fallback_bearing,
            "compass_direction": "",
            "distance_meters": 0.0,
            "distance_km": 0.0,
            "distance_text": "0 m",
            "duration_seconds": 0.0,
            "location": [dest_lat, dest_lon],
            "step_geometry": waypoints[-3:]
        }
    ]

    return {
        "success": True,
        "source": source_clean,
        "destination": dest_clean,
        "distance_km": dist_km,
        "distance_meters": dist_km * 1000.0,
        "duration_seconds": mode_duration_sec,
        "route_duration_minutes": est_duration_mins,
        "source_coordinates": [source_lat, source_lon],
        "destination_coordinates": [dest_lat, dest_lon],
        "route_geometry": waypoints,
        "steps": fallback_steps,
        "service_used": f"{service_label} (Haversine)"
    }


