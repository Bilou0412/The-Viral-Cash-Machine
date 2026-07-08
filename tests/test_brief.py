"""Lot Brief — le producteur (agent de dialogue) + fil brief→décrypteur (offline)."""

import pytest

pytest.importorskip("pydantic")

from src.features.brief import Brief, CrewAgentError, FakeProducerAgent
from src.features.brief.openai_producer_agent import OpenAIProducerAgent
from src.features.crew import CREW
from src.features.scenes.fake_scene_decomposer import FakeSceneDecomposer
from src.features.scenes.openai_scene_decomposer import OpenAISceneDecomposer


def test_roster_has_producteur_first_in_developpement():
    """Le producteur ouvre le casting (phase développement, kind 'brief')."""
    prod = next(r for r in CREW if r.key == "producteur")
    assert prod.phase == "developpement"
    assert prod.kind == "brief"
    assert CREW[0].key == "producteur"  # en amont du scénariste


# -- producteur FAKE : déterministe, l'humain garde la main -------------------

def test_fake_producer_completes_brief():
    b = FakeProducerAgent().draft_brief(idea="Un métro hanté la nuit, horreur")
    assert b.objectif and b.audience and b.plateforme == "tiktok"
    assert b.langue == "fr" and b.ton  # ton dérivé (heuristique horreur)


def test_fake_producer_respects_partial():
    """Les champs déjà décidés par l'humain priment sur la proposition."""
    partial = Brief(plateforme="reels", langue="en", audience="pros B2B")
    b = FakeProducerAgent().draft_brief(idea="un tuto", partial=partial)
    assert b.plateforme == "reels"
    assert b.langue == "en"
    assert b.audience == "pros B2B"
    assert b.objectif  # complété par l'agent (était vide)


def test_fake_producer_deterministic():
    a = FakeProducerAgent()
    assert a.draft_brief(idea="x").model_dump() == a.draft_brief(idea="x").model_dump()


# -- producteur OpenAI : client STUB (aucun réseau) ---------------------------

class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, content):
        self._content = content
        self.systems: list[str] = []

    def create(self, **kw):
        # Capture le prompt système pour vérifier le fil du Brief.
        for m in kw.get("messages", []):
            if m.get("role") == "system":
                self.systems.append(m["content"])
        return _Resp(self._content)


class _Chat:
    def __init__(self, content):
        self.completions = _Completions(content)


class _StubClient:
    def __init__(self, content):
        self.chat = _Chat(content)


def test_openai_producer_parses_brief():
    payload = (
        '{"objectif":"faire peur","audience":"ados","plateforme":"shorts",'
        '"duree_s":25,"budget_usd":2,"ton":"angoissant","langue":"fr","notes":""}'
    )
    b = OpenAIProducerAgent(_StubClient(payload), "gpt-x").draft_brief(idea="métro")
    assert b.objectif == "faire peur"
    assert b.plateforme == "shorts"
    assert b.duree_s == 25


def test_openai_producer_empty_raises():
    ag = OpenAIProducerAgent(_StubClient('{"objectif":""}'), "gpt-x")
    with pytest.raises(CrewAgentError):
        ag.draft_brief(idea="x")


# -- fil Brief → décrypteur ---------------------------------------------------

# Un seul payload sert les deux phases (extra='ignore' → chaque phase lit sa clé).
_SCENE_SHOT = (
    '{"scenes":[{"id":"s1","title":"T","environment_desc":"env","intention":"i"}],'
    '"shots":[{"id":"s1_sh1","kind":"video","visual_desc":"v","motion_desc":"m",'
    '"narration_fr":"n","duration_s":3}]}'
)


def test_decomposer_defaults_are_french_no_budget():
    """Défauts (pas de brief) : narration FRANÇAISE, pas de budget-temps imposé."""
    stub = _StubClient(_SCENE_SHOT)
    OpenAISceneDecomposer(stub, "gpt-x").decompose_video("idée", n_scenes=1)
    joined = "\n".join(stub.chat.completions.systems)
    assert "FRENCH" in joined
    assert "budget" not in joined.lower()  # aucune durée cible → pas de consigne budget


