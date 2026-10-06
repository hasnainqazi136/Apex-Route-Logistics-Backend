import math
from .routing import sample_coord_at_ratio

# FMCSA HOS Regulation Constants (Property-Carrying 70hr/8day)
MAX_DRIVE_HOURS_PER_SHIFT = 11.0      # § 395.3(a)(3)(i)
MAX_DUTY_WINDOW_HOURS = 14.0          # § 395.3(a)(2)
MAX_DRIVE_BEFORE_BREAK = 8.0          # § 395.3(a)(3)(ii)
REQUIRED_BREAK_HOURS = 0.5            # 30 minutes rest break
REQUIRED_DAILY_REST_HOURS = 10.0      # 10 consecutive hours off duty/sleeper
MAX_CYCLE_HOURS = 70.0                # 70 hours in 8 days
RESTART_HOURS = 34.0                  # 34-hour restart
FUEL_INTERVAL_MILES = 1000.0          # Fuel at least once every 1,000 miles
FUEL_DURATION_HOURS = 0.5             # 30 minutes on-duty
PICKUP_DURATION_HOURS = 1.0           # 1 hour on-duty
DROPOFF_DURATION_HOURS = 1.0          # 1 hour on-duty
PRE_TRIP_INSPECTION_HOURS = 0.25      # 15 minutes on-duty

STATUS_OFF_DUTY = "OFF_DUTY"                 # Line 1
STATUS_SLEEPER = "SLEEPER_BERTH"             # Line 2
STATUS_DRIVING = "DRIVING"                   # Line 3
STATUS_ON_DUTY = "ON_DUTY_NOT_DRIVING"       # Line 4

STATUS_TO_LINE = {
    STATUS_OFF_DUTY: 1,
    STATUS_SLEEPER: 2,
    STATUS_DRIVING: 3,
    STATUS_ON_DUTY: 4
}


