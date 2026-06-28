"""Storage backends — offline (no network, no boto3 needed).

LocalStorage and FakeStorage are exercised directly; R2Storage is exercised with
an injected fake S3 client so its key derivation and call shape are covered
without boto3/moto.
"""

from __future__ import annotations

import os

from src.features.storage import set_storage
from src.features.storage.factory import get_storage
from src.features.storage.fakes import FakeStorage
from src.features.storage.local import LocalStorage
from src.features.storage.r2 import R2Storage, _key_for


def test_local_round_trip(tmp_path) -> None:
    st = LocalStorage()
    src = tmp_path / "in.bin"
    src.write_bytes(b"hello")
    ref = st.persist_file(str(src), str(tmp_path / "out"), "a.bin")
    assert os.path.isabs(ref) and ref.endswith("a.bin")
    assert st.exists(ref)
    assert st.materialize(ref) == ref            # identity for local
    assert not st.exists(str(tmp_path / "nope"))


def test_fake_round_trip(tmp_path) -> None:
    st = FakeStorage()
    src = tmp_path / "in.bin"
    src.write_bytes(b"data")
    ref = st.persist_file(str(src), "exports/p/episode_1", "v.mp4")
    assert ref == "p/episode_1/v.mp4"            # key, not a path
    assert st.exists(ref)
    mat = st.materialize(ref)
    assert open(mat, "rb").read() == b"data"


def test_factory_default_is_local() -> None:
    set_storage(None)                            # reset to env-configured
    try:
        assert isinstance(get_storage(), LocalStorage)
    finally:
        set_storage(None)


def test_key_derivation_under_output_base(monkeypatch) -> None:
    monkeypatch.setenv("VCM_OUTPUT_DIR", "exports")
    assert _key_for("exports/proj/episode_2", "x.png") == "proj/episode_2/x.png"


class _FakeS3:
    def __init__(self) -> None:
        self.uploaded: dict[str, str] = {}
    def upload_file(self, local: str, bucket: str, key: str) -> None:
        self.uploaded[key] = local
    def head_object(self, Bucket: str, Key: str):  # noqa: N803
        if Key in self.uploaded:
            return {"ContentLength": 10}
        raise RuntimeError("404")
    def download_file(self, Bucket: str, Key: str, dest: str) -> None:  # noqa: N803
        with open(dest, "wb") as f:
            f.write(b"obj")


def test_r2_uses_keys_and_client(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("VCM_OUTPUT_DIR", str(tmp_path))
    r2 = R2Storage(
        endpoint="https://acc.r2.cloudflarestorage.com",
        bucket="b",
        access_key="k",
        secret_key="s",
        public_base="https://cdn.example.com",
    )
    r2._client = _FakeS3()                       # bypass boto3
    src = tmp_path / "in.bin"
    src.write_bytes(b"x")
    folder = str(tmp_path / "proj" / "episode_1")
    ref = r2.persist_file(str(src), folder, "v.mp4")
    assert ref == "proj/episode_1/v.mp4"
    assert r2.exists(ref)
    assert not r2.exists("missing/key.mp4")
    mat = r2.materialize(ref)                     # downloads via fake client
    assert open(mat, "rb").read() == b"obj"
    resp = r2.serve(ref)                          # public base -> redirect
    assert resp.status_code == 307
    assert resp.headers["location"] == "https://cdn.example.com/proj/episode_1/v.mp4"
