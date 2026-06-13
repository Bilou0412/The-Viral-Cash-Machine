"""Turn an AdventureScript into a concrete, ordered list of asset jobs.

PURE module (no I/O, no DB, no network). It is the single source of truth for
"what assets does an episode need", shared by:
  - `estimate_cost(...)` (pre-flight HUD), and
  - the background generator (which executes the same plan via an AssetProvider).

Methodology = image-first: every video beat is an IMAGE (first frame) THEN an
image→video (motion). Choices are plain images. We follow ONE path (default the
left character / non-fatal route) and the epilogue shows the OTHER character —
exactly the contract of `adventure_to_prompts`.
"""

from dataclasses import dataclass
from typing import List, Literal, Optional

from ....features.scripting.adventure import AdventureScript
from ....features.scripting.adventure_to_prompts import (
    Side,
    epilogue_beat,
    script_prompts,
)
from . import pricing

AssetKind = Literal["image", "video", "audio"]


@dataclass(frozen=True)
class PlannedAsset:
    """One asset to generate. Maps 1:1 onto a DB `Asset` row.

    `round_index` is None for episode-level assets (epilogue). `beat` names the
    slot (e.g. "action", "environment.frame", "choice.0", "narration",
    "character.voice", "epilogue.motion"). `image_prompt` is the seedream prompt;
    for video assets it is the first-frame source, and `motion_prompt` is the
    p-video prompt. For audio, `text` carries the spoken French.
    """

    round_index: Optional[int]
    beat: str
    kind: AssetKind
    image_prompt: Optional[str] = None
    motion_prompt: Optional[str] = None
    text: Optional[str] = None


def _video_pair(
    round_index: Optional[int], beat: str, frame: str, motion: str
) -> List[PlannedAsset]:
    """A video beat = its first-frame image THEN the image→video motion."""
    return [
        PlannedAsset(round_index, f"{beat}.frame", "image", image_prompt=frame),
        PlannedAsset(
            round_index,
            f"{beat}.motion",
            "video",
            image_prompt=frame,
            motion_prompt=motion,
        ),
    ]


def plan_episode_assets(
    script: AdventureScript, side: Side = "left"
) -> List[PlannedAsset]:
    """Full ordered asset plan for one episode along the followed `side`.

    Order follows the timeline: per round (action, environment, character,
    2 choice images, fatal, survival) then the epilogue, then the audio track
    (narration + the followed character's spoken lines).
    """
    assets: List[PlannedAsset] = []

    rounds = script_prompts(script, side)
    for i, rp in enumerate(rounds):
        for beat_name, beat in (
            ("action", rp.action),
            ("environment", rp.environment),
            ("character", rp.character),
            ("fatal", rp.fatal),
            ("survival", rp.survival),
        ):
            assets += _video_pair(i, beat_name, beat.frame, beat.motion)
        for ci, choice_img in enumerate(rp.choice_images):
            assets.append(
                PlannedAsset(i, f"choice.{ci}", "image", image_prompt=choice_img)
            )

    # Epilogue (the OTHER character) — one more video beat at episode level.
    epi = epilogue_beat(script, side)
    assets += _video_pair(None, "epilogue", epi.frame, epi.motion)

    # Audio: narrator track + the followed character's spoken lines.
    assets += _plan_audio(script, side)
    return assets


def _plan_audio(script: AdventureScript, side: Side) -> List[PlannedAsset]:
    """Narration (narrator voice) + character lines (followed character voice)."""
    assets: List[PlannedAsset] = []

    # Narrator: transition + per-round narrations + epilogue narration.
    narration_parts = [script.transition_narration_fr]
    for i, rnd in enumerate(script.rounds):
        narration_parts += [
            rnd.action_narration_fr,
            rnd.environment_narration_fr,
            rnd.choice_narration_fr,
            rnd.fatal_narration_fr,
            rnd.survival_narration_fr,
        ]
    narration_parts.append(script.epilogue_narration_fr)
    assets.append(
        PlannedAsset(
            None, "narration", "audio", text="\n".join(narration_parts)
        )
    )

    # Character: the spoken face-cam lines of the followed character, per round.
    for i, rnd in enumerate(script.rounds):
        assets.append(
            PlannedAsset(i, "character.voice", "audio", text=rnd.character_line_fr)
        )
    return assets


def estimate_cost(
    script: AdventureScript, side: Side = "left", draft: bool = False
) -> pricing.CostEstimate:
    """Pre-flight cost estimate for generating all of an episode's assets.

    Groups the plan into image / video / voice rate-card lines so the UI can show
    a per-model breakdown and a total before the user spends anything.
    """
    plan = plan_episode_assets(script, side)

    n_images = sum(1 for a in plan if a.kind == "image")
    video_seconds = sum(
        pricing.BEAT_VIDEO_SECONDS for a in plan if a.kind == "video"
    )
    voice_chars = sum(len(a.text or "") for a in plan if a.kind == "audio")

    lines = (
        pricing.image_cost(n_images),
        pricing.video_cost(video_seconds, draft=draft),
        pricing.voice_cost(voice_chars),
    )
    return pricing.CostEstimate(lines=lines)
