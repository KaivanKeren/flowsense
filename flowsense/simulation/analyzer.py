"""Post-simulation performance analyzer.

Parses SUMO's output/tripinfo.xml and generates JSON + Markdown reports.
"""

import json
import logging
import os
import statistics
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime

from .sim_config import SIM_DURATION

log = logging.getLogger("flowsense.simulation")

OUTPUT_DIR = "output"
SUMMARY_DIR = os.path.join(OUTPUT_DIR, "summary")
TRIPINFO_PATH = os.path.join(OUTPUT_DIR, "tripinfo.xml")


def _parse_tripinfo(path: str) -> list[dict]:
    """Parse every <tripinfo> element into a list of dicts."""
    if not os.path.exists(path):
        log.error("tripinfo.xml not found at: %s", path)
        return []

    tree = ET.parse(path)
    root = tree.getroot()
    vehicles = []
    for elem in root.iter("tripinfo"):
        try:
            vehicles.append({
                "id":           elem.get("id", ""),
                "vType":        elem.get("vType", "unknown"),
                "duration":     float(elem.get("duration",    0)),
                "waitingTime":  float(elem.get("waitingTime", 0)),
                "timeLoss":     float(elem.get("timeLoss",    0)),
                "waitingCount": int(float(elem.get("waitingCount", 0))),
                "stopTime":     float(elem.get("stopTime",    0)),
                "routeLength":  float(elem.get("routeLength", 0)),
                "departDelay":  float(elem.get("departDelay", 0)),
                "arrival":      float(elem.get("arrival",     0)),
                "fuel_abs":     float(elem.get("fuel_abs",  0)),
                "CO2_abs":      float(elem.get("CO2_abs",   0)),
                "CO_abs":       float(elem.get("CO_abs",    0)),
                "NOx_abs":      float(elem.get("NOx_abs",   0)),
                "PMx_abs":      float(elem.get("PMx_abs",   0)),
            })
        except (ValueError, TypeError):
            continue
    return vehicles


def _compute_global(vehicles: list[dict]) -> dict:
    """Compute overall KPIs across all vehicles."""
    if not vehicles:
        return {}

    def _avg(key):
        vals = [v[key] for v in vehicles]
        return round(statistics.mean(vals), 2) if vals else 0.0

    def _total(key):
        return round(sum(v[key] for v in vehicles), 2)

    stopped = [v for v in vehicles if v["waitingCount"] > 0]
    sim_duration = max([v["arrival"] for v in vehicles]) if vehicles else 0.0

    return {
        "configured_duration_s": float(SIM_DURATION),
        "actual_duration_s":     round(sim_duration, 2),
        "total_vehicles":        len(vehicles),
        "vehicles_stopped":      len(stopped),
        "pct_vehicles_stopped":  round(len(stopped) / len(vehicles) * 100, 1),
        "avg_travel_time_s":     _avg("duration"),
        "avg_waiting_time_s":    _avg("waitingTime"),
        "avg_time_loss_s":       _avg("timeLoss"),
        "avg_stops_per_vehicle": _avg("waitingCount"),
        "avg_depart_delay_s":    _avg("departDelay"),
        "total_fuel_ml":         _total("fuel_abs"),
        "total_fuel_L":          round(_total("fuel_abs") / 1000, 3),
        "total_CO2_mg":          _total("CO2_abs"),
        "total_CO2_kg":          round(_total("CO2_abs") / 1_000_000, 3),
        "total_CO_mg":           _total("CO_abs"),
        "total_NOx_mg":          _total("NOx_abs"),
        "total_PMx_mg":          _total("PMx_abs"),
    }


def _compute_by_vtype(vehicles: list[dict]) -> dict:
    """Compute KPIs grouped by vehicle type."""
    grouped: dict[str, list] = defaultdict(list)
    for v in vehicles:
        grouped[v["vType"]].append(v)

    result = {}
    for vtype, group in sorted(grouped.items()):
        def _avg(key, _group=group):
            vals = [v[key] for v in _group]
            return round(statistics.mean(vals), 2) if vals else 0.0

        result[vtype] = {
            "count":             len(group),
            "avg_travel_time_s": _avg("duration"),
            "avg_waiting_time_s": _avg("waitingTime"),
            "avg_time_loss_s":   _avg("timeLoss"),
            "avg_stops":         _avg("waitingCount"),
            "total_fuel_L":      round(sum(v["fuel_abs"] for v in group) / 1000, 3),
        }
    return result


def _build_report_data(mode_label: str, congested: list[str]) -> dict:
    """Parse XML and assemble the full report data structure."""
    vehicles = _parse_tripinfo(TRIPINFO_PATH)
    return {
        "timestamp":       datetime.now().isoformat(timespec="seconds"),
        "simulation_mode": mode_label,
        "congested_directions": congested,
        "global":          _compute_global(vehicles),
        "by_vehicle_type": _compute_by_vtype(vehicles),
    }


