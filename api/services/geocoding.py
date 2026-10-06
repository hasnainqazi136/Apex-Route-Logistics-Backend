import requests
import re
import math

# Built-in high-accuracy geocoding cache for major freight hubs and US cities
POPULAR_US_CITIES = {
    "chicago, il": {"name": "Chicago, IL", "lat": 41.8781, "lng": -87.6298, "state": "IL"},
    "indianapolis, in": {"name": "Indianapolis, IN", "lat": 39.7684, "lng": -86.1581, "state": "IN"},
    "dallas, tx": {"name": "Dallas, TX", "lat": 32.7767, "lng": -96.7970, "state": "TX"},
    "houston, tx": {"name": "Houston, TX", "lat": 29.7604, "lng": -95.3698, "state": "TX"},
    "atlanta, ga": {"name": "Atlanta, GA", "lat": 33.7490, "lng": -84.3880, "state": "GA"},
    "los angeles, ca": {"name": "Los Angeles, CA", "lat": 34.0522, "lng": -118.2437, "state": "CA"},
    "new york, ny": {"name": "New York, NY", "lat": 40.7128, "lng": -74.0060, "state": "NY"},
    "philadelphia, pa": {"name": "Philadelphia, PA", "lat": 39.9526, "lng": -75.1652, "state": "PA"},
    "phoenix, az": {"name": "Phoenix, AZ", "lat": 33.4484, "lng": -112.0740, "state": "AZ"},
    "seattle, wa": {"name": "Seattle, WA", "lat": 47.6062, "lng": -122.3321, "state": "WA"},
    "denver, co": {"name": "Denver, CO", "lat": 39.7392, "lng": -104.9903, "state": "CO"},
    "kansas city, mo": {"name": "Kansas City, MO", "lat": 39.0997, "lng": -94.5786, "state": "MO"},
    "memphis, tn": {"name": "Memphis, TN", "lat": 35.1495, "lng": -90.0490, "state": "TN"},
    "nashville, tn": {"name": "Nashville, TN", "lat": 36.1627, "lng": -86.7816, "state": "TN"},
    "st. louis, mo": {"name": "St. Louis, MO", "lat": 38.6270, "lng": -90.1994, "state": "MO"},
    "columbus, oh": {"name": "Columbus, OH", "lat": 39.9612, "lng": -82.9988, "state": "OH"},
    "cincinnati, oh": {"name": "Cincinnati, OH", "lat": 39.1031, "lng": -84.5120, "state": "OH"},
    "cleveland, oh": {"name": "Cleveland, OH", "lat": 41.4993, "lng": -81.6944, "state": "OH"},
    "detroit, mi": {"name": "Detroit, MI", "lat": 42.3314, "lng": -83.0458, "state": "MI"},
    "milwaukee, wi": {"name": "Milwaukee, WI", "lat": 43.0389, "lng": -87.9065, "state": "WI"},
    "minneapolis, mn": {"name": "Minneapolis, MN", "lat": 44.9778, "lng": -93.2650, "state": "MN"},
    "omaha, ne": {"name": "Omaha, NE", "lat": 41.2565, "lng": -95.9345, "state": "NE"},
    "des moines, ia": {"name": "Des Moines, IA", "lat": 41.5868, "lng": -93.6250, "state": "IA"},
    "oklahoma city, ok": {"name": "Oklahoma City, OK", "lat": 35.4676, "lng": -97.5164, "state": "OK"},
    "albuquerque, nm": {"name": "Albuquerque, NM", "lat": 35.0844, "lng": -106.6504, "state": "NM"},
    "salt lake city, ut": {"name": "Salt Lake City, UT", "lat": 40.7608, "lng": -111.8910, "state": "UT"},
    "las vegas, nv": {"name": "Las Vegas, NV", "lat": 36.1699, "lng": -115.1398, "state": "NV"},
    "san diego, ca": {"name": "San Diego, CA", "lat": 32.7157, "lng": -117.1611, "state": "CA"},
    "san francisco, ca": {"name": "San Francisco, CA", "lat": 37.7749, "lng": -122.4194, "state": "CA"},
    "portland, or": {"name": "Portland, OR", "lat": 45.5152, "lng": -122.6784, "state": "OR"},
    "miami, fl": {"name": "Miami, FL", "lat": 25.7617, "lng": -80.1918, "state": "FL"},
    "tampa, fl": {"name": "Tampa, FL", "lat": 27.9506, "lng": -82.4572, "state": "FL"},
    "orlando, fl": {"name": "Orlando, FL", "lat": 28.5383, "lng": -81.3792, "state": "FL"},
    "jacksonville, fl": {"name": "Jacksonville, FL", "lat": 30.3322, "lng": -81.6557, "state": "FL"},
    "charlotte, nc": {"name": "Charlotte, NC", "lat": 35.2271, "lng": -80.8431, "state": "NC"},
    "raleigh, nc": {"name": "Raleigh, NC", "lat": 35.7796, "lng": -78.6382, "state": "NC"},
    "richmond, va": {"name": "Richmond, VA", "lat": 37.5407, "lng": -77.4360, "state": "VA"},
    "washington, dc": {"name": "Washington, DC", "lat": 38.9072, "lng": -77.0369, "state": "DC"},
    "baltimore, md": {"name": "Baltimore, MD", "lat": 39.2904, "lng": -76.6122, "state": "MD"},
    "boston, ma": {"name": "Boston, MA", "lat": 42.3601, "lng": -71.0589, "state": "MA"},
    "pittsburgh, pa": {"name": "Pittsburgh, PA", "lat": 40.4406, "lng": -79.9959, "state": "PA"},
    "louisville, ky": {"name": "Louisville, KY", "lat": 38.2527, "lng": -85.7585, "state": "KY"},
    "new orleans, la": {"name": "New Orleans, LA", "lat": 29.9511, "lng": -90.0715, "state": "LA"},
    "birmingham, al": {"name": "Birmingham, AL", "lat": 33.5186, "lng": -86.8104, "state": "AL"},
    "little rock, ar": {"name": "Little Rock, AR", "lat": 34.7465, "lng": -92.2896, "state": "AR"},
    "tulsa, ok": {"name": "Tulsa, OK", "lat": 36.1540, "lng": -95.9928, "state": "OK"},
    "el paso, tx": {"name": "El Paso, TX", "lat": 31.7619, "lng": -106.4850, "state": "TX"},
    "san antonio, tx": {"name": "San Antonio, TX", "lat": 29.4241, "lng": -98.4936, "state": "TX"},
    "austin, tx": {"name": "Austin, TX", "lat": 30.2672, "lng": -97.7431, "state": "TX"},
    "boise, id": {"name": "Boise, ID", "lat": 43.6150, "lng": -116.2023, "state": "ID"},
    "billings, mt": {"name": "Billings, MT", "lat": 45.7833, "lng": -108.5007, "state": "MT"},
    "fargo, nd": {"name": "Fargo, ND", "lat": 46.8772, "lng": -96.7898, "state": "ND"},
    "sioux falls, sd": {"name": "Sioux Falls, SD", "lat": 43.5460, "lng": -96.7313, "state": "SD"},
    "cheyenne, wy": {"name": "Cheyenne, WY", "lat": 41.1400, "lng": -104.8202, "state": "WY"},
}

