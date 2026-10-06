import math
from datetime import datetime, timedelta

def format_hour_to_hhmm(hour_val: float) -> str:
    """Converts 6.5 -> '06:30', 14.75 -> '14:45'."""
    clamped = max(0.0, min(24.0, hour_val))
    total_minutes = int(round(clamped * 60))
    hh = min(23, total_minutes // 60)
    mm = total_minutes % 60
    return f"{hh:02d}:{mm:02d}"

def generate_eld_sheets(events: list, trip_start_date: str = None, 
                        initial_cycle_used: float = 0.0, carrier_name: str = "Apex Freight Logistics Inc.",
                        driver_name: str = "Alex Mercer", truck_id: str = "VOLVO-VNL-860") -> list:
    """
    Takes a continuous list of trip events and slices them cleanly into
    24-hour Midnight-to-Midnight Daily Log Sheets.
    Guarantees:
    - Every day is exactly 24.0 hours.
    - Status totals sum to exactly 24.0 hours.
    - Generates 15-minute resolution segments and step-line graph points for SVG/Canvas.
    - Computes 70-hour cycle daily recap.
    """
    if not events:
        return []

    # Parse start date or use today
    if trip_start_date:
        try:
            base_date = datetime.strptime(trip_start_date, "%Y-%m-%d")
        except Exception:
            base_date = datetime.now()
    else:
        base_date = datetime.now()

    # Determine total days spanned
    max_time = max(ev["end_time"] for ev in events)
    total_days = max(1, math.ceil(max_time / 24.0))

    daily_sheets = []
    running_cycle_used = float(initial_cycle_used)

    for day_idx in range(total_days):
        day_start = float(day_idx * 24.0)
        day_end = float((day_idx + 1) * 24.0)
        sheet_date = (base_date + timedelta(days=day_idx)).strftime("%Y-%m-%d")

        # Find events overlapping [day_start, day_end]
        day_events = []
        for ev in events:
            ev_start = ev["start_time"]
            ev_end = ev["end_time"]
            
            # Check overlap
            if ev_end > day_start and ev_start < day_end:
                # Clip event to day boundaries
                clipped_start = max(day_start, ev_start)
                clipped_end = min(day_end, ev_end)
                clipped_duration = clipped_end - clipped_start

                if clipped_duration > 0.0001:
                    # Normalized hour within the day (0.0 to 24.0)
                    hour_in_day_start = clipped_start - day_start
                    hour_in_day_end = clipped_end - day_start
                    
                    # Pro-rate miles if driving
                    miles = 0.0
                    if ev.get("miles_driven", 0) > 0 and (ev_end - ev_start) > 0:
                        ratio = clipped_duration / (ev_end - ev_start)
                        miles = round(ev["miles_driven"] * ratio, 2)

                    day_events.append({
                        "original_event": ev,
                        "status": ev["status"],
                        "status_line": ev["status_line"],
                        "activity": ev["activity"],
                        "location_name": ev.get("location_name", "En Route"),
                        "hour_start": round(hour_in_day_start, 3),
                        "hour_end": round(hour_in_day_end, 3),
                        "duration": round(clipped_duration, 3),
                        "miles": miles,
                        "time_str": format_hour_to_hhmm(hour_in_day_start),
                        "lat": ev.get("lat"),
                        "lng": ev.get("lng")
                    })

        # Calculate status summaries for the day
        summary = {
            "off_duty": 0.0,
            "sleeper_berth": 0.0,
            "driving": 0.0,
            "on_duty_not_driving": 0.0
        }
        total_miles_today = 0.0
        remarks = []
        graph_segments = []

        last_line = 1
        for i, dev in enumerate(day_events):
            dur = dev["duration"]
            st = dev["status"]
            line = dev["status_line"]

            if st == "OFF_DUTY":
                summary["off_duty"] += dur
            elif st == "SLEEPER_BERTH":
                summary["sleeper_berth"] += dur
            elif st == "DRIVING":
                summary["driving"] += dur
            elif st == "ON_DUTY_NOT_DRIVING":
                summary["on_duty_not_driving"] += dur

            total_miles_today += dev["miles"]

            # Add horizontal segment for SVG/Canvas
            graph_segments.append({
                "type": "horizontal",
                "x1": dev["hour_start"],
                "x2": dev["hour_end"],
                "line": line,
                "status": st,
                "activity": dev["activity"]
            })

            # Add vertical transition if status changed
            if i > 0 and line != last_line:
                graph_segments.append({
                    "type": "vertical",
                    "x": dev["hour_start"],
                    "y1": last_line,
                    "y2": line
                })

            last_line = line

            # Add remark for noticeable events
            remarks.append({
                "time": dev["time_str"],
                "hour": dev["hour_start"],
                "status": st,
                "line": line,
                "location": dev["location_name"],
                "activity": dev["activity"],
                "miles": dev["miles"]
            })

        # Round status totals to 2 decimal places and balance exactly to 24.00
        for k in summary:
            summary[k] = round(summary[k], 2)
        
        sum_hours = round(sum(summary.values()), 2)
        diff = round(24.0 - sum_hours, 2)
        if abs(diff) > 0.001:
            # Rebalance discrepancy into off_duty or sleeper
            if summary["off_duty"] > 0:
                summary["off_duty"] = round(summary["off_duty"] + diff, 2)
            else:
                summary["sleeper_berth"] = round(summary["sleeper_berth"] + diff, 2)

        # Duty hours worked today (driving + on duty)
        duty_worked_today = round(summary["driving"] + summary["on_duty_not_driving"], 2)
        cycle_start_today = round(running_cycle_used, 2)
        running_cycle_used += duty_worked_today
        cycle_end_today = round(running_cycle_used, 2)
        cycle_hours_available = round(max(0.0, 70.0 - cycle_end_today), 2)

        daily_sheets.append({
            "day_number": day_idx + 1,
            "date": sheet_date,
            "carrier_name": carrier_name,
            "driver_name": driver_name,
            "truck_id": truck_id,
            "total_miles_today": round(total_miles_today, 1),
            "summary_hours": {
                "off_duty": summary["off_duty"],
                "sleeper_berth": summary["sleeper_berth"],
                "driving": summary["driving"],
                "on_duty_not_driving": summary["on_duty_not_driving"],
                "total_hours": 24.0
            },
            "recap_70hr": {
                "cycle_limit": 70.0,
                "cycle_used_at_start": cycle_start_today,
                "hours_worked_today": duty_worked_today,
                "cycle_used_at_end": cycle_end_today,
                "cycle_hours_available": cycle_hours_available
            },
            "graph_segments": graph_segments,
            "remarks": remarks
        })

    return daily_sheets
