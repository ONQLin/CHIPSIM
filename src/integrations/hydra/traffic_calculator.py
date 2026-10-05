"""CHIPSIM traffic generation using HYDRA's explicit weight locations."""

from __future__ import annotations

from typing import Any

from src.core.comm_types import TrafficMatrixDict
from src.core.system import System
from src.core.traffic_calculator import TrafficCalculator

from .memory_placement import HydraMemoryPlacement, HydraWeightShard


class HydraTrafficCalculator(TrafficCalculator):
    def __init__(
        self,
        system: System,
        memory_placement: HydraMemoryPlacement,
        bits_per_activation: int = 8,
        bits_per_packet: int = 128,
    ) -> None:
        super().__init__(system, bits_per_activation, bits_per_packet)
        self.memory_placement: HydraMemoryPlacement = memory_placement

    def _calculate_single_layer_weight_traffic(
        self,
        layer_idx: int,
        model_metrics: list[dict[str, Any]],
        mapping: list[tuple[int, list[tuple[int, float]]]],
    ) -> TrafficMatrixDict:
        layer_metrics: dict[str, Any] | None = next(
            (
                metrics
                for metrics in model_metrics
                if metrics.get("name") == f"layer_{layer_idx}"
            ),
            None,
        )
        if layer_metrics is None:
            raise ValueError(f"Metrics are missing for HYDRA layer {layer_idx}.")
        num_weights: int = int(layer_metrics.get("num_weights", 0))
        if num_weights == 0:
            return {}

        layer_mapping: list[tuple[int, float]] | None = next(
            (
                chiplet_mappings
                for mapped_layer, chiplet_mappings in mapping
                if mapped_layer == layer_idx
            ),
            None,
        )
        if not layer_mapping:
            raise ValueError(f"Mapping is missing for HYDRA layer {layer_idx}.")

        shards: list[HydraWeightShard] = self.memory_placement.shards_for_layer(
            layer_idx
        )
        traffic: TrafficMatrixDict = {}
        for destination_id, destination_fraction in layer_mapping:
            if self.system.is_io_chiplet(destination_id):
                raise ValueError(
                    f"HYDRA layer {layer_idx} maps compute to HBM {destination_id}."
                )
            chiplet: Any = self.system.chiplets[destination_id - 1]
            weights_for_destination: int = int(
                num_weights * destination_fraction / 100.0
            )
            for shard in shards:
                weight_bits: int = int(
                    weights_for_destination
                    * shard.fraction
                    * int(chiplet.bits_per_weight)
                )
                if weight_bits <= 0:
                    continue
                packets: int = max(1, weight_bits // self.bits_per_packet)
                source_traffic: dict[int, int] = traffic.setdefault(
                    shard.source_chiplet_id,
                    {},
                )
                source_traffic[destination_id] = (
                    source_traffic.get(destination_id, 0) + packets
                )
        return traffic
