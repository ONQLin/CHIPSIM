"""Communication orchestration with HYDRA HBM service constraints."""

from __future__ import annotations

from typing import Any

from src.sim.communication_orchestrator import CommunicationOrchestrator

from .memory_placement import HydraMemoryPlacement


class HydraCommunicationOrchestrator(CommunicationOrchestrator):
    def __init__(
        self,
        *args: Any,
        memory_placement: HydraMemoryPlacement,
        bits_per_packet: int,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.memory_placement: HydraMemoryPlacement = memory_placement
        self.bits_per_packet: int = bits_per_packet

    def _update_simulation_results(
        self,
        network_stats: dict[str, Any] | None,
        active_mapped_models: dict[int, Any],
        active_phases: list[tuple[int, int, int, int, str]],
        global_time_us: float,
    ) -> bool:
        updated: bool = super()._update_simulation_results(
            network_stats,
            active_mapped_models,
            active_phases,
            global_time_us,
        )
        packet_bytes: float = self.bits_per_packet / 8.0
        for model_id, input_id, phase_id, _, phase_type in active_phases:
            if phase_type != "WEIGHT_LOADING_COMM":
                continue
            mapped_model: Any = active_mapped_models[model_id]
            instance: Any = mapped_model.phase_instances[input_id][phase_id]
            if getattr(instance, "hydra_hbm_latency_applied", False):
                continue
            phase: Any = mapped_model.phases[phase_id]
            traffic: dict[int, dict[int, int]] = phase.traffic or {}
            transferred_bytes: dict[int, int] = {
                source_id: int(
                    sum(destinations.values()) * packet_bytes
                )
                for source_id, destinations in traffic.items()
            }
            hbm_latency_us: float = self.memory_placement.service_latency_us(
                transferred_bytes
            )
            instance.latency_us = max(instance.latency_us, hbm_latency_us)
            instance.hydra_hbm_latency_us = hbm_latency_us
            instance.hydra_hbm_latency_applied = True
        return updated
