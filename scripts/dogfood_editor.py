"""Harnais dogfood du rail ÉDITEUR (ClipBrick) — idée → assets réels (Replicate).

But (ROADMAP S1) : lancer la **vraie boucle** hors du serveur web, sur un épisode
minimal (1 scène, 2 plans), pour trouver/corriger ce qui casse hors mock (slugs
Replicate, schéma d'input, i2v env→plan, coûts). On s'arrête aux **assets générés**
(photo d'environnement + plans vidéo i2v + audio) ; le MP4 final (Remotion) est
tenté seulement avec `--render`.

⚠️ Dérogation assumée : ce harnais DEV lit les clés depuis l'ENVIRONNEMENT
(`OPENAI_API_KEY`, `REPLICATE_API_TOKEN`) — le serveur FastAPI, lui, utilise le
store par-utilisateur chiffré (`VCM_SECRET_KEY`). Ne pas utiliser ce script en prod.

Usage :
    export OPENAI_API_KEY=…  REPLICATE_API_TOKEN=…  VCM_OUTPUT_DIR=./out
    python scripts/dogfood_editor.py --check          # préflight, ZÉRO dépense
    python scripts/dogfood_editor.py "une idée courte" # génère 1 scène / 2 plans
    python scripts/dogfood_editor.py "…" --render      # + MP4 Remotion (best-effort)
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Rendre le paquet `src` importable quand on lance `python scripts/dogfood_editor.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MAX_SHOTS = 2  # « 1 scène, 2 plans » — pour limiter le coût du 1er run.


def _install_proxy_shim() -> None:
    """Sandbox-only : force les SDK (httpx) à passer par le proxy d'egress.

    Dans l'environnement Claude Code web, l'accès sortant passe par un proxy
    (`HTTPS_PROXY`) mais les SDK replicate/openai tapent en DIRECT et se font
    bloquer (403 « Host not in allowlist »). On patche `httpx.Client` pour
    défaut-er `proxy`/`verify` vers le proxy + son CA. **No-op** hors sandbox
    (pas de `HTTPS_PROXY`) → aucun effet en prod / sur ta machine.
    """
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not proxy:
        return
    ca = os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt"
    verify: object = ca if os.path.exists(ca) else True
    try:
        import httpx
    except ImportError:
        return
    for cls in (httpx.Client, httpx.AsyncClient):
        orig = cls.__init__

        def patched(self: object, *a: object, __orig: object = orig, **kw: object) -> None:
            kw.setdefault("proxy", proxy)
            kw.setdefault("verify", verify)
            kw.setdefault("trust_env", True)
            __orig(self, *a, **kw)  # type: ignore[operator]

        cls.__init__ = patched  # type: ignore[method-assign]


# -- préflight (testable, client injecté) -------------------------------------

@dataclass
class CheckRow:
    """Une ligne du préflight : un contrôle, son verdict, un détail."""

    label: str
    ok: bool
    detail: str = ""


def check_models(models_get: Callable[[str], Any], slugs: tuple[str, ...]) -> list[CheckRow]:
    """Vérifie chaque slug via un `models.get(slug)` injecté (Replicate en réel).

    `models_get` lève si le slug n'existe pas (404) → ligne rouge. Aucune génération,
    donc **zéro dépense**. Injecté pour être testable hors réseau.
    """
    rows: list[CheckRow] = []
    for slug in slugs:
        try:
            models_get(slug)
            rows.append(CheckRow(f"modèle {slug}", True, "trouvé"))
        except Exception as e:  # 404 / auth / réseau
            rows.append(CheckRow(f"modèle {slug}", False, f"introuvable ({e})"))
    return rows


def _replicate_models_get(token: str) -> Callable[[str], Any]:
    from replicate.client import Client

    client = Client(api_token=token)
    return client.models.get


def preflight() -> list[CheckRow]:
    """Assemble toutes les vérifications sans rien générer."""
    from src.features.assets.models import ALL_MODELS

    rows: list[CheckRow] = []
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    replicate_token = os.environ.get("REPLICATE_API_TOKEN", "")
    rows.append(CheckRow("clé OPENAI_API_KEY", bool(openai_key),
                         "présente" if openai_key else "absente → scènes de démo (Fake)"))
    rows.append(CheckRow("clé REPLICATE_API_TOKEN", bool(replicate_token),
                         "présente" if replicate_token else "absente → pas de génération réelle"))

    if replicate_token:
        rows.extend(check_models(_replicate_models_get(replicate_token), ALL_MODELS))
    else:
        rows.append(CheckRow("slugs Replicate", False, "non vérifiés (pas de token)"))

    # Étape render (best-effort) : Node + Chromium + bundle Remotion.
    rows.append(CheckRow("node (render)", shutil.which("node") is not None,
                         shutil.which("node") or "absent"))
    chromium = shutil.which("chromium") or os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    rows.append(CheckRow("chromium (render)", bool(chromium), chromium or "absent"))
    rows.append(CheckRow("render/dist/cli.js", os.path.exists("render/dist/cli.js"),
                         "présent" if os.path.exists("render/dist/cli.js") else "à builder (npm run build dans render/)"))
    return rows


def _print_rows(rows: list[CheckRow]) -> None:
    for r in rows:
        mark = "✅" if r.ok else "❌"
        print(f"  {mark} {r.label:<28} {r.detail}")


# -- run réel (assets) --------------------------------------------------------

def run_dogfood(idea: str, *, render: bool) -> int:
    """Idée → plan (1 scène) → doc (≤2 plans) → génération réelle → assets sur disque."""
    # Sorties/DB user-writable par défaut — AVANT les imports (paths/engine lisent
    # ces variables à l'import). Posé au run seulement (import du module = sans effet).
    os.environ.setdefault("VCM_OUTPUT_DIR", "./out")
    os.environ.setdefault("VCM_STUDIO_DB", "sqlite:///dogfood.db")

    from sqlmodel import Session

    from src.features.scenes.scene_plan_to_document import scene_plan_to_document
    from src.studio.api.services.editor_generation import EditorGenerationService
    from src.studio.api.services.scenes import decomposer_source, generate_video_plan
    from src.studio.db.engine import get_engine, init_db
    from src.studio.db.repositories import (
        AssetRepo,
        EditorDocRepo,
        EpisodeRepo,
        ProjectRepo,
    )

    openai_key = os.environ.get("OPENAI_API_KEY") or None
    replicate_token = os.environ.get("REPLICATE_API_TOKEN") or None
    if not replicate_token:
        print("✗ REPLICATE_API_TOKEN absent — impossible de générer en réel "
              "(lance `--check`).", file=sys.stderr)
        return 2

    src = decomposer_source(openai_key)
    print(f"[plan] décrypteur = {src} — « {idea} »", flush=True)
    plan = generate_video_plan(idea, n_scenes=1, openai_key=openai_key)
    if plan.scenes:
        plan.scenes[0].shots = plan.scenes[0].shots[:MAX_SHOTS]  # cap coût
    n_shots = len(plan.scenes[0].shots) if plan.scenes else 0
    print(f"[plan] {len(plan.scenes)} scène(s), {n_shots} plan(s)", flush=True)

    doc = scene_plan_to_document(plan)
    engine = get_engine()
    init_db(engine)
    with Session(engine) as s:
        pid = ProjectRepo(s).create(name="dogfood").id
        assert pid is not None
        eid = EpisodeRepo(s).create(project_id=pid, title="Dogfood", draft_mode=True).id
        assert eid is not None
        doc_id = EditorDocRepo(s).create(pid, "Dogfood", doc.model_dump_json(), episode_id=eid).id
    assert doc_id is not None
    print(f"[setup] projet={pid} épisode={eid} doc={doc_id} (draft)", flush=True)

    print("[generate] génération réelle (image → motion i2v → voix)…", flush=True)
    EditorGenerationService(engine, replicate_token=replicate_token, draft=True).generate_document(doc_id)

    with Session(engine) as s:
        assets = AssetRepo(s).assets_by_document(doc_id)
    ok = [a for a in assets if a.status == "ready"]
    ko = [a for a in assets if a.status == "failed"]
    print(f"[assets] {len(ok)} prêt(s), {len(ko)} échec(s) :", flush=True)
    for a in assets:
        mark = "✅" if a.status == "ready" else "❌"
        print(f"  {mark} {a.beat:<22} {a.status:<10} {a.local_path or ''}", flush=True)
    if ko:
        print("→ des nœuds ont échoué : remonte-moi les erreurs (slug 404 ? schéma "
              "d'input ? ref i2v ?) et je corrige.", flush=True)

    if render:
        print("[render] tentative MP4 Remotion (Node + Chromium + render/dist)…", flush=True)
        try:
            from src.studio.api.services.remotion_render import render_document

            render_document(engine, doc_id)
            print("[render] terminé — cf. final_video.mp4 dans le dossier du doc.", flush=True)
        except Exception as e:
            print(f"[render] ✗ échec (attendu si Node/Chromium/render absent) : {e}", flush=True)

    return 1 if ko else 0


# -- aperçu du matériel texte (dry-run, ZÉRO génération) ----------------------

def preview_text(idea: str) -> int:
    """Idée → descripteur 3 niveaux RÉSOLU + les 3 prompts compilés, par plan.

    Aucune génération (ni image ni vidéo) : la boucle pour tester/enrichir le
    matériel texte. Fake sans clé OpenAI (gratuit), OpenAI si clé (quelques centimes).
    """
    from src.editor.compile_shot import (
        compile_image_prompt,
        compile_motion_prompt,
        looks_french,
        resolve_shot,
    )
    from src.editor.document import ClipBrick, Scene
    from src.features.scenes import scene_plan_to_document
    from src.studio.api.services.scenes import decomposer_source, generate_video_plan

    openai_key = os.environ.get("OPENAI_API_KEY") or None
    print(f"[aperçu] décrypteur = {decomposer_source(openai_key)} — « {idea} »\n")
    plan = generate_video_plan(idea, n_scenes=1, openai_key=openai_key)
    doc = scene_plan_to_document(plan)

    m = doc.meta
    style = f" | style: {m.style_rendu}" if m.style_rendu.strip() else ""
    reso = f" {m.resolution}" if m.resolution.strip() else ""
    print(f"■ VIDÉO — {doc.title} | {m.ratio}{reso} {m.fps}fps{style}")
    print(f"  intention: {doc.intention_globale.genre} · {doc.intention_globale.ton}")
    print(f"  bibles: {len(doc.location_bible)} décor(s), {len(doc.bible)} perso(s)\n")

    scene_of = {sid: sc for sc in doc.scenes for sid in (*sc.shot_ids, sc.environment_photo_ref)}
    for sc in doc.scenes:
        loc = next((locn.lieu for locn in doc.location_bible if locn.ref == sc.location_ref), "?")
        print(f"● SCÈNE {sc.id} — {sc.title} | décor: {loc} | {sc.moment_jour} {sc.meteo} | mood: {sc.mood}")
    print()
    for brick in doc.bricks:
        if not (isinstance(brick, ClipBrick) and brick.shot is not None):
            continue
        r = resolve_shot(doc, scene_of.get(brick.id, Scene(id="_none")), brick.shot)
        print(f"  ▸ PLAN {brick.id} | cadre: {brick.shot.cadre.taille_plan or '—'} | "
              f"caméra: {brick.shot.camera.type or '—'}")
        img = compile_image_prompt(r)
        mot = compile_motion_prompt(r)
        fr = " ⚠FR" if looks_french(img) else ""
        print(f"      IMAGE  ({len(img.split()):>2}w{fr}): {img or '(vide)'}")
        print(f"      MOTION ({len(mot.split()):>2}w): {mot or '(vide)'}")
        narr = next((c.params.get('text', '') for c in brick.children), '')
        print(f"      VOIX   : {narr or '(aucune)'}\n")
    return 0


# -- CLI ----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dogfood du rail éditeur (assets réels).")
    parser.add_argument("idea", nargs="?", default="", help="l'idée de la vidéo")
    parser.add_argument("--check", action="store_true", help="préflight seul (zéro dépense)")
    parser.add_argument("--text", action="store_true", help="aperçu du matériel texte (zéro génération)")
    parser.add_argument("--render", action="store_true", help="tente aussi le MP4 Remotion")
    args = parser.parse_args(argv)

    _install_proxy_shim()  # sandbox-only : SDK via proxy (no-op hors Claude Code web)

    if args.check:
        print("Préflight dogfood (aucune génération) :")
        rows = preflight()
        _print_rows(rows)
        return 0 if all(r.ok for r in rows) else 1

    if not args.idea:
        parser.error("donne une idée, ou utilise --check")
    if args.text:
        return preview_text(args.idea)
    return run_dogfood(args.idea, render=args.render)


if __name__ == "__main__":
    raise SystemExit(main())
