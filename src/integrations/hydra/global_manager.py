"""Additive CHIPSIM manager for HYDRA-owned memory and compute decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.sim.global_manager import GlobalManager

from .compute_backend import HydraComputeBackend
from .communication_orchestrator import HydraCommunicationOrchestrator
from .memory_placement import HydraMemoryPlacement
from .model_mapper import HydraModelMapper
from .traffic_calculator import HydraTrafficCalculator


class HydraGlobalManager(GlobalManager):
    def __init__(
        self,
        *args: Any,
        hydra_weight_placement_file: str | Path,
        hydra_execution_mapping_file: str | Path,
        **kwargs: Any,
    ) -> None:
        self.hydra_weight_placement_file: Path = Path(
            hydra_weight_placement_file
        )
        self.hydra_execution_mapping_file: Path = Path(
            hydra_execution_mapping_file
        )
        with self.hydra_execution_mapping_file.open(
            "r", encoding="utf-8"
        ) as stream:
            self.hydra_execution: dict[str, Any] = json.load(stream)
        self.hydra_compute_backend: HydraComputeBackend = HydraComputeBackend()
        super().__init__(*args, **kwargs)

    def _initialize_system_components(
        self,
        bits_per_activation: int,
        bits_per_packet: int,
    ) -> None:
        super()._initialize_system_components(
            bits_per_activation=bits_per_activation,
            bits_per_packet=bits_per_packet,
        )
        self.hydra_memory_placement: HydraMemoryPlacement = HydraMemoryPlacement(
            self.hydra_weight_placement_file,
            self.system,
        )
        self.traffic_calculator = HydraTrafficCalculator(
            system=self.system,
            memory_placement=self.hydra_memory_placement,
            bits_per_activation=bits_per_activation,
            bits_per_packet=bits_per_packet,
        )
        layer_mapping: dict[int, int] = {
            int(layer_id): int(chiplet_id)
            for layer_id, chiplet_id in self.hydra_execution[
                "layer_mapping"
            ].items()
        }
        self.model_mapper = HydraModelMapper(
            system=self.system,
            layer_mapping=layer_mapping,
        )

    def _initialize_orchestration(self) -> None:
        super()._initialize_orchestration()
        self.comm_orchestrator = HydraCommunicationOrchestrator(
            comm_simulator=self.comm_simulator,
            dsent_collector=self.dsent_collector,
            system=self.system,
            memory_placement=self.hydra_memory_placement,
            bits_per_packet=self.bits_per_packet,
        )

    def simulate_compute(
        self,
        model_name: str,
        layer_idx: int,
        chiplet_id: int,
        partitioned_layer: dict[str, Any],
        num_layers: int,
        model_idx: int,
    ) -> dict[str, Any]:
        chiplet_type: str = self.system.chiplet_mapping[chiplet_id]
        chiplet_params: dict[str, Any] = self.system.get_chiplet_params(
            chiplet_id
        )
        if chiplet_params.get("compute_backend") == "HYDRA":
            return self.hydra_compute_backend.simulate(
                partitioned_layer=partitioned_layer,
                chiplet_id=chiplet_id,
                chiplet_type=chiplet_type,
            )
        return super().simulate_compute(
            model_name=model_name,
            layer_idx=layer_idx,
            chiplet_id=chiplet_id,
            partitioned_layer=partitioned_layer,
            num_layers=num_layers,
            model_idx=model_idx,
        )
