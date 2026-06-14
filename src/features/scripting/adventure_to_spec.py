"""AdventureScript → VideoSpec — adaptateur PUR, à sens unique (LOT 1.5).

Ce module dérive, depuis un `AdventureScript`, une description déclarative
`VideoSpec` (l'IR de `src/videospec/models.py`). C'est une description DÉRIVÉE et
À SENS UNIQUE : VideoSpec n'est PAS encore le moteur de rendu (le compositor
MoviePy historique reste la source de vérité du pixel). Ce que cet adaptateur
apporte aujourd'hui :

- **Composabilité** : une vidéo = INTRO + N blocs séquence-choix + OUTRO, exprimée
  comme une donnée immuable (pas du code).
- **Une cible de rendu future**, validée segment par segment et asset par asset
  par le validateur d'intégrité référentielle de `VideoSpec` (les ids d'assets
  référencés par les segments doivent exister).

Méthodologie (alignée sur l'écosystème existant) :

- La LISTE D'ASSETS est dérivée de `plan_episode_assets(script, side)` — l'unique
  source de vérité de « quels assets un épisode produit ». Un asset VideoSpec par
  `PlannedAsset`, avec un id stable dérivé de `(round_index, beat)`, pour que les
  segments puissent les référencer et que le validateur passe.
- L'ORDRE DES SEGMENTS reproduit ce que le compositor rend par round
  (action → environment → face-cam → écran de choix → countdown → fatal →
  survival), encadré par l'INTRO (image de référence + nameplates) et l'OUTRO
  (épilogue narré, cf. `compose_narrated_segment`).

Module PUR : aucune I/O, aucun réseau, aucune DB. Le `theme` optionnel est
réinjecté dans la construction des prompts via `script_prompts` / `epilogue_beat`
(qui acceptent déjà un thème), de sorte que la DA apparaît dans les prompts émis.
"""

from typing import Dict, List, Optional

from ...studio.api.services.generation_plan import (
    PlannedAsset,
    plan_episode_assets,
)
from ...videospec.models import (
    Asset,
    Canvas,
    CountdownSegment,
    FileAsset,
    FootageSegment,
    HeadAnchor,
    ImageAsset,
    IntroSegment,
    NameplateSpec,
    NarrationSegment,
    Segment,
    SubtitleTrack,
    VideoAsset,
    VideoSpec,
    VoiceAsset,
)
from .adventure import AdventureScript
from .adventure_to_prompts import (
    Side,
    epilogue_beat,
    script_prompts,
)
from .themes import Theme

# Ids des SFX statiques (fichiers déjà sur disque, cf. builder.legacy_spec).
_TICK_ID = "sfx_tick"
_BEEP_ID = "sfx_beep"


def _asset_id(round_index: Optional[int], beat: str) -> str:
    """Id stable dérivé de (round_index, beat).

    Episode-level (round_index None) → `ep_<beat>` ; sinon `r<i>_<beat>`. Le beat
    peut contenir un point (« action.frame ») — conservé tel quel, ce qui garde
    l'id lisible et bijectif avec le `PlannedAsset` d'origine.
    """
    prefix = "ep" if round_index is None else f"r{round_index}"
    return f"{prefix}_{beat}"


def _themed_prompts(
    script: AdventureScript, side: Side, theme: Optional[Theme]
) -> Dict[str, str]:
    """Table (round_index, beat) -> prompt, reconstruite SOUS le `theme`.

    `plan_episode_assets` n'accepte pas de thème (il émet la DA par défaut). Pour
    threader le thème dans les prompts émis, on reconstruit ici les mêmes prompts
    via `script_prompts(..., theme)` / `epilogue_beat(..., theme)` (qui acceptent
    déjà un thème) et on les indexe par la MÊME clé `(round_index, beat)` que les
    PlannedAssets. Clé sous forme de chaîne « <ri>:<beat> » (ri = "None" pour les
    assets épisode), pour appliquer le bon prompt à chaque asset image/vidéo.
    """
    out: Dict[str, str] = {}
    if theme is None:
        return out

    for i, rp in enumerate(script_prompts(script, side, theme)):
        for beat_name, vb in (
            ("action", rp.action),
            ("environment", rp.environment),
            ("character", rp.character),
            ("fatal", rp.fatal),
            ("survival", rp.survival),
        ):
            out[f"{i}:{beat_name}.frame"] = vb.frame
            out[f"{i}:{beat_name}.motion"] = vb.motion
        for ci, choice_img in enumerate(rp.choice_images):
            out[f"{i}:choice.{ci}"] = choice_img

    epi = epilogue_beat(script, side, theme)
    out["None:epilogue.frame"] = epi.frame
    out["None:epilogue.motion"] = epi.motion
    return out


