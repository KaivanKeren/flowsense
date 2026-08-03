"""Simulation step logger — writes per-step traffic metrics to CSV."""

import csv
import logging
import os

log = logging.getLogger("flowsense.simulation")


class SimulationLogger:
    """Logs per-step simulation metrics to a CSV file for post-analysis."""

    FIELDNAMES = [
        "sim_time",
        "phase",
        "active_direction",
        "queue_N", "queue_S", "queue_E", "queue_W",
        "vehicles_N", "vehicles_S", "vehicles_E", "vehicles_W",
        "total_waiting_vehicles",
        "elapsed_green",
        "decision_event",
    ]

    def __init__(self, output_path="output/simulation_log.csv", interval_steps=100):
        self.output_path = output_path
        self.interval_steps = max(1, interval_steps)
        self._step_counter = 0
        self._pending_event = ""

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        self._file = open(output_path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.FIELDNAMES)
        self._writer.writeheader()
        self._file.flush()

        log.info("SimulationLogger initialized -> %s", output_path)

    def record_event(self, event_text: str):
        """Buffer a decision event string (GAP-OUT, MAX-OUT, SKIP, EVP, etc.)."""
        if self._pending_event:
            self._pending_event += "; " + event_text
        else:
            self._pending_event = event_text

    def log_step(self, sim_time: float, phase: str, active_direction: str,
                 queues: dict, vehicles: dict, elapsed_green: float):
        self._step_counter += 1

        if self._step_counter % self.interval_steps != 0:
            return

        total_waiting = sum(queues.get(d, 0) for d in ["N", "S", "E", "W"])

        row = {
            "sim_time": round(sim_time, 1),
            "phase": phase,
            "active_direction": active_direction,
            "queue_N": queues.get("N", 0),
            "queue_S": queues.get("S", 0),
            "queue_E": queues.get("E", 0),
            "queue_W": queues.get("W", 0),
            "vehicles_N": vehicles.get("N", 0),
            "vehicles_S": vehicles.get("S", 0),
            "vehicles_E": vehicles.get("E", 0),
            "vehicles_W": vehicles.get("W", 0),
            "total_waiting_vehicles": total_waiting,
            "elapsed_green": round(elapsed_green, 1),
            "decision_event": self._pending_event,
        }

        self._writer.writerow(row)
        self._file.flush()
        self._pending_event = ""

    def finalize(self):
        """Close the CSV file handle."""
        try:
            self._file.close()
            log.info("Simulation log saved -> %s", self.output_path)
        except Exception:
            pass
