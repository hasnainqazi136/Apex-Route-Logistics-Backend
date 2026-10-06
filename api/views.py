from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import traceback

from .services.geocoding import geocode_location, search_suggestions
from .services.routing import get_route
from .services.hos_engine import plan_trip_hos
from .services.eld_generator import generate_eld_sheets

@api_view(["GET"])
def api_root(request):
    return Response({
        "status": "online",
        "service": "Apex Route Logistics - ELD API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health/",
            "geocode": "/api/geocode/?q={query}",
            "plan_trip": "/api/plan-trip/"
        }
    })

@api_view(["GET"])
def health_check(request):
    return Response({"status": "healthy", "service": "ELD Route Planner API"})

@api_view(["GET"])
def geocode_search(request):
    q = request.GET.get("q", "").strip()
    if not q or len(q) < 2:
        return Response([])
    results = search_suggestions(q, limit=8)
    return Response(results)

@api_view(["POST"])
def plan_trip(request):
    try:
        data = request.data
        current_loc_str = data.get("current_location", "").strip()
        pickup_loc_str = data.get("pickup_location", "").strip()
        dropoff_loc_str = data.get("dropoff_location", "").strip()
        
        try:
            current_cycle_used = float(data.get("current_cycle_used", 0.0))
        except (ValueError, TypeError):
            current_cycle_used = 0.0

        if not current_loc_str or not pickup_loc_str or not dropoff_loc_str:
            return Response(
                {"error": "Please provide current_location, pickup_location, and dropoff_location."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Geocode locations
        current_coords = geocode_location(current_loc_str)
        pickup_coords = geocode_location(pickup_loc_str)
        dropoff_coords = geocode_location(dropoff_loc_str)

        # 2. Compute route legs
        leg1_route = get_route(current_coords, pickup_coords)
        leg2_route = get_route(pickup_coords, dropoff_coords)

        # Combine route geometry for map
        combined_coords = []
        if leg1_route.get("coordinates"):
            combined_coords.extend(leg1_route["coordinates"])
        if leg2_route.get("coordinates"):
            # Avoid repeating joint coordinate
            if combined_coords and len(leg2_route["coordinates"]) > 0:
                combined_coords.extend(leg2_route["coordinates"][1:])
            else:
                combined_coords.extend(leg2_route["coordinates"])

        # 3. Simulate FMCSA HOS
        hos_result = plan_trip_hos(
            current_loc=current_coords,
            pickup_loc=pickup_coords,
            dropoff_loc=dropoff_coords,
            current_cycle_used=current_cycle_used,
            leg1_route=leg1_route,
            leg2_route=leg2_route
        )

        # 4. Generate standard 24-hour Midnight-to-Midnight ELD sheets
        daily_sheets = generate_eld_sheets(
            events=hos_result["events"],
            initial_cycle_used=current_cycle_used
        )

        # 5. Calculate summary metrics
        total_driving_hours = round(
            sum(ev["duration_hours"] for ev in hos_result["events"] if ev["status"] == "DRIVING"), 2
        )
        total_rest_hours = round(
            sum(ev["duration_hours"] for ev in hos_result["events"] if ev["status"] in ["OFF_DUTY", "SLEEPER_BERTH"]), 2
        )
        total_on_duty_hours = round(
            sum(ev["duration_hours"] for ev in hos_result["events"] if ev["status"] == "ON_DUTY_NOT_DRIVING"), 2
        )
        fuel_stops_count = len([s for s in hos_result["stops"] if s["type"] == "FUEL"])
        rest_stops_count = len([s for s in hos_result["stops"] if s["type"] in ["REST_BREAK", "DAILY_REST", "CYCLE_RESTART"]])

        response_data = {
            "inputs": {
                "current_location": current_coords,
                "pickup_location": pickup_coords,
                "dropoff_location": dropoff_coords,
                "current_cycle_used": current_cycle_used
            },
            "summary": {
                "total_miles": hos_result["total_miles"],
                "total_trip_duration_hours": hos_result["total_trip_duration_hours"],
                "total_driving_hours": total_driving_hours,
                "total_rest_hours": total_rest_hours,
                "total_on_duty_hours": total_on_duty_hours,
                "fuel_stops_count": fuel_stops_count,
                "rest_stops_count": rest_stops_count,
                "final_cycle_used": hos_result["final_cycle_used"],
                "cycle_hours_remaining": hos_result["cycle_hours_remaining"],
                "days_count": len(daily_sheets)
            },
            "stops": hos_result["stops"],
            "route_geometry": combined_coords,
            "daily_logs": daily_sheets,
            "events": hos_result["events"]
        }

        return Response(response_data)

    except Exception as e:
        traceback.print_exc()
        return Response(
            {"error": f"Trip calculation failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
