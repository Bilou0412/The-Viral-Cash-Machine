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
la compilation des prompts, la description, le rendu — cf. `src/features/formats/`.

## Le TEMPLATE = une DONNÉE co-écrite (la feature du projet)

Le produit n'est pas « des moules codés en dur » : c'est **la machine à co-construire des
templates réutilisables avec les agents**. Donc :

- **Un TEMPLATE est un `EditorDocument` v5 sauvé et paramétrable** (ou un **fragment** = une
  séquence, p.ex. une intro), PAS du Python figé. La structure est **co-écrite par les agents**
  (à partir d'une **description NL** de l'humain + le **catalogue** des briques/effets), puis
  **sauvée** pour être **ré-instanciée** plus tard (nouveaux persos/idée) et **améliorée**.
- **Les agents sont conscients du catalogue.** Ils VOIENT toute la palette — génératif
  (`compositing.registry.CONTRACTS`) ET effets de montage (`compositing.registry.REGISTRY` :
  `montage.timer/choice/zoom/nameplate/facecam/narrate/eye_open`) — via `AgentContext.tools`
  (`services/context.py`). Un agent qui ne voit pas un effet ne peut pas le poser : le catalogue
  est la **source unique** de ce qu'on peut assembler.
- **Les effets sont des DONNÉES IR**, pas de l'impératif. Un countdown flou, un choix A/B, un
  zoom, une nameplate se **déclarent sur l'`EditorDocument`** et se **rendent via
  `document_to_spec`** — jamais une fonction MoviePy invoquée hors du rail. Un effet non
  représentable en IR n'est pas sur le rail — à corriger.
- **Un décomposeur codé en dur (`adventure_to_video_plan`…) est un SEED**, pas le mécanisme :
  un exemple de départ qu'on sauve comme template, pas la façon dont on crée des formats.

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
- Un **effet de montage invoqué en impératif** (fonction MoviePy appelée hors du rail) au lieu
  d'être **déclaré comme donnée** sur l'`EditorDocument` et rendu par `document_to_spec`.
- Un agent qui **assemble à l'aveugle** (sans lire le catalogue `AgentContext.tools`) et donc
  invente ou ignore des briques/effets au lieu de **choisir dans la palette réelle**.
- **Ré-inventer la structure à chaque génération** au lieu de **sauver le template** co-écrit
  puis de le **ré-instancier** : la co-construction se fait UNE fois (avec l'humain), le
  template sauvé est ensuite instancié de façon **déterministe** (idempotence de forme).

> Règle de trois pour l'abstraction : on n'extrait un schéma générique (ex. slots de format
> paramétrables) qu'au **3ᵉ** template — pas depuis n=1. En dessous, un template reste un
> `EditorDocument` sauvé **concret** (données), pas une abstraction prématurée. (cf.
> `ROADMAP.md`, `DECISIONS.md`)
