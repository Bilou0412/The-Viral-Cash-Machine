# Architecture — règles (le « rail unique »)

> La loi qui tue la bidouille : **un seul rail**. Toute vidéo, quel que soit son FORMAT
> (moule), passe par la MÊME architecture. Aucun format ne construit ses prompts à la main.

## La loi

**Un FORMAT = une STRUCTURE qui produit un `EditorDocument` v5.** Point.

- Le document est TOUJOURS le v5 : **Vidéo → Scène → Plan** (`EditorDocument` → `Scene` →
  `ClipBrick.shot: ShotBrief`), avec **bibles réutilisables** (`CharacterEntry` perso,
  `LocationEntry` décor) et **héritage** PLAN > SCÈNE > VIDÉO. (`src/editor/document.py`)
- **Les prompts se COMPILENT, ils ne s'écrivent pas.** `src/editor/compile_shot.py`
  (`compile_image_prompt` / `compile_motion_prompt` / `recompile_document`) est le SEUL
  producteur de prompts image/mouvement. Un format qui fabrique ses prompts en concaténant
  des phrases à la main est une **régression** (deux systèmes de qualité divergents).
- **Un seul descripteur texte** : `src/editor/describe.py` (`describe_document`) rend
  n'importe quel format en texte. Si un format n'est pas rendable ici, c'est qu'il n'est pas
  sur le rail — à corriger, pas à contourner.
- **Un seul compilateur de rendu** : `src/editor/compile_spec.py` (`document_to_spec`) →
  `VideoSpec` → MP4. Idem : un format ⇒ un `EditorDocument` ⇒ ce chemin.
- **Un format = une entrée** : `src/studio/api/services/formats.py` (`build_format_document`)
  dispatche vers le pipeline du format ; tous **retournent le même IR** `EditorDocument`.

Le **cerveau** d'un format (le décomposeur LLM : `AdventureScript`, `VideoPlan`…) reste
spécifique et peut être riche. Ce qui est **partagé et non-dupliquable** : le document v5,
la compilation des prompts, la description, le rendu. On sépare **structure** (propre au
format, codée en dur) et **fond** (rempli par l'IA) — cf. `src/features/formats/`.

## Conventions (non négociables — déjà appliquées sur le rail)

- **Langue** : prompts visuels en **anglais**, dialogues/narration en **français**.
- **Noms de personnages** = **prénoms humains français** (jamais un rôle/métier, jamais un
  article « le/la/un »). Garde-fou déterministe : `scene_plan_to_document._clean_name`.
- **1 plan = 1 beat = 1 delta** ≤ **l'horizon de cohérence du modèle** i2v actif
  (`features/assets/models.max_coherent_duration_s`). Trop long → on **scinde**, on ne rabote
  pas (`features/scenes/split.split_overlong_shots`, `capabilities.validate_shot_duration`).
- **Prompts image courts, EN, sujet-en-tête, dédupliqués** (budget de mots, cf. `compile_shot`).
- **Idempotence de génération** : un asset `ready` n'est ni régénéré ni repayé.
- **Ports** (`typing.Protocol`) pour chaque feature ; impl Fake (offline) + réelle (OpenAI/
  Replicate) injectées au bord. Tests **offline d'abord**.

## Anti-patterns (= bidouille, à refuser)

- Un format qui émet des briques **blob** (`shot=None`) avec un prompt pré-cuit au lieu d'un
  `ShotBrief` structuré → invisible pour `describe`, hors de la qualité `compile_shot`.
- Un **deuxième** système de construction de prompts parallèle à `compile_shot`.
- Une **deuxième** UI/atelier de création qui ne parle pas le document v5.
- Un champ « magique » dupliqué (durée, modèle) au lieu d'une source unique.
- Brancher la **salle multi-agent à contrat libre** (`crew_room` : le réalisateur INVENTE
  les plans) sur un **moule à structure fixe** (CYOA) → l'agent réinvente une structure qui
  doit être **codée en dur**. Sur un moule, les agents raffinent le **fond**, pas la forme :
  on utilise les agents de contenu **agnostiques au format** (`direct_art_direction`,
  `direct_dialogue`, qui réécrivent prompts d'établissement et texte parlé d'un `EditorDocument`
  quelconque). La salle libre reste pour les formats **sans** grille de beats imposée (scènes).

> Règle de trois pour l'abstraction : on n'extrait un schéma générique (ex. slots de format)
> qu'au **3ᵉ** exemplaire — pas depuis n=1. La structure d'un format reste **codée en dur**
> tant qu'on est en dessous. (cf. `ROADMAP.md`, `DECISIONS.md`)
