from prometheus_client import CollectorRegistry, generate_latest

from infrastructure.monitoring.prometheus import register_runtime_metrics


def test_register_runtime_metrics_exposes_process_cpu_and_memory_metrics():
    registry = CollectorRegistry()

    register_runtime_metrics(registry)
    register_runtime_metrics(registry)

    metrics_payload = generate_latest(registry).decode("utf-8")

    assert "process_cpu_percent" in metrics_payload
    assert "process_resident_memory_bytes" in metrics_payload
    assert "process_virtual_memory_bytes" in metrics_payload
