"""CHIPSIM runner that activates the additive HYDRA adapters."""

from __future__ import annotations

from typing import Any

from src.run.simulation_runner import SimulationRunner

from .global_manager import HydraGlobalManager


class HydraSimulationRunner(SimulationRunner):
    def _initialize_global_manager(self) -> None:
        print("Initializing HYDRA-aware Global Manager...")
        simulation: dict[str, Any] = self.config["simulation"]
        input_files: dict[str, Any] = simulation["input_files"]
        core_settings: dict[str, Any] = simulation["core_settings"]
        hardware: dict[str, Any] = simulation["hardware_parameters"]
        gem5: dict[str, Any] = simulation.get("gem5_parameters", {})
        dsent: dict[str, Any] = simulation.get("dsent_parameters", {})

        self.gm = HydraGlobalManager(
            wl_file_name=input_files["workload"],
            adj_matrix_file=input_files["adj_matrix"],
            chiplet_mapping_file=input_files["chiplet_mapping"],
            model_definitions_file=input_files["model_defs"],
            hydra_weight_placement_file=input_files["hydra_weight_placement"],
            hydra_execution_mapping_file=input_files["hydra_execution_mapping"],
            clear_cache=core_settings["clear_cache"],
            communication_simulator=core_settings["comm_simulator"],
            communication_method=core_settings["comm_method"],
            enable_dsent=core_settings["enable_dsent"],
            bits_per_activation=hardware["bits_per_activation"],
            bits_per_packet=hardware["bits_per_packet"],
            network_operation_frequency_hz=hardware[
                "network_operation_frequency_hz"
            ],
            gem5_sim_cycles=gem5.get("gem5_sim_cycles", 500_000_000),
            gem5_injection_rate=gem5.get("gem5_injection_rate", 0.0),
            gem5_ticks_per_cycle=gem5.get("gem5_ticks_per_cycle", 1000),
            gem5_deadlock_threshold=gem5.get("gem5_deadlock_threshold"),
            dsent_tech_node=dsent.get("dsent_tech_node", "32"),
            enable_comm_cache=core_settings["enable_comm_cache"],
            warmup_period_us=core_settings.get("warmup_period_us", 0.0),
            blocking_age_threshold=core_settings["blocking_age_threshold"],
            weight_stationary=core_settings["weight_stationary"],
            weight_loading_strategy=core_settings["weight_loading_strategy"],
        )
        print("HYDRA-aware Global Manager initialized")
