"""Exact layer-to-chiplet mapping imported from HYDRA."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.core.system import System
from src.mapping.model_mapper import ModelMapper


class HydraModelMapper(ModelMapper):
    def __init__(
        self,
        system: System,
        layer_mapping: dict[int, int],
    ) -> None:
        super().__init__(system=system)
        self.hydra_layer_mapping: dict[int, int] = layer_mapping

    def generate_mapping(
        self,
        model_metrics: list[dict[str, Any]],
    ) -> tuple[
        list[tuple[int, list[tuple[int, float]]]] | None,
        np.ndarray,
        str | None,
    ]:
        available: np.ndarray = self.system.get_available_capacity_per_chiplet()
        remaining: np.ndarray = available.copy()
        mapping: list[tuple[int, list[tuple[int, float]]]] = []
        staging_requirement: dict[int, int] = {}
        for layer_id, layer_metrics in enumerate(model_metrics):
            if layer_id not in self.hydra_layer_mapping:
                raise ValueError(f"HYDRA execution mapping omits layer {layer_id}.")
            chiplet_id: int = self.hydra_layer_mapping[layer_id]
            if not self.system.is_compute_chiplet(chiplet_id):
                raise ValueError(
                    f"HYDRA layer {layer_id} targets non-compute chiplet {chiplet_id}."
                )
            required: int = int(layer_metrics.get("num_weights", 0))
            staging_requirement[chiplet_id] = max(
                staging_requirement.get(chiplet_id, 0),
                required,
            )
            mapping.append((layer_id, [(chiplet_id, 100.0)]))

        for chiplet_id, required in staging_requirement.items():
            if remaining[chiplet_id - 1] < required:
                return None, np.array([]), "INSUFFICIENT_MEMORY"
            remaining[chiplet_id - 1] -= required

        if not self.system.update_capacity_availability(remaining):
            return None, np.array([]), "SYSTEM_UPDATE_FAILURE"
        return mapping, available - remaining, None
