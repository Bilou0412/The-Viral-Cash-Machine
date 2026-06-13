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
        char_left_desc: str = "",
        char_right_desc: str = "",
    ) -> AdventureScript:
        """Return a fixed, valid 3-round cave-horror adventure script.

        Offline/deterministic : le prompt est ignoré (pas de réseau). Les noms
        sont injectés ; si une description de perso est fournie, elle remplace
        l'apparence par défaut (pour tester le contrat « créateur décrit »).
        """
        round1 = _round(
            action_desc="descends deeper down the collapsed mine shaft, torch raised",
            action_narration_fr=(
                "Tu le suis dans le boyau effondré. L'air sent la rouille et "
                "l'eau croupie, et chaque planche craque sous vos pas."
            ),
            environment_desc="a flooded mine tunnel of weathered timber and black water",
            danger_desc="rotten support beams sagging under tons of dripping wet rock",
            environment_narration_fr=(
                "Devant toi, le plafond ploie déjà sous la roche, prêt à lâcher au "
                "moindre souffle. Le passage se sépare en deux."
            ),
            character_line_fr=(
                "Écoute-moi. Tu me suis sur la passerelle, ou tu files dans le "
                "tunnel d'eau. Décide vite, j'attends pas, et lui non plus."
            ),
            character_delivery="in a low urgent trembling whisper",
            choice_fatal=Choice(
                label_fr="La passerelle de bois",
                image_desc="a frail wooden plank bridge over a dark flooded pit",
                is_fatal=True,
            ),
            choice_safe=Choice(
                label_fr="Le tunnel inondé",
                image_desc="a low water-filled side tunnel with a faint cold draft",
                is_fatal=False,
            ),
            choice_narration_fr="La passerelle de bois, ou le tunnel inondé. Choisis.",
            fatal_kill_desc="spins as the rotten planks snap and the black water erupts upward",
            fatal_pov_reaction="we claw at splinters as the freezing dark drags us under",
            fatal_narration_fr=(
                "Si tu as choisi la passerelle, le bois cède d'un coup. L'eau noire "
                "se referme sur toi avant même que tu cries."
            ),
            survival_outcome_desc="wades through the icy side tunnel and hauls us onto dry stone",
            survival_narration_fr=(
                "Le tunnel inondé tient bon. L'eau te glace jusqu'aux os, mais tu "
                "respires encore. Pour l'instant."
            ),
        )
        round2 = _round(
            action_desc="climbs a groaning rusted ladder toward a pale glow",
            action_narration_fr=(
                "Tu grimpes derrière lui vers une lueur malade. Les barreaux "
                "rouillés plient, et le vide t'aspire dans le dos."
            ),
            environment_desc="a vast cavern hung with razor-sharp mineral formations",
            danger_desc="loose stalactites trembling far above the narrow path",
            environment_narration_fr=(
                "La caverne s'ouvre, hérissée de lames de pierre. Au-dessus de vos "
                "têtes, tout tremble et menace de tomber."
            ),
            character_line_fr=(
                "Ça bouge au plafond, tu entends ? Soit on court sous les pointes, "
                "soit on longe la paroi. Mais réfléchis pas trop, on n'a pas le temps."
            ),
            character_delivery="in a tense hushed murmur on the edge of panic",
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
            choice_narration_fr="Courir sous les pointes, ou longer la paroi. Vite.",
            fatal_kill_desc="throws an arm up as the ceiling unloads its stone spikes in one roar",
            fatal_pov_reaction="we flinch upward half a second too late",
            fatal_narration_fr=(
                "Si tu as choisi de courir, le plafond s'effondre. La pierre te "
                "cloue au sol dans un fracas, et le silence revient."
            ),
            survival_outcome_desc="presses us flat to the wall as the debris thunders past",
            survival_narration_fr=(
                "Collé à la paroi, tu laisses l'avalanche passer à un souffle de "
                "ton visage. Ton cœur cogne, mais tu es vivant."
            ),
        )
        round3 = _round(
            action_desc="edges onto a narrow ledge above an unseen drop",
            action_narration_fr=(
                "La sortie n'est plus loin. Mais le vide aussi. Tu avances derrière "
                "lui sur une corniche large comme une main."
            ),
            environment_desc="a fractured stone bridge over a bottomless black chasm",
            danger_desc="hairline cracks spreading fast across the load-bearing slab",
            environment_narration_fr=(
                "Un pont de pierre fendu enjambe le gouffre. Sous vos pieds, les "
                "fissures s'écartent dans un craquement sourd."
            ),
            character_line_fr=(
                "Le pont lâche, regarde. Tu bondis d'un coup avec moi, ou tu avances "
                "pas à pas. Mais décide maintenant, ou je décide pour toi."
            ),
            character_delivery="in a sharp pressing hiss",
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
            choice_narration_fr="Bondir d'un coup, ou avancer pas à pas. Choisis vite.",
            fatal_kill_desc="lands hard as the slab shatters the instant our weight hits it",
            fatal_pov_reaction="we reach for the crumbling edge as the chasm rushes up",
            fatal_narration_fr=(
                "Si tu as choisi de bondir, la dalle explose sous toi. Tu tombes "
                "dans le noir, et le noir n'a pas de fond."
            ),
            survival_outcome_desc="reaches the far ledge and pulls us across as the bridge falls",
            survival_narration_fr=(
                "Pas à pas, le poids réparti, tu atteins l'autre rive. Le pont "
                "s'effondre derrière toi. Tu es sorti. Tu as survécu."
            ),
        )

        return AdventureScript(
            char_left_name=char_left_name,
            char_right_name=char_right_name,
            char_left_desc=(
                char_left_desc
                or "a gaunt pale man in a soaked miner's jacket, hollow eyes, "
                "ash-streaked face"
            ),
            char_right_desc=(
                char_right_desc
                or "a wiry man with a weathered scarred face and a cracked helmet lamp"
            ),
            char_left_personality_fr=(
                "Un mineur calme et fatigué, qui connaît la mine par cœur."
            ),
            char_right_personality_fr=(
                "Un homme nerveux et pressé, prêt à tout pour sortir vite."
            ),
            # P2 : conseil angoissant (gauche) + réponse courte (droite),
            # sans « choisis-moi » (le narrateur gère le choix). Ordre aléatoire au render.
            char_left_intro_line_fr=(
                "Quoi qu'il arrive là-dessous, ne t'arrête jamais de marcher."
            ),
            char_right_intro_line_fr="Et ne regarde pas derrière toi.",
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
                f"Si tu as choisi {char_left_name}, voici la nuit qui t'attend : "
                "la mine noyée, l'eau qui monte, et chaque pas qui peut être le dernier."
            ),
            rounds=(round1, round2, round3),
            epilogue_other_desc=(
                "the other character standing alone at the mine entrance, fading into mist"
            ),
            epilogue_narration_fr=(
                f"Si tu avais choisi {char_right_name}, ton histoire aurait été tout autre."
            ),
        )