def normalize_key(s: str) -> str:
    cleaned = re.sub(r"[^\w\s,]", "", s.strip().lower())
    return " ".join(cleaned.split())

def geocode_location(query: str) -> dict:
    """
    Geocodes a query string into a dict: {'name': str, 'lat': float, 'lng': float}
    Checks coordinates pattern -> popular database -> Nominatim API -> fallback.
    """
    if not query:
        raise ValueError("Location query cannot be empty")

    query_str = str(query).strip()

    # Check if input is "lat, lng"
    coord_match = re.match(r"^([-+]?\d{1,2}\.?\d*)[,\s]+([-+]?\d{1,3}\.?\d*)$", query_str)
    if coord_match:
        lat = float(coord_match.group(1))
        lng = float(coord_match.group(2))
        return {"name": f"{lat:.4f}, {lng:.4f}", "lat": lat, "lng": lng}

    norm = normalize_key(query_str)
    
    # Direct dictionary match
    if norm in POPULAR_US_CITIES:
        return POPULAR_US_CITIES[norm].copy()

    # Partial / city name only match
    for key, data in POPULAR_US_CITIES.items():
        city_name = key.split(",")[0].strip()
        if norm == city_name or norm.startswith(city_name + " ") or norm.endswith(" " + city_name):
            return data.copy()

    # Try OpenStreetMap Nominatim
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {
            "User-Agent": "ELDRoutePlanner/1.0 (assessment-eld-app@trucking.dev)"
        }
        params = {
            "q": query_str,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        resp = requests.get(url, params=params, headers=headers, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                first = data[0]
                disp_name = first.get("display_name", query_str)
                # Shorten name if too long
                parts = [p.strip() for p in disp_name.split(",")]
                short_name = ", ".join(parts[:2]) if len(parts) >= 2 else disp_name
                return {
                    "name": short_name,
                    "lat": float(first["lat"]),
                    "lng": float(first["lon"])
                }
    except Exception as e:
        print(f"Geocoding online lookup failed for '{query_str}': {e}")

    # Fallback default (Chicago) if completely unknown
    return {"name": query_str, "lat": 41.8781, "lng": -87.6298}


def search_suggestions(query: str, limit: int = 6) -> list:
    """Returns autocomplete suggestions for city search."""
    q = normalize_key(query)
    results = []
    
    # Search local database first
    for key, data in POPULAR_US_CITIES.items():
        if q in key:
            results.append({
                "label": data["name"],
                "value": data["name"],
                "lat": data["lat"],
                "lng": data["lng"]
            })
            if len(results) >= limit:
                return results

    # If few results and query length >= 2, query Nominatim
    if len(results) < 5 and len(query.strip()) >= 2:
        try:
            url = "https://nominatim.openstreetmap.org/search"
            headers = {"User-Agent": "ELDRoutePlanner/1.0 (freight-eld-app@trucking.dev)"}
            params = {
                "q": query.strip() + ", USA",
                "format": "json",
                "limit": limit - len(results),
                "addressdetails": 1
            }
            resp = requests.get(url, params=params, headers=headers, timeout=3)
            if resp.status_code == 200:
                for item in resp.json():
                    addr = item.get("address", {})
                    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county")
                    state = addr.get("state")
                    if city and state:
                        label = f"{city}, {state}"
                    else:
                        parts = [p.strip() for p in item.get("display_name", "").split(",")]
                        label = ", ".join(parts[:2]) if len(parts) >= 2 else item.get("display_name", "")

                    # Avoid duplicate label
                    if not any(r["label"].lower() == label.lower() for r in results):
                        results.append({
                            "label": label,
                            "value": label,
                            "lat": float(item["lat"]),
                            "lng": float(item["lon"])
                        })
        except Exception:
            pass

    return results
