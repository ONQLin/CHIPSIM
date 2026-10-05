"""Explicit HBM weight placement imported from a HYDRA system snapshot."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from src.core.system import System


@dataclass(frozen=True)
class HydraWeightShard:
    source_chiplet_id: int
    fraction: float
    weight_bytes: int


class HydraMemoryPlacement:
    """Validated mapping from translated CHIPSIM layers to HYDRA HBM shards."""

    def __init__(self, placement_file: str | Path, system: System) -> None:
        self.placement_file: Path = Path(placement_file)
        with self.placement_file.open("r", encoding="utf-8") as stream:
            self.data: dict[str, Any] = json.load(stream)
        self.layer_to_block: dict[int, int] = {
            int(layer_id): int(block_id)
            for layer_id, block_id in self.data["layer_to_block"].items()
        }
        self.blocks: dict[int, dict[str, Any]] = {
            int(block_id): block
            for block_id, block in self.data["blocks"].items()
        }
        self.memories: dict[int, dict[str, Any]] = {
            int(memory["chipsim_chiplet_id"]): memory
            for memory in self.data["memories"]
        }
        self._validate(system)

    def _validate(self, system: System) -> None:
        if int(self.data.get("schema_version", 0)) != 1:
            raise ValueError("Unsupported HYDRA weight-placement schema.")
        for memory_id, memory in self.memories.items():
            if not system.is_io_chiplet(memory_id):
                raise ValueError(
                    f"HYDRA HBM source {memory_id} is not an I/O chiplet in CHIPSIM."
                )
            if float(memory["bandwidth_bytes_per_second"]) <= 0:
                raise ValueError(f"HYDRA HBM source {memory_id} has no bandwidth.")
            if int(memory["capacity_bytes"]) <= 0:
                raise ValueError(f"HYDRA HBM source {memory_id} has no capacity.")

        allocated_bytes: dict[int, int] = {memory_id: 0 for memory_id in self.memories}
        for block_id, block in self.blocks.items():
            shards: list[dict[str, Any]] = list(block.get("shards", []))
            if not shards:
                raise ValueError(f"HYDRA block {block_id} has no HBM weight shard.")
            fraction_sum: float = sum(float(shard["fraction"]) for shard in shards)
            if abs(fraction_sum - 1.0) > 1e-6:
                raise ValueError(
                    f"HYDRA block {block_id} shard fractions sum to {fraction_sum}."
                )
            for shard in shards:
                source_id: int = int(shard["chipsim_memory_chiplet_id"])
                if source_id not in self.memories:
                    raise ValueError(
                        f"HYDRA block {block_id} references unknown HBM {source_id}."
                    )
                allocated_bytes[source_id] += int(shard["weight_bytes"])

        for memory_id, used_bytes in allocated_bytes.items():
            capacity_bytes: int = int(self.memories[memory_id]["capacity_bytes"])
            if used_bytes > capacity_bytes:
                raise ValueError(
                    f"HYDRA HBM {memory_id} stores {used_bytes} bytes but has "
                    f"capacity {capacity_bytes}."
                )

    def shards_for_layer(self, layer_id: int) -> list[HydraWeightShard]:
        block_id: int = self.layer_to_block[layer_id]
        return [
            HydraWeightShard(
                source_chiplet_id=int(shard["chipsim_memory_chiplet_id"]),
                fraction=float(shard["fraction"]),
                weight_bytes=int(shard["weight_bytes"]),
            )
            for shard in self.blocks[block_id]["shards"]
        ]

    def service_latency_us(
        self,
        transferred_bytes: dict[int, int],
    ) -> float:
        """Return parallel HBM service time for one weight-transfer phase."""
        source_latencies: list[float] = []
        for source_id, byte_count in transferred_bytes.items():
            memory: dict[str, Any] = self.memories[source_id]
            bandwidth: float = float(memory["bandwidth_bytes_per_second"])
            access_us: float = float(memory["access_latency_ns"]) / 1000.0
            source_latencies.append(access_us + byte_count / bandwidth * 1e6)
        return max(source_latencies, default=0.0)