def _write_json(data: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _write_markdown(data: dict, path: str) -> None:
    g    = data.get("global", {})
    mode = data["simulation_mode"]
    ts   = data["timestamp"]
    cong = ", ".join(data.get("congested_directions", [])) or "none"

    lines = [
        f"# Simulation Performance Report",
        f"",
        f"| Field | Value |",
        f"|:------|:------|",
        f"| Generated | `{ts}` |",
        f"| Mode | **{mode}** |",
        f"| Congested Directions | `{cong}` |",
        f"| Configured Duration | `{g.get('configured_duration_s', 0):.2f} s` |",
        f"| Actual Completion Time | `{g.get('actual_duration_s', 0):.2f} s` |",
        f"",
        f"---",
        f"",
        f"## Global Traffic Metrics",
        f"",
        f"| Metric | Value |",
        f"|:-------|:------|",
        f"| Total Vehicles Served       | **{g.get('total_vehicles', 0):,}** veh |",
        f"| Vehicles That Stopped       | {g.get('vehicles_stopped', 0):,} veh ({g.get('pct_vehicles_stopped', 0)}%) |",
        f"| Avg. Travel Time            | {g.get('avg_travel_time_s', 0):.2f} s |",
        f"| Avg. Waiting Time           | {g.get('avg_waiting_time_s', 0):.2f} s |",
        f"| Avg. Time Loss              | {g.get('avg_time_loss_s', 0):.2f} s |",
        f"| Avg. Stops / Vehicle        | {g.get('avg_stops_per_vehicle', 0):.2f} stops |",
        f"| Avg. Departure Delay        | {g.get('avg_depart_delay_s', 0):.2f} s |",
        f"",
        f"---",
        f"",
        f"## Environmental Impact",
        f"",
        f"| Metric | Value |",
        f"|:-------|:------|",
        f"| Total Fuel Consumed | {g.get('total_fuel_L', 0):.3f} L |",
        f"| Total CO2 Emitted   | {g.get('total_CO2_kg', 0):.3f} kg |",
        f"| Total CO Emitted    | {g.get('total_CO_mg', 0):.1f} mg |",
        f"| Total NOx Emitted   | {g.get('total_NOx_mg', 0):.1f} mg |",
        f"| Total PMx Emitted   | {g.get('total_PMx_mg', 0):.1f} mg |",
        f"",
        f"---",
        f"",
        f"## Performance by Vehicle Type",
        f"",
        f"| Type | Count | Avg Wait (s) | Avg Delay (s) | Avg Stops | Fuel (L) |",
        f"|:-----|------:|-------------:|--------------:|----------:|---------:|",
    ]

    for vtype, stats in data.get("by_vehicle_type", {}).items():
        lines.append(
            f"| {vtype:<12} "
            f"| {stats['count']:>5} "
            f"| {stats['avg_waiting_time_s']:>12.2f} "
            f"| {stats['avg_time_loss_s']:>13.2f} "
            f"| {stats['avg_stops']:>9.2f} "
            f"| {stats['total_fuel_L']:>8.3f} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"*Report auto-generated by FlowSense SUMO Simulation.*",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def print_simulation_report(mode_label: str = "Unknown", congested: list[str] | None = None) -> dict | None:
    """Parse tripinfo.xml, log summary, and write Markdown/JSON reports.

    Returns the report data dict, or None if no data was found.
    """
    if congested is None:
        congested = []

    os.makedirs(SUMMARY_DIR, exist_ok=True)

    log.info("Processing simulation results...")

    data = _build_report_data(mode_label, congested)

    if not data.get("global"):
        log.warning("No vehicle data found — report skipped.")
        return None

    g = data["global"]
    log.info("Simulation Report [%s]: %d vehicles served, avg wait=%.2fs, avg travel=%.2fs, fuel=%.3fL, CO2=%.3fkg",
             mode_label, g.get("total_vehicles", 0), g.get("avg_waiting_time_s", 0),
             g.get("avg_travel_time_s", 0), g.get("total_fuel_L", 0), g.get("total_CO2_kg", 0))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_slug = mode_label.lower().replace(" ", "_").replace("-", "_")
    base_name = f"report_{mode_slug}_{timestamp}"

    json_path = os.path.join(SUMMARY_DIR, base_name + ".json")
    md_path   = os.path.join(SUMMARY_DIR, base_name + ".md")

    _write_json(data, json_path)
    _write_markdown(data, md_path)

    log.info("Report saved: %s, %s", md_path, json_path)
    return data
