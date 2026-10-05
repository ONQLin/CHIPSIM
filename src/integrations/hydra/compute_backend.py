"""Compute backend for latency and energy profiles supplied by HYDRA."""

from __future__ import annotations

from typing import Any


class HydraComputeBackend:
    def simulate(
        self,
        partitioned_layer: dict[str, Any],
        chiplet_id: int,
        chiplet_type: str,
    ) -> dict[str, float | int]:
        profiles: dict[str, dict[str, float]] = partitioned_layer.get(
            "hydra_compute_profiles",
            {},
        )
        if chiplet_type not in profiles:
            raise ValueError(
                f"HYDRA layer has no compute profile for chiplet type "
                f"'{chiplet_type}' (chiplet {chiplet_id})."
            )
        profile: dict[str, float] = profiles[chiplet_type]
        fraction: float = float(partitioned_layer.get("percentage", 100.0)) / 100.0
        latency_us: float = float(profile["latency_us"]) * fraction
        energy_fj: float = float(profile["energy_fj"]) * fraction
        frequency_hz: float = float(profile.get("frequency_hz", 1e9))
        return {
            "latency_us": latency_us,
            "energy_fj": energy_fj,
            "cycles": int(round(latency_us * frequency_hz / 1e6)),
        }
