from app.utils.metrics import MetricsEngine

def test_metrics_logic():
    MetricsEngine.record_task()
    MetricsEngine.record_task()
    MetricsEngine.record_failure()
    MetricsEngine.record_latency(100)
    MetricsEngine.record_latency(200)
    MetricsEngine.record_latency(300)

    stats = MetricsEngine.get_stats()
    print(f"Stats: {stats}")

    assert stats['total_tasks'] == 2
    assert stats['failure_rate_pct'] == 50.0
    # p95 of [100, 200, 300]
    # index = 3 * 0.95 = 2.85 -> 2 (300)
    assert stats['p95_ms'] == 300

if __name__ == "__main__":
    test_metrics_logic()
