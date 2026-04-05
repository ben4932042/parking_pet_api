from __future__ import annotations

from typing import Set

import psutil
from prometheus_client import CollectorRegistry, REGISTRY
from prometheus_client.core import GaugeMetricFamily

_REGISTERED_REGISTRY_IDS: Set[int] = set()


class RuntimeMetricsCollector:
    def __init__(self) -> None:
        self._process = psutil.Process()
        # Prime cpu_percent so subsequent scrapes reflect recent usage.
        self._process.cpu_percent(interval=None)

    def collect(self):
        memory_info = self._process.memory_info()

        yield GaugeMetricFamily(
            "process_cpu_percent",
            "Process CPU usage percentage.",
            value=self._process.cpu_percent(interval=None),
        )
        yield GaugeMetricFamily(
            "process_resident_memory_bytes",
            "Resident memory size in bytes.",
            value=float(memory_info.rss),
        )
        yield GaugeMetricFamily(
            "process_virtual_memory_bytes",
            "Virtual memory size in bytes.",
            value=float(memory_info.vms),
        )


def register_runtime_metrics(
    registry: CollectorRegistry = REGISTRY,
) -> CollectorRegistry:
    registry_id = id(registry)
    if registry_id in _REGISTERED_REGISTRY_IDS:
        return registry

    registry.register(RuntimeMetricsCollector())
    _REGISTERED_REGISTRY_IDS.add(registry_id)
    return registry