def test_decomposer_honors_brief_language_and_duration():
    """`language='en'` → libellés EN ; `target_duration_s>0` → budget-temps par scène."""
    stub = _StubClient(_SCENE_SHOT)
    OpenAISceneDecomposer(stub, "gpt-x").decompose_video(
        "idea", n_scenes=1, platform="reels", language="en", target_duration_s=30
    )
    systems = stub.chat.completions.systems
    macro, micro = systems[0], systems[1]
    assert "ENGLISH" in macro and "for Reels" in macro
    assert "ENGLISH" in micro  # narration EN
    assert "about 30s" in micro  # 30s / 1 scène


def test_fake_decomposer_ignores_brief_params():
    """Le Fake accepte les nouveaux kwargs et reste déterministe (golden scènes)."""
    dec = FakeSceneDecomposer()
    a = dec.decompose_video("x", n_scenes=2)
    b = dec.decompose_video("x", n_scenes=2, platform="reels", language="en", target_duration_s=99)
    assert a.model_dump() == b.model_dump()


# -- assembleur de contexte : le dossier de briefing par métier ---------------

def _sample_doc():
    from src.features.scenes import scene_plan_to_document

    plan = FakeSceneDecomposer().decompose_video("un métro hanté", n_scenes=2)
    return scene_plan_to_document(plan, title="Ma vidéo")


def test_assemble_context_always_carries_brief_and_refs():
    from src.studio.api.services.context import assemble_context

    brief = Brief(objectif="faire peur", plateforme="reels")
    ctx = assemble_context("scenariste", brief=brief, doc=None)
    assert ctx.brief.objectif == "faire peur"
    assert ctx.refs["title"] and ctx.refs["phase"] == "developpement"
    assert ctx.dossier == {}  # pas de document en amont


def test_assemble_context_unknown_role_raises():
    from src.studio.api.services.context import assemble_context

    with pytest.raises(KeyError):
        assemble_context("réalisateur_fantôme", brief=Brief())


def test_assemble_context_tools_by_role():
    """Chaque métier reçoit le manifeste des seuls kinds d'outils qu'il touche."""
    from src.studio.api.services.context import assemble_context

    doc = _sample_doc()
    expected = {
        "producteur": set(),
        "scenariste": set(),
        "directeur_artistique": {"image"},
        "chef_operateur": {"video"},
        "dialoguiste": set(),
        "tournage": {"image", "video", "voice"},
        "monteur": set(),
        "inge_son": {"voice"},
        "attache_presse": set(),
    }
    for role, kinds in expected.items():
        ctx = assemble_context(role, brief=Brief(), doc=doc)
        assert {t.kind for t in ctx.tools} == kinds, role
        # Le manifeste porte les modèles préférés quand il y a des outils.
        for tool in ctx.tools:
            assert tool.preferred_models and tool.fields


def test_assemble_context_dossier_slices():
    from src.studio.api.services.context import assemble_context

    doc = _sample_doc()
    da = assemble_context("directeur_artistique", brief=Brief(), doc=doc).dossier
    assert da["scenes"] and all("environment" in s for s in da["scenes"])
    son = assemble_context("inge_son", brief=Brief(), doc=doc).dossier
    # Les répliques du Fake décrypteur, porteuses de l'id de leur enfant audio.
    assert son["narration"] and all("id" in u and "text" in u for u in son["narration"])
    presse = assemble_context("attache_presse", brief=Brief(), doc=doc).dossier
    assert presse["title"] == "Ma vidéo" and "hook" in presse


def test_assemble_context_effects_only_for_assembly_roles():
    """Seuls les métiers qui ASSEMBLENT voient la palette d'effets de montage."""
    from src.studio.api.services.context import assemble_context

    # Le tournage (assemble) voit tous les effets ; un métier de contenu, aucun.
    tournage = assemble_context("tournage", brief=Brief())
    names = {e.name for e in tournage.effects}
    assert {"montage.timer", "montage.choice", "montage.zoom", "montage.nameplate"} <= names
    assert all(e.summary for e in tournage.effects)
    assert assemble_context("directeur_artistique", brief=Brief()).effects == []
    assert assemble_context("dialoguiste", brief=Brief()).effects == []


def test_catalog_lists_generative_and_montage_palettes():
    """Le catalogue = source unique de « ce qu'on peut assembler » (génératif + montage)."""
    from src.studio.api.services.catalog import build_catalog

    cat = build_catalog()
    assert {t.kind for t in cat.generative} == {"image", "video", "voice"}
    names = {e.name for e in cat.effects}
    # Les effets de l'intro-exemple sont dans la palette.
    assert {"montage.timer", "montage.choice", "montage.zoom", "montage.nameplate"} <= names
