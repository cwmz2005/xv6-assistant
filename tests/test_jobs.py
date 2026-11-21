from backend.core import jobs


def test_active_worker_is_not_recovered_as_failed():
    assert jobs.worker_alive(
        {
            "worker_host": jobs.worker_host,
            "worker_pid": jobs.worker_pid,
            "worker_started": jobs.worker_started,
        }
    )


def test_legacy_or_absent_worker_is_interrupted():
    assert not jobs.worker_alive({})
    assert not jobs.worker_alive({"worker_pid": 0})


def test_remote_worker_is_not_incorrectly_declared_dead():
    assert jobs.worker_alive(
        {"worker_host": jobs.worker_host + "-remote", "worker_pid": 1}
    )