def _build_assets(
    planned: List[PlannedAsset],
    themed: Dict[str, str],
) -> tuple[List[Asset], Dict[str, str]]:
    """Convertit chaque PlannedAsset en un asset VideoSpec typé.

    `themed` (peut être vide) surcharge les prompts image/vidéo pour appliquer la
    DA du thème ; sinon on garde le prompt du PlannedAsset (DA par défaut).

    Retourne (assets, frame_id_par_base_beat) où la table permet à un VideoAsset
    (« X.motion ») de référencer l'image de sa première frame (« X.frame »), qui
    porte le même (round_index, base_beat) — exactement le pairing produit par
    `generation_plan._video_pair`.
    """
    # Map (round_index, base_beat) -> id de l'asset image « .frame ».
    frame_ids: Dict[str, str] = {}
    for p in planned:
        if p.kind == "image" and p.beat.endswith(".frame"):
            base = p.beat[: -len(".frame")]
            frame_ids[f"{p.round_index}:{base}"] = _asset_id(p.round_index, p.beat)

    assets: List[Asset] = []
    for p in planned:
        aid = _asset_id(p.round_index, p.beat)
        key = f"{p.round_index}:{p.beat}"
        if p.kind == "image":
            prompt = themed.get(key, p.image_prompt or "")
            assets.append(ImageAsset(id=aid, prompt=prompt))
        elif p.kind == "video":
            # « X.motion » : l'image source est le « X.frame » du même round/beat.
            base = p.beat[: -len(".motion")] if p.beat.endswith(".motion") else p.beat
            image_ref = frame_ids.get(
                f"{p.round_index}:{base}", _asset_id(p.round_index, f"{base}.frame")
            )
            prompt = themed.get(key, p.motion_prompt or "")
            assets.append(
                VideoAsset(
                    id=aid,
                    prompt=prompt,
                    image=image_ref,
                )
            )
        else:  # audio
            assets.append(VoiceAsset(id=aid, text=p.text or ""))
    return assets, frame_ids