class HOSSimulation:
    def __init__(self, current_cycle_used_hours: float, start_hour_of_day: float = 6.0):
        """
        start_hour_of_day: 6.0 means Day 1 starts at 06:00 AM after 10hr sleeper berth.
        current_cycle_used_hours: Hours already accumulated in 70-hour cycle.
        """
        self.clock = float(start_hour_of_day)  # continuous time from Day 1 00:00
        self.cycle_used = float(current_cycle_used_hours)
        self.drive_in_shift = 0.0
        self.duty_window_elapsed = 0.0
        self.drive_since_break = 0.0
        self.miles_since_fuel = 0.0
        self.cumulative_miles = 0.0
        
        self.events = []
        self.stops = []
        
        # Day 1 initial rest prior to 06:00 AM (midnight to start_hour)
        if start_hour_of_day > 0:
            self.events.append({
                "start_time": 0.0,
                "end_time": float(start_hour_of_day),
                "duration_hours": float(start_hour_of_day),
                "status": STATUS_SLEEPER,
                "status_line": 2,
                "activity": "Pre-Trip Sleeper Berth Rest",
                "location_name": "Origin / Terminal",
                "miles_driven": 0.0,
                "cumulative_miles": 0.0,
                "lat": None,
                "lng": None
            })

    def add_event(self, duration: float, status: str, activity: str, loc_name: str, 
                  miles: float = 0.0, lat: float = None, lng: float = None):
        """Records an event and updates clocks."""
        start = self.clock
        end = start + duration
        
        self.events.append({
            "start_time": round(start, 4),
            "end_time": round(end, 4),
            "duration_hours": round(duration, 4),
            "status": status,
            "status_line": STATUS_TO_LINE[status],
            "activity": activity,
            "location_name": loc_name,
            "miles_driven": round(miles, 2),
            "cumulative_miles": round(self.cumulative_miles + miles, 2),
            "lat": lat,
            "lng": lng
        })
        
        self.clock = end
        self.cumulative_miles += miles
        
        # Update duty window
        self.duty_window_elapsed += duration

        # Update cycle hours if On Duty or Driving
        if status in [STATUS_DRIVING, STATUS_ON_DUTY]:
            self.cycle_used += duration

        if status == STATUS_DRIVING:
            self.drive_in_shift += duration
            self.drive_since_break += duration
            self.miles_since_fuel += miles

    def take_30m_break(self, loc_name: str, lat: float, lng: float):
        """Mandatory 30-minute break after 8 hours of driving."""
        self.add_event(
            duration=REQUIRED_BREAK_HOURS,
            status=STATUS_OFF_DUTY,
            activity="Mandatory 30-Min Rest Break",
            loc_name=loc_name,
            miles=0.0,
            lat=lat,
            lng=lng
        )
        self.drive_since_break = 0.0
        
        self.stops.append({
            "type": "REST_BREAK",
            "name": f"30-Min Rest Break ({loc_name})",
            "time_hours": self.clock - REQUIRED_BREAK_HOURS,
            "duration": "30 mins",
            "cumulative_miles": self.cumulative_miles,
            "lat": lat,
            "lng": lng,
            "description": "FMCSA 30-minute rest break taken after driving."
        })

    def take_10hr_rest(self, loc_name: str, lat: float, lng: float, reason="Daily 10-Hour Reset"):
        """Mandatory 10 consecutive hours rest to reset 11h driving & 14h window."""
        self.add_event(
            duration=REQUIRED_DAILY_REST_HOURS,
            status=STATUS_SLEEPER,
            activity=f"{reason} (Sleeper Berth)",
            loc_name=loc_name,
            miles=0.0,
            lat=lat,
            lng=lng
        )
        # Reset 11-hour and 14-hour clocks
        self.drive_in_shift = 0.0
        self.duty_window_elapsed = 0.0
        self.drive_since_break = 0.0
        
        self.stops.append({
            "type": "DAILY_REST",
            "name": f"10-Hour Sleeper Berth ({loc_name})",
            "time_hours": self.clock - REQUIRED_DAILY_REST_HOURS,
            "duration": "10 hours",
            "cumulative_miles": self.cumulative_miles,
            "lat": lat,
            "lng": lng,
            "description": f"FMCSA 10-hour consecutive off-duty rest to reset shift clocks."
        })

    def take_34hr_restart(self, loc_name: str, lat: float, lng: float):
        """34-hour restart if 70-hour cycle exhausted."""
        self.add_event(
            duration=RESTART_HOURS,
            status=STATUS_OFF_DUTY,
            activity="34-Hour Cycle Restart",
            loc_name=loc_name,
            miles=0.0,
            lat=lat,
            lng=lng
        )
        self.cycle_used = 0.0
        self.drive_in_shift = 0.0
        self.duty_window_elapsed = 0.0
        self.drive_since_break = 0.0
        
        self.stops.append({
            "type": "CYCLE_RESTART",
            "name": f"34-Hour Restart ({loc_name})",
            "time_hours": self.clock - RESTART_HOURS,
            "duration": "34 hours",
            "cumulative_miles": self.cumulative_miles,
            "lat": lat,
            "lng": lng,
            "description": "FMCSA 34-hour restart taken to reset 70-hour 8-day cycle."
        })

    def take_fuel_stop(self, loc_name: str, lat: float, lng: float):
        """Fueling stop every 1,000 miles (30 min on duty)."""
        self.add_event(
            duration=FUEL_DURATION_HOURS,
            status=STATUS_ON_DUTY,
            activity="Fuel Stop & Vehicle Inspection",
            loc_name=loc_name,
            miles=0.0,
            lat=lat,
            lng=lng
        )
        self.miles_since_fuel = 0.0
        
        self.stops.append({
            "type": "FUEL",
            "name": f"Fuel Stop ({loc_name})",
            "time_hours": self.clock - FUEL_DURATION_HOURS,
            "duration": "30 mins",
            "cumulative_miles": self.cumulative_miles,
            "lat": lat,
            "lng": lng,
            "description": "Commercial truck fueling and mid-trip vehicle walkaround."
        })

    def simulate_driving_leg(self, leg_miles: float, leg_duration: float, 
                             origin_name: str, dest_name: str, 
                             origin_coords: dict, dest_coords: dict,
                             leg_coordinates: list):
        """
        Simulates driving along a leg with real-time HOS constraints checking:
        - 30 min break after 8h driving
        - 10h rest after 11h driving or 14h window
        - Fuel stop at 1,000 miles
        - 34h restart if cycle limit reached
        """
        miles_remaining = leg_miles
        hours_remaining = leg_duration
        leg_miles_done = 0.0

        while miles_remaining > 0.05 and hours_remaining > 0.01:
            # Check 70-hour cycle limit
            if self.cycle_used >= MAX_CYCLE_HOURS:
                ratio = min(1.0, max(0.0, leg_miles_done / leg_miles)) if leg_miles > 0 else 0
                coord = sample_coord_at_ratio(leg_coordinates, ratio)
                self.take_34hr_restart(f"En Route ({origin_name} to {dest_name})", coord[1], coord[0])

            # Determine maximum drive time possible before hitting any constraint:
            drive_avail_shift = MAX_DRIVE_HOURS_PER_SHIFT - self.drive_in_shift
            drive_avail_window = MAX_DUTY_WINDOW_HOURS - self.duty_window_elapsed
            drive_avail_break = MAX_DRIVE_BEFORE_BREAK - self.drive_since_break
            
            # Fuel limit check in hours
            miles_until_fuel = max(0.0, FUEL_INTERVAL_MILES - self.miles_since_fuel)
            if miles_remaining > 0:
                avg_speed = leg_miles / leg_duration
                hours_until_fuel = miles_until_fuel / avg_speed if avg_speed > 0 else 999.0
            else:
                hours_until_fuel = 999.0

            # Cycle limit in hours
            hours_until_cycle_limit = max(0.0, MAX_CYCLE_HOURS - self.cycle_used)

            # Available driving block before the NEXT constraint hits
            can_drive_hours = min(
                hours_remaining,
                drive_avail_shift,
                drive_avail_window,
                drive_avail_break,
                hours_until_fuel,
                hours_until_cycle_limit
            )

            # If driver has exhausted shift or window (<= 0.05 hr left)
            if drive_avail_shift <= 0.05 or drive_avail_window <= 0.05:
                ratio = min(1.0, max(0.0, leg_miles_done / leg_miles)) if leg_miles > 0 else 0
                coord = sample_coord_at_ratio(leg_coordinates, ratio)
                reason = "11-Hour Drive Limit Reached" if drive_avail_shift <= 0.05 else "14-Hour Duty Window Reached"
                self.take_10hr_rest(f"Highway Rest Area ({origin_name} to {dest_name})", coord[1], coord[0], reason)
                continue

            # If 8 hours driving reached before break
            if drive_avail_break <= 0.05:
                ratio = min(1.0, max(0.0, leg_miles_done / leg_miles)) if leg_miles > 0 else 0
                coord = sample_coord_at_ratio(leg_coordinates, ratio)
                self.take_30m_break(f"Travel Center ({origin_name} to {dest_name})", coord[1], coord[0])
                continue

            # If fueling needed
            if hours_until_fuel <= 0.05 or self.miles_since_fuel >= FUEL_INTERVAL_MILES:
                ratio = min(1.0, max(0.0, leg_miles_done / leg_miles)) if leg_miles > 0 else 0
                coord = sample_coord_at_ratio(leg_coordinates, ratio)
                self.take_fuel_stop(f"Truck Stop Fueling Plaza", coord[1], coord[0])
                continue

            # If cycle limit hit
            if hours_until_cycle_limit <= 0.05:
                ratio = min(1.0, max(0.0, leg_miles_done / leg_miles)) if leg_miles > 0 else 0
                coord = sample_coord_at_ratio(leg_coordinates, ratio)
                self.take_34hr_restart(f"Truck Plaza ({origin_name} to {dest_name})", coord[1], coord[0])
                continue

            # Drive this chunk!
            chunk_hours = max(0.05, can_drive_hours)
            chunk_hours = min(chunk_hours, hours_remaining)
            chunk_miles = round((chunk_hours / leg_duration) * leg_miles, 2)
            chunk_miles = min(chunk_miles, miles_remaining)

            leg_miles_done += chunk_miles
            ratio = min(1.0, max(0.0, leg_miles_done / leg_miles)) if leg_miles > 0 else 1.0
            coord = sample_coord_at_ratio(leg_coordinates, ratio)

            self.add_event(
                duration=chunk_hours,
                status=STATUS_DRIVING,
                activity=f"Driving towards {dest_name}",
                loc_name=f"En Route ({round(leg_miles_done)} mi)",
                miles=chunk_miles,
                lat=coord[1],
                lng=coord[0]
            )

            miles_remaining -= chunk_miles
            hours_remaining -= chunk_hours


