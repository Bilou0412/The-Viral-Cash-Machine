"""RealAssetResolver — orchestration testée EN OFFLINE.

On n'a ni token ni réseau en CI : on injecte un faux provider (URLs bidon), on
monkeypatche le téléchargeur (écrit un fichier vide), et on vérifie que le
resolver enchaîne correctement réf-perso → images → voix → vidéos → transcripts
→ têtes, sans aucune référence orpheline. Le `produce_cli._build_spec` est aussi
vérifié (câblage CLI + thème), script « fake », sans réseau.
"""

import argparse
import os

import pytest

pytest.importorskip("pydantic")

from src.videospec.resolve_real import RealAssetResolver


class _FakeProvider:
    def generate_image(self, prompt, size, aspect_ratio, image_input=None):
        return "http://fake/img"

    def synthesize_voice(self, text, voice_id, model=None):
        return "http://fake/voice"

    def animate_video(
        self, prompt, image_url, duration, aspect_ratio, resolution,
        audio_url=None, draft=False,
    ):
        return "http://fake/vid"

    def run_model(self, model_ref, params):
        return ["http://fake/x"]


class _FakeCues:
    def to_list(self):
        return [{"text": "mot", "start": 0.0, "end": 0.1}]


class _FakeTranscriber:
    def transcribe(self, path):
        return _FakeCues()


def _fake_heads():
    from src.features.compositing.heads import HeadLayout

    class _FakeHeads:
        def detect(self, image_path, instance_dir):
            return HeadLayout(left=(0.2, 0.3), right=(0.8, 0.3))

    return _FakeHeads()


def _adventure_spec(n_rounds):
    from src.features.scripting.adventure_to_spec import adventure_to_spec
    from src.features.scripting.fake_adventure_decomposer import (
        FakeAdventureDecomposer,
    )

    script = FakeAdventureDecomposer().decompose_adventure("x", n_rounds=n_rounds)
    return adventure_to_spec(script)


def test_real_resolver_orchestration_offline(tmp_path, monkeypatch):
    import src.infra.download as dl

    def fake_dl(url, folder, filename):
        os.makedirs(folder, exist_ok=True)
        p = os.path.join(folder, filename)
        with open(p, "wb") as f:
            f.write(b"x")
        return p

    monkeypatch.setattr(dl, "download_file", fake_dl)

    spec = _adventure_spec(n_rounds=1)
    resolver = RealAssetResolver(
        provider=_FakeProvider(),
        transcriber=_FakeTranscriber(),
        head_detector=_fake_heads(),
    )
    resolved = resolver.resolve(spec, str(tmp_path))

    # Toute référence d'asset est résolue en un chemin local.
    for a in spec.assets:
        assert a.id in resolved.paths, f"asset non résolu : {a.id}"

    # Têtes détectées issues du faux détecteur.
    assert resolved.heads["left"] == (0.2, 0.3)

    # Chaque source de sous-titres a un transcript.
    for seg in spec.segments:
        src = getattr(getattr(seg, "subtitles", None), "source", None)
        if src is not None:
            assert src in resolved.transcripts


def test_cli_builds_valid_spec_fake_script():
    from src.videospec.produce_cli import _build_spec

    args = argparse.Namespace(
        script="fake",
        prompt="une nuit dans un dirigeable abandonné",
        theme="horror",
        side="left",
        left="Étienne",
        right="Marc",
        n_rounds=2,
        model=None,
    )
    spec = _build_spec(args)
    assert len(spec.segments) > 0
    assert len(spec.assets) > 0
