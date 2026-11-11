"""Bucle de conciliación en segundo plano (Fase E)."""

from __future__ import annotations

import asyncio

import pytest

from tallerclaro.infrastructure.payment.reconciliation_worker import (
    PaymentReconciliationWorker,
)


class _Recorder:
    def __init__(self, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def execute(self) -> dict[str, int]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("database unavailable")
        return {}


def test_worker_runs_a_pass_and_stops_when_cancelled():
    recorder = _Recorder()

    async def scenario() -> None:
        worker = PaymentReconciliationWorker(recorder, interval_seconds=60)
        task = asyncio.create_task(worker.run())
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())

    assert recorder.calls == 1


def test_worker_survives_a_failing_pass():
    recorder = _Recorder(fail=True)

    async def scenario() -> None:
        worker = PaymentReconciliationWorker(recorder, interval_seconds=60)
        task = asyncio.create_task(worker.run())
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())

    assert recorder.calls == 1


def test_worker_rejects_a_non_positive_interval():
    with pytest.raises(ValueError):
        PaymentReconciliationWorker(_Recorder(), interval_seconds=0)