def adventure_to_spec(
    script: AdventureScript,
    theme: Theme | None = None,
    side: Side = "left",
) -> VideoSpec:
    """Dérive un `VideoSpec` déclaratif depuis un `AdventureScript`.

    Émet, dans l'ordre : un IntroSegment, puis pour chaque round le bloc
    séquence-choix (action / environment / face-cam / écran de choix / countdown /
    fatal / survival), puis l'OUTRO (épilogue narré). Tous les assets proviennent
    de `plan_episode_assets`, garantissant des ids/beats cohérents avec ce que le
    générateur produit réellement.
    """
    planned = plan_episode_assets(script, side)
    themed = _themed_prompts(script, side, theme)
    assets, _frame_ids = _build_assets(planned, themed)

    # SFX statiques pour le countdown (mêmes fichiers que builder.legacy_spec).
    assets.append(FileAsset(id=_TICK_ID, path="assets/tick.wav"))
    assets.append(FileAsset(id=_BEEP_ID, path="assets/final.wav"))

    # Nameplates des deux persos (ancrés sur les têtes détectées au resolve),
    # comme builder.legacy_spec. Réutilisés sur intro + footage de chaque round.
    nameplates = (
        NameplateSpec(text=script.char_left_name, placement=HeadAnchor(side="left")),
        NameplateSpec(text=script.char_right_name, placement=HeadAnchor(side="right")),
    )

    segments: List[Segment] = []

    # 1) INTRO — image de référence perso (épisode) + nameplates, transition
    #    eye-open par défaut (cf. builder.legacy_spec / IntroSegment).
    intro_bg = _asset_id(None, "char_reference")
    segments.append(IntroSegment(background=intro_bg, nameplates=nameplates))

    # 2) N blocs séquence-choix — un par round.
    n_rounds = len(script.rounds)
    for i in range(n_rounds):
        action_motion = _asset_id(i, "action.motion")
        action_frame = _asset_id(i, "action.frame")
        env_motion = _asset_id(i, "environment.motion")
        env_frame = _asset_id(i, "environment.frame")
        char_motion = _asset_id(i, "character.motion")
        choice0 = _asset_id(i, "choice.0")
        fatal_frame = _asset_id(i, "fatal.frame")
        survival_frame = _asset_id(i, "survival.frame")

        # -- action : la vidéo (footage) + sa narration (image de frame zoomée).
        segments.append(
            FootageSegment(
                video=action_motion,
                subtitles=SubtitleTrack(source=_asset_id(i, "action.narration")),
                nameplates=nameplates,
            )
        )
        segments.append(
            NarrationSegment(
                background=action_frame,
                audio=_asset_id(i, "action.narration"),
                subtitles=SubtitleTrack(source=_asset_id(i, "action.narration")),
            )
        )

        # -- environment : footage + narration.
        segments.append(
            FootageSegment(video=env_motion, nameplates=nameplates)
        )
        segments.append(
            NarrationSegment(
                background=env_frame,
                audio=_asset_id(i, "environment.narration"),
                subtitles=SubtitleTrack(
                    source=_asset_id(i, "environment.narration")
                ),
            )
        )

        # -- face-cam (perso) : footage seul (voix native dans la vidéo, pas de
        #    piste TTS séparée — cf. generation_plan._plan_audio).
        segments.append(
            FootageSegment(video=char_motion, nameplates=nameplates)
        )

        # -- écran de choix : narration énonçant les deux options.
        #    APPROXIMATION : NarrationSegment n'a qu'UN `background` ; l'IR n'a pas
        #    de segment multi-image. On prend choice.0 comme fond et on s'appuie
        #    sur l'audio `choice.narration` qui énonce les DEUX choix. choice.1
        #    reste un asset déclaré (donc résolu/généré) mais n'est pas porté par
        #    un champ de segment dédié faute de type adéquat dans models.py.
        segments.append(
            NarrationSegment(
                background=choice0,
                audio=_asset_id(i, "choice.narration"),
                subtitles=SubtitleTrack(source=_asset_id(i, "choice.narration")),
            )
        )

        # -- countdown 3-2-1 (timer + jauge + SFX), fond = écran de choix.
        segments.append(
            CountdownSegment(
                background=choice0,
                tick_sound=_TICK_ID,
                end_sound=_BEEP_ID,
            )
        )

        # -- issues : fatal puis survival, narrées sur leur frame respective.
        segments.append(
            NarrationSegment(
                background=fatal_frame,
                audio=_asset_id(i, "fatal.narration"),
                subtitles=SubtitleTrack(source=_asset_id(i, "fatal.narration")),
            )
        )
        segments.append(
            NarrationSegment(
                background=survival_frame,
                audio=_asset_id(i, "survival.narration"),
                subtitles=SubtitleTrack(
                    source=_asset_id(i, "survival.narration")
                ),
            )
        )

    # 3) OUTRO — épilogue narré (cf. compose_narrated_segment) : la frame de
    #    l'épilogue (l'AUTRE perso) zoomée sous la voix narrateur.
    segments.append(
        NarrationSegment(
            background=_asset_id(None, "epilogue.frame"),
            audio=_asset_id(None, "epilogue.narration"),
            subtitles=SubtitleTrack(source=_asset_id(None, "epilogue.narration")),
        )
    )

    return VideoSpec(
        canvas=Canvas(),
        assets=tuple(assets),
        segments=tuple(segments),
    )