def plan_trip_hos(current_loc: dict, pickup_loc: dict, dropoff_loc: dict, 
                  current_cycle_used: float, leg1_route: dict, leg2_route: dict) -> dict:
    """
    Executes the complete HOS simulation for a full freight run:
    Leg 1: Current Location -> Pickup Location
    At Pickup: 1 Hour On-Duty
    Leg 2: Pickup Location -> Dropoff Location
    At Dropoff: 1 Hour On-Duty
    """
    sim = HOSSimulation(current_cycle_used_hours=current_cycle_used, start_hour_of_day=6.0)

    # 1. Start / Pre-trip inspection at Current Location
    sim.stops.append({
        "type": "ORIGIN",
        "name": f"Current Location: {current_loc['name']}",
        "time_hours": sim.clock,
        "duration": "15 mins",
        "cumulative_miles": 0.0,
        "lat": current_loc["lat"],
        "lng": current_loc["lng"],
        "description": "Start point of trip. Pre-trip vehicle inspection performed."
    })
    sim.add_event(
        duration=PRE_TRIP_INSPECTION_HOURS,
        status=STATUS_ON_DUTY,
        activity="Initial Pre-Trip Vehicle Inspection",
        loc_name=current_loc["name"],
        miles=0.0,
        lat=current_loc["lat"],
        lng=current_loc["lng"]
    )

    # 2. Leg 1 Driving: Current Location -> Pickup Location
    if leg1_route["distance_miles"] > 1.0:
        sim.simulate_driving_leg(
            leg_miles=leg1_route["distance_miles"],
            leg_duration=leg1_route["duration_hours"],
            origin_name=current_loc["name"],
            dest_name=pickup_loc["name"],
            origin_coords=current_loc,
            dest_coords=pickup_loc,
            leg_coordinates=leg1_route["coordinates"]
        )

    # 3. Arrive at Pickup Location (1 Hour On-Duty)
    sim.stops.append({
        "type": "PICKUP",
        "name": f"Pickup Location: {pickup_loc['name']}",
        "time_hours": sim.clock,
        "duration": "1.0 hour",
        "cumulative_miles": sim.cumulative_miles,
        "lat": pickup_loc["lat"],
        "lng": pickup_loc["lng"],
        "description": "Cargo loading, paperwork & vehicle securement (1 hour on-duty)."
    })
    sim.add_event(
        duration=PICKUP_DURATION_HOURS,
        status=STATUS_ON_DUTY,
        activity="Cargo Loading & Paperwork (Pickup)",
        loc_name=pickup_loc["name"],
        miles=0.0,
        lat=pickup_loc["lat"],
        lng=pickup_loc["lng"]
    )

    # 4. Leg 2 Driving: Pickup Location -> Dropoff Location
    sim.simulate_driving_leg(
        leg_miles=leg2_route["distance_miles"],
        leg_duration=leg2_route["duration_hours"],
        origin_name=pickup_loc["name"],
        dest_name=dropoff_loc["name"],
        origin_coords=pickup_loc,
        dest_coords=dropoff_loc,
        leg_coordinates=leg2_route["coordinates"]
    )

    # 5. Arrive at Dropoff Location (1 Hour On-Duty)
    sim.stops.append({
        "type": "DROPOFF",
        "name": f"Dropoff Location: {dropoff_loc['name']}",
        "time_hours": sim.clock,
        "duration": "1.0 hour",
        "cumulative_miles": sim.cumulative_miles,
        "lat": dropoff_loc["lat"],
        "lng": dropoff_loc["lng"],
        "description": "Cargo unloading & post-trip vehicle inspection (1 hour on-duty)."
    })
    sim.add_event(
        duration=DROPOFF_DURATION_HOURS,
        status=STATUS_ON_DUTY,
        activity="Cargo Unloading & Post-Trip Inspection (Dropoff)",
        loc_name=dropoff_loc["name"],
        miles=0.0,
        lat=dropoff_loc["lat"],
        lng=dropoff_loc["lng"]
    )

    # Fill remainder of final day to 24:00 with Off Duty
    final_day = math.floor(sim.clock / 24.0)
    end_of_day_clock = (final_day + 1) * 24.0
    if sim.clock < end_of_day_clock:
        rem = end_of_day_clock - sim.clock
        sim.add_event(
            duration=rem,
            status=STATUS_OFF_DUTY,
            activity="Post-Trip Off Duty",
            loc_name=dropoff_loc["name"],
            miles=0.0,
            lat=dropoff_loc["lat"],
            lng=dropoff_loc["lng"]
        )

    return {
        "events": sim.events,
        "stops": sim.stops,
        "total_trip_duration_hours": round(sim.clock, 2),
        "total_miles": round(sim.cumulative_miles, 1),
        "final_cycle_used": round(sim.cycle_used, 2),
        "cycle_hours_remaining": round(max(0.0, MAX_CYCLE_HOURS - sim.cycle_used), 2)
    }
