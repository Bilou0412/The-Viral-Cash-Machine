"""Fake adventure decomposer — offline, deterministic, no network.

Renvoie un `AdventureScript` codé en dur, complet et valide (thème grotte / mine
hantée). Indispensable pour les tests et le développement quand la clé OpenAI
n'est pas disponible. Respecte les règles d'or : visuels EN, dialogues FR courts,
voix distinctives, aucun texte demandé à l'image.
"""

from .adventure import AdventureScript, Choice, Round, VoiceProfile


def _round(
    action_desc: str,
    action_narration_fr: str,
    environment_desc: str,
    danger_desc: str,
    environment_narration_fr: str,
    character_line_fr: str,
    character_delivery: str,
    choice_fatal: Choice,
    choice_safe: Choice,
    choice_narration_fr: str,
    fatal_kill_desc: str,
    fatal_pov_reaction: str,
    fatal_narration_fr: str,
    survival_outcome_desc: str,
    survival_narration_fr: str,
) -> Round:
    return Round(
        action_desc=action_desc,
        action_narration_fr=action_narration_fr,
        environment_desc=environment_desc,
        danger_desc=danger_desc,
        environment_narration_fr=environment_narration_fr,
        character_line_fr=character_line_fr,
        character_delivery=character_delivery,
        choices=(choice_fatal, choice_safe),
        choice_narration_fr=choice_narration_fr,
        fatal_kill_desc=fatal_kill_desc,
        fatal_pov_reaction=fatal_pov_reaction,
        fatal_narration_fr=fatal_narration_fr,
        survival_outcome_desc=survival_outcome_desc,
        survival_narration_fr=survival_narration_fr,
    )


class FakeAdventureDecomposer:
    """Deterministic offline AdventureDecomposer for tests and local dev."""

    def decompose_adventure(
        self,
        prompt: str,
        char_left_name: str = "Étienne",
        char_right_name: str = "Marc",
    ) -> AdventureScript:
        """Return a fixed, valid 3-round cave-horror adventure script.

        The user prompt and names are accepted for interface compatibility;
        the names are injected, the prompt is ignored (no network call).
        """
        round1 = _round(
            action_desc="walks deeper into a collapsed mine shaft",
            action_narration_fr="Il s'enfonce dans la galerie effondrée, lampe tremblante.",
            environment_desc="a flooded mine tunnel of weathered timber and black water",
            danger_desc="rotten support beams sagging under tons of wet rock",
            environment_narration_fr="Au-dessus de lui, le plafond gémit déjà.",
            character_line_fr="Le sol cède. Je passe par où ?",
            character_delivery="whispering",
            choice_fatal=Choice(
                label_fr="La passerelle de bois",
                image_desc="a frail wooden plank bridge over a dark flooded pit",
                is_fatal=True,
            ),
            choice_safe=Choice(
                label_fr="Le tunnel inondé",
                image_desc="a low water-filled side tunnel with a faint draft",
                is_fatal=False,
            ),
            choice_narration_fr="La passerelle de bois, ou le tunnel inondé ?",
            fatal_kill_desc="the rotten planks snap and the dark water swallows everything",
            fatal_pov_reaction="you grab at splinters as the cold pulls you under",
            fatal_narration_fr="Si tu as choisi la passerelle, le bois cède sous toi.",
            survival_outcome_desc="wades through the icy tunnel and reaches dry stone",
            survival_narration_fr="Le tunnel inondé tient bon. Tu respires encore.",
        )
        round2 = _round(
            action_desc="climbs a rusted ladder toward a faint glow",
            action_narration_fr="Une lueur pâle l'attire vers le haut.",
            environment_desc="a vast cavern hung with razor-sharp mineral formations",
            danger_desc="loose stalactites trembling far above the path",
            environment_narration_fr="Chaque pas fait pleuvoir des éclats de pierre.",
            character_line_fr="Ça bouge au plafond. On court ?",
            character_delivery="murmuring",
            choice_fatal=Choice(
                label_fr="Courir sous les pointes",
                image_desc="a sprint beneath a ceiling bristling with hanging stone spikes",
                is_fatal=True,
            ),
            choice_safe=Choice(
                label_fr="Longer la paroi",
                image_desc="a slow crawl along a sheltered cavern wall",
                is_fatal=False,
            ),
            choice_narration_fr="Courir sous les pointes, ou longer la paroi ?",
            fatal_kill_desc="the ceiling releases its stone spikes in a single roar",
            fatal_pov_reaction="you flinch upward a half-second too late",
            fatal_narration_fr="Si tu as choisi de courir, la pierre tombe sur toi.",
            survival_outcome_desc="presses flat to the wall as debris crashes past",
            survival_narration_fr="Contre la paroi, tu laisses passer l'avalanche.",
        )
        round3 = _round(
            action_desc="crosses a narrow ledge above an unseen drop",
            action_narration_fr="La sortie est proche, mais le vide aussi.",
            environment_desc="a fractured stone bridge over a bottomless black chasm",
            danger_desc="hairline cracks spreading across the load-bearing slab",
            environment_narration_fr="Le pont se fend dans un craquement sourd.",
            character_line_fr="Le pont se fissure. Vite ou doucement ?",
            character_delivery="hissing",
            choice_fatal=Choice(
                label_fr="Bondir d'un coup",
                image_desc="a desperate leap onto a cracked stone slab over a void",
                is_fatal=True,
            ),
            choice_safe=Choice(
                label_fr="Avancer pas à pas",
                image_desc="careful weight-spread footsteps across thin fractured stone",
                is_fatal=False,
            ),
            choice_narration_fr="Bondir d'un coup, ou avancer pas à pas ?",
            fatal_kill_desc="the slab shatters the instant your weight lands",
            fatal_pov_reaction="you reach for the edge as the chasm rushes up",
            fatal_narration_fr="Si tu as choisi de bondir, la dalle explose sous toi.",
            survival_outcome_desc="reaches the far ledge as the bridge collapses behind",
            survival_narration_fr="Pas à pas, tu atteins l'autre rive. Tu es sorti.",
        )

        return AdventureScript(
            char_left_name=char_left_name,
            char_right_name=char_right_name,
            char_left_desc=(
                "a gaunt pale man in a soaked miner's jacket, hollow eyes, "
                "ash-streaked face"
            ),
            char_right_desc=(
                "a wiry man with a weathered scarred face and a cracked helmet lamp"
            ),
            char_left_voice=VoiceProfile(
                description=(
                    "low breathy male voice, slow and trembling, frequent dry swallows"
                )
            ),
            char_right_voice=VoiceProfile(
                description=(
                    "tense raspy male voice, fast clipped delivery, edge of panic"
                )
            ),
            transition_narration_fr=(
                f"Si tu as choisi {char_left_name}, l'aventure commence dans le noir."
            ),
            rounds=(round1, round2, round3),
            epilogue_other_desc=(
                "the other character standing alone at the mine entrance, fading into mist"
            ),
            epilogue_narration_fr=(
                f"Si tu avais choisi {char_right_name}, ton histoire aurait été tout autre."
            ),
        )
