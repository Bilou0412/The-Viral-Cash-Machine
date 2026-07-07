"""Retry anti-throttle (429) du provider Replicate — offline, sans réseau.

Trouvaille du dogfood réel : les comptes à faible crédit (et tout pic de charge)
sont throttlés (429). Le provider doit patienter et réessayer plutôt qu'échouer.
"""

from __future__ import annotations

from typing import Any

import pytest

import src.features.assets.replicate_provider as rp
from src.features.assets.replicate_provider import (
    ReplicateAssetProvider,
    _is_rate_limited,
    _retry_after_seconds,
)

# -- helpers purs -------------------------------------------------------------

class _Throttle(Exception):
    status = 429

    def __str__(self) -> str:
        return "Request was throttled. Your rate limit resets in ~3s."


def test_is_rate_limited_detects_429_status_and_text():
    assert _is_rate_limited(_Throttle())
    assert _is_rate_limited(RuntimeError("status: 429 throttled"))
    assert not _is_rate_limited(RuntimeError("500 internal error"))


def test_retry_after_parses_reset_hint_else_default():
    assert _retry_after_seconds(_Throttle(), 10.0) == 4.0  # « ~3s » + 1 s de marge
    assert _retry_after_seconds(RuntimeError("boom"), 7.0) == 7.0


# -- boucle de retry (client factice, sleep neutralisé) -----------------------

class _Pred:
    def __init__(self) -> None:
        self.metrics = {"predict_time": 1.0}
        self.cost = 0.01
        self.output = ["https://fake.local/out.png"]

    def wait(self) -> None:
        pass


class _Preds:
    def __init__(self, fail_times: int) -> None:
        self.calls = 0
        self.fail_times = fail_times

    def create(self, model_ref: str, input: dict[str, Any]) -> _Pred:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise _Throttle()
        return _Pred()


class _Models:
    def __init__(self, preds: _Preds) -> None:
        self.predictions = preds


class _Client:
    def __init__(self, preds: _Preds) -> None:
        self.models = _Models(preds)

    def run(self, model_ref: str, input: dict[str, Any]) -> list[str]:
        return ["https://fake.local/fallback.png"]


class _Provider(ReplicateAssetProvider):
    def __init__(self, client: _Client) -> None:
        super().__init__()
        self._fake = client

    def _client(self) -> Any:
        return self._fake


def test_retry_on_429_then_succeeds(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(rp.time, "sleep", lambda s: slept.append(s))
    preds = _Preds(fail_times=2)  # 2 throttles puis succès
    res = _Provider(_Client(preds)).run_model_metered("m", {})
    assert res.urls == ["https://fake.local/out.png"]
    assert preds.calls == 3       # 2 retries + 1 succès
    assert len(slept) == 2        # a patienté 2 fois


def test_retry_exhausted_raises(monkeypatch):
    monkeypatch.setattr(rp.time, "sleep", lambda s: None)
    with pytest.raises(_Throttle):
        _Provider(_Client(_Preds(fail_times=99))).run_model_metered("m", {})


class _OtherErr(Exception):
    pass


class _PredsOther:
    def create(self, model_ref: str, input: dict[str, Any]) -> _Pred:
        raise _OtherErr("boom")


def test_non_429_error_falls_back_to_run():
    client = _Client(_Preds(fail_times=0))
    client.models = _Models(_PredsOther())  # type: ignore[assignment]
    res = _Provider(client).run_model_metered("m", {})
    assert res.urls == ["https://fake.local/fallback.png"]  # repli client.run
