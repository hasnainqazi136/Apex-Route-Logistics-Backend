import requests
import math

TRUCK_AVG_SPEED_MPH = 55.0  # Commercial truck average driving speed on US highways

def haversine_distance_miles(lat1, lon1, lat2, lon2) -> float:
    """Calculates great circle distance between two points in miles."""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def interpolate_line(coord1, coord2, steps=15):
    """Generates interpolated points between two coordinates."""
    points = []
    lat1, lng1 = coord1[1], coord1[0]
    lat2, lng2 = coord2[1], coord2[0]
    for i in range(steps + 1):
        ratio = i / float(steps)
        lat = lat1 + (lat2 - lat1) * ratio
        lng = lng1 + (lng2 - lng1) * ratio
        points.append([lng, lat])
    return points

def get_route(origin_coords: dict, dest_coords: dict) -> dict:
    """
    Fetches route between origin {'lat': float, 'lng': float} and dest.
    Returns:
    {
        'distance_miles': float,
        'duration_hours': float,
        'coordinates': list of [lng, lat],
        'provider': 'osrm' or 'fallback'
    }
    """
    lat1, lng1 = origin_coords['lat'], origin_coords['lng']
    lat2, lng2 = dest_coords['lat'], dest_coords['lng']

    # Try OSRM public routing API
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=geojson"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and len(data.get("routes", [])) > 0:
                route = data["routes"][0]
                meters = route.get("distance", 0)
                distance_miles = round(meters * 0.000621371, 1)
                
                # Commercial truck realistic driving duration (distance / 55 mph)
                # OSRM duration is for cars, trucks are governed and heavier
                duration_hours = round(max(distance_miles / TRUCK_AVG_SPEED_MPH, 0.1), 2)
                
                coords = route.get("geometry", {}).get("coordinates", [])
                if coords and len(coords) >= 2:
                    return {
                        "distance_miles": distance_miles,
                        "duration_hours": duration_hours,
                        "coordinates": coords,
                        "provider": "osrm"
                    }
    except Exception as e:
        print(f"OSRM routing failed: {e}. Using highway network estimation.")

    # High-accuracy fallback: Haversine with 1.18x highway circuity factor
    straight_miles = haversine_distance_miles(lat1, lng1, lat2, lng2)
    highway_miles = round(straight_miles * 1.18, 1)
    duration_hours = round(max(highway_miles / TRUCK_AVG_SPEED_MPH, 0.1), 2)
    coords = interpolate_line([lng1, lat1], [lng2, lat2], steps=30)

    return {
        "distance_miles": highway_miles,
        "duration_hours": duration_hours,
        "coordinates": coords,
        "provider": "fallback"
    }

def sample_coord_at_ratio(coordinates: list, ratio: float) -> list:
    """Returns [lng, lat] along coordinates line at given ratio (0.0 to 1.0)."""
    if not coordinates:
        return [0, 0]
    if ratio <= 0.0:
        return coordinates[0]
    if ratio >= 1.0:
        return coordinates[-1]
    
    idx = int(round(ratio * (len(coordinates) - 1)))
    idx = max(0, min(idx, len(coordinates) - 1))
    return coordinates[idx]
