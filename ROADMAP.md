# ROADMAP.md — Source unique de vérité

> Ce document **remplace et consolide** les plans précédents (archivés :
> `ARCHITECTURE_PLAN.md`, `EDITOR_PLAN.md`, `MODIF_PLAN.md`, `EXTENSION_PLAN.md`,
> `BRIQUES_PLAN.md`). **Pour reprendre le travail : lire CE fichier**, section
> « État consolidé » (§4) puis « Étapes restantes » (§5) — première ligne ⬜ = prochaine étape.

---

## 1. Le résultat visé (north star)

Un **créateur de vidéos verticales 9:16** pour TikTok/Shorts/Reels, où **l'IA écrit et
découpe, puis on révise en briques** — vite et pas cher, en **ne régénérant que ce qu'on
touche**.

Modèle mental (tranché) : une **VIDÉO** = une séquence ordonnée de **SCÈNES** (l'arc :
accroche → développement → chute). Une **SCÈNE** = un **contexte concentré qui ne se dilue
pas**, en deux temps : **contexte figé** (une **photo d'environnement** qui tient le décor)
puis **contexte en mouvement** (des **plans courts** vidéo/photo qui l'animent, + audio).
Principe : **briques courtes = meilleurs prompts** (une intro de 20 s = plusieurs plans
courts, pas une brique longue diluée).

Décision produit (tranchée) : **« l'IA écrit → je révise en briques »**, PAS un éditeur de
montage vierge. La brique est l'**unité de REVUE d'une génération** — on ajuste ce que l'IA a
produit, on régénère ciblé pour maîtriser le coût. Dialogues/narration en **français**,
prompts visuels en **anglais**.

> Note pivot (2026-07) : PAS un « créateur générique ». Une **usine à moules viraux** — chaque
> FORMAT reste ultra-niche (« Aventure à choix », « Scènes libres »…), **même forme, fond
> variable**. On vend une collection de **machines-à-viral**, pas une toile blanche. Le rail bas
> (`ClipBrick` → `VideoSpec` → MP4) est **inchangé et réutilisé** ; la couche **Format** au-dessus
> (`src/features/formats/`) nomme et unifie les moules (aventure #1, scènes #2). Le rail aventure
> **survit** comme format #1 ; le **happy path** reste « Créer » (idée → scènes, format #2).
>
> **Endgame visé** : `idée → moule → 3 variantes → prédiction → publication`. L'humain n'approuve
> que le **gagnant** ; découpe, cohérence et choix du hook sont **portés par les agents** et, à
> terme, **calibrés par les perfs réelles** (la boucle fermée = le moat).

---

## 2. Le rail retenu (pipeline unique)

```
Idée / thème (page « Créer »)
   │
   ▼  [S-IA]  get_scene_decomposer (Fake offline / OpenAI 2 phases)  →  VideoPlan   (✅ fait)
   │            macro : idée → scènes ; micro : scène → plans courts + audio
   │
   ▼  [S-B]   scene_plan_to_document       →  EditorDocument          (✅ fait)
   │            (briques ClipBrick courtes + INDEX de scènes ; photo d'env en tête)
   │
   ▼  [R2]    UI de REVUE (React)          →  timeline multipiste (Vidéo/Son),
   │            bandes de scène, clic → inspecteur d'args (form_descriptor),        (✅ fait)
   │            régénération ciblée par brique
   │
   ▼  [B1]    document_to_spec             →  VideoSpec (IR immuable)  (✅ fait)
   │
   ▼  [IR]    resolve_real + MoviePyRenderEngine → MP4 final           (✅ existe)
```

Chemin alternatif (legacy, conservé) : `openai_adventure_decomposer → adventure_to_bricks →
document_to_spec` (même sortie `ClipBrick`, sans le modèle de scènes).

Principe directeur : **la brique = revue de la génération**. Tout le rail bas
(compiler → spec → rendu) est déjà là ; les décrypteurs du haut alimentent le même
`EditorDocument`.

---

## 3. Ce qu'on ABANDONNE / absorbe (pour lever le flou)

- **Format CYOA / horreur comme CADRE PRODUIT UNIQUE et rigide** (le produit = *une seule*
  histoire à choix) — abandonné au profit de l'**usine à moules**. ⚠️ **Le CYOA lui-même n'est
  PAS abandonné** : il est le **format flagship #1** (cf. `docs/GTM.md`, commits CYOA-1/2/3,
  `features/formats/catalog.py`), désormais unifié sur le rail v5 comme les autres moules. Le
  décrypteur de scènes neutre (`src/features/scenes/`) reste le **happy path** (« Créer »).
- **Éditeur timeline vierge (composer de zéro)** — abandonné. Le front est une **surface de
  revue** de l'arbre de briques généré (timeline multipiste Vidéo/Son + bandes de scène).
- **Briques PLATES (`GenerativeBrick` image/video/voice) comme modèle d'autoring** — legacy.
  Conservées uniquement pour `resolve.py`/preview existant ; à retirer à terme.
- **`adventure_to_spec` direct (script → VideoSpec sans briques)** — gardé comme chemin rapide
  « sans revue » ; le chemin canonique éditable passe par les briques.

---

## 4. État consolidé (déjà fait — ne pas refaire)

| Domaine | Statut | Où |
|---|---|---|
| Refactor feature-driven (ports, immutabilité, pipeline pur) | ✅ | `src/features/`, `src/pipeline.py` |
| IR déclarative `VideoSpec` + ports `RenderEngine`/`AssetResolver` | ✅ | `src/videospec/` |
| Rendu `MoviePyRenderEngine` (interprète le spec) | ✅ | `src/videospec/render_moviepy.py` |
| `RealAssetResolver` (Step-1 piloté par manifest) | ✅ | `src/videospec/resolve_real.py` |
| Décomposeur LLM aventure (+ chronologie) — legacy | ✅ | `src/features/scripting/` |
| Génération idempotente (ne pas repayer un asset prêt) | ✅ | commit `85bd441` |
| Contrats de capacité + 3 modèles préférés/kind | ✅ | `src/features/compositing/registry.py` |
| Catalogue Replicate + `form_descriptor` (schéma→formulaire) | ✅ | `src/studio/api/services/model_catalog.py` |
| **Brique composite `ClipBrick`** (VIDÉO/PHOTO + enfants + zoom) | ✅ | `src/editor/document.py` (B0) |
| **`document_to_spec`** : briques → `VideoSpec` | ✅ | `src/editor/compile_spec.py` (B1) |
| **`validate_clip`** cohérent avec le compilateur | ✅ | `src/editor/capabilities.py` (B2) |
| **Tests allégés** : défaut ~6 s, `--runheavy` pour tout | ✅ | `tests/conftest.py` (T) |
| **`adventure_to_bricks`** : script → arbre `ClipBrick` (legacy) | ✅ | `src/features/scripting/adventure_to_bricks.py` (R1) |
| **Génération des `ClipBrick`** (image→motion→narration) + idempotence | ✅ | `src/studio/api/services/editor_generation.py` (R1b) |
| **UI de revue en timeline multipiste** (Vidéo / Son, clic → args) | ✅ | `frontend/src/pages/ClipReview.tsx` (#14) |
| **Templates T1** — constructeur du « contenant » (structure) + CRUD | ✅ | `src/studio/db` + `frontend/.../Template*` (#15) |
| **Styles T2.1** — templates de prompt système à champs (cahier des charges) | ✅ | `PromptTemplate` + `frontend/.../PromptTemplate*` (#16) |
| **Modèle de scènes** (`Scene` = INDEX de briques, schema v3, VideoSpec identique) | ✅ | `src/editor/document.py` (#17) |
| **Décrypteur de scènes** (Fake offline + OpenAI 2 phases, neutre) | ✅ | `src/features/scenes/` (#17, #18) |
| **`scene_plan_to_document`** + route `POST /episodes/{id}/scene-document` | ✅ | `src/features/scenes/scene_plan_to_document.py` (#17) |
| **Photo d'environnement = 1re frame des plans** (i2v, `{brick:X.image}`) | ✅ | `editor_generation.py` (#18, R4) |
| **Page « Créer »** (idée + nb de scènes → épisode → revue) + **bandes de scène** | ✅ | `frontend/src/pages/Creer.tsx` (#17) |
| **Nav resserrée** (7 → 4 + groupe « Avancé ») | ✅ | `frontend/src/components/studio/layout.tsx` (#18) |
| **Rigueur type-Rust** : mypy strict cliquet 0, ruff, TS strict, eslint typé | ✅ | `scripts/verify.sh`, `pyproject.toml` (#13) |
| **Boucle réelle prouvée** (dogfood 7/7 assets) + harnais `--check/--text/run` | ✅ | `scripts/dogfood_editor.py` (S1) |
| **Architecture 3 niveaux v5** (Vidéo→Scène→Plan, bibles décor+perso, héritage) | ✅ | `src/editor/document.py`, `compile_shot.py` (T-DESC) |
| **Prompts compilés courts EN** (sujet-en-tête, dédup, ≤ 60 mots) | ✅ | `src/editor/compile_shot.py` (T-DESC-3) |
| **Discipline de durée** (horizon modèle 5 s, split-pas-clamp, fallback-qui-crie) | ✅ | `capabilities.validate_shot_duration`, `features/assets/models.py` (T-DESC-4) |
| **Couche Format** (moules : catalogue + dispatcher + API), aventure #1 / scènes #2 | ✅ | `src/features/formats/`, `services/formats.py` (TPL-1/2) |
| **Boucle virale** : N hooks → prédiction → classement → appliquer la gagnante | ✅ | `src/features/virality/`, routes `/hooks`, `/documents/{id}/hook` (VIR-1/2) |
| **Diagnose de découpe** (shot-audit au niveau document) | ✅ | `capabilities.audit_shot_durations`, route `/shot-audit` (DIR-1) |
| **Auto-split** — aucun plan généré ne dépasse l'horizon (scinde, ne rabote pas) | ✅ | `src/features/scenes/split.py` (E1) |
| **Cohérence i2v** — start_image par plan, ancrée à l'établissement (`image_input`) | ✅ | `scene_plan_to_document.py` (E2) |
| **Publication** (port + Fake + route) — dernier maillon | ✅ | `src/features/publish/`, route `/publish` (E3) |
| **Boucle de perfs réelles (moat)** — perfs → poids appris → prédicteur recalibré | ✅ | `src/features/performance/`, `services/performance.py` (E4) |
| **CYOA unifié sur le rail v5** (flagship #1 ; agents-métiers raffinent le fond ; flux « Créer ») | ✅ | `src/features/formats/`, `services/formats.py` (CYOA-1/2/3) |
| **Template = donnée co-écrite (TPLM)** : reframe + catalogue vu par les agents + effets = données IR | ✅ | `compositing/registry.py`, `services/context.py`, `compile_spec.py` (TPLM-0/A/B) |
| **Réalisateur assemble une partie depuis une description NL** → `FragmentPlan` → briques v5 | ✅ *(feature+tests offline ; **orphelin, à brancher** cf. §5)* | `src/features/crew/` (TPLM-C) |

---

## 5. Étapes restantes (ordonnées — 1 étape / session)

> **Endgame câblé de bout en bout (E1–E4 + E2) — voir ci-dessous.** Chaque maillon est posé en
> **ports + Fakes** (offline vert) ; les impls RÉELLES sont des swaps au bord. Restent : la
> **validation réelle** (dogfood/creds/data — R1–R3 ci-dessous) et les concerns produit (S2–S5).

### S1 — Fermer la boucle réelle (dogfood)  ✅  ·  ### E1 auto-split ✅ · E2 cohérence i2v ✅ · E3 publication ✅ · E4 moat ✅
- **E1** `features/scenes/split.split_overlong_shots` — aucun plan généré ne dépasse l'horizon
  (scinde, ne rabote pas ; câblé dans `generate_video_plan`). *Note : re-décomposition LLM en
  beats distincts = E1b futur.*
- **E2** `scene_plan_to_document` — chaque plan compose SA `start_image` avec l'établissement en
  `image_input`, le motion anime SA frame (≠ photo partagée). Même coût.
- **E3** `features/publish/` + route `POST /episodes/{id}/publish` (FakePublisher ; API plateforme = swap).
- **E4** `features/performance/` — `calibrate_angle_weights` : perfs réelles → poids appris ; le
  prédicteur passe de LLM-juge à **signal réel** (`calibrated_predictor` injecté dans `propose_hooks`).

### TPLM-D — Brancher le réalisateur (co-construction réelle)  ⬜  ← EN COURS
Le cœur de la co-construction (TPLM-C, `src/features/crew/`) était **construit + testé offline
mais ORPHELIN**. On le rend invocable de bout en bout — **description NL → template sauvé →
ré-instancié** (cf. `docs/AUDIT-2026-07.md` §3) :
- **D1** ✅ service `director` (`get_director_agent` + `assemble_part`) + route
  `POST /api/editor/documents/{id}/parts` (`{description, part}` → `assemble_context("realisateur").effects`
  → agent → `fragment_to_bricks` → append à la suite de la timeline, revalidé + persisté).
  `src/studio/api/services/director.py`, tests `test_director_service.py` + route dans `test_editor_api.py`.
- **D2** refonte du stockage `Template` : `structure_json` (slots vides) → `document_json`
  (`EditorDocument` v5) + « save as template » + migration versionnée.
- **D3** ré-instanciation déterministe (`Template` v5 + persos/idée → nouveau `EditorDocument`).
- **D4** front : remplacer `TemplateBuilder` (slots) par une surface de co-construction (NL →
  revue briques v5 → save), câbler `/api/catalog` ; retirer le stub `toast`.
- **D5** fermer l'écart palette/IR (effets `montage.choice/facecam/narrate/subtitles` non-IR) +
  converger `services/intro.py` sur `compile_shot`.

### R1 — Valider E2 en dogfood réel  ⬜
Le wiring E2 est prouvé offline ; reste à confirmer que la RÉFÉRENCE seedream (`image_input`)
produit des frames visuellement cohérentes sur une vraie génération courte. `dogfood_editor.py`.

### R2 — Brancher la publication réelle  ⬜
Swap `FakePublisher` → API plateforme (TikTok/Reels/Shorts) — **needs creds plateforme**.

### R3 — Alimenter le moat en donnée réelle  ⬜
Swap `FakePerformanceSource` → analytics plateforme + persistance de l'historique (published_id,
angle, perfs) → recalibrer le prédicteur en continu. **needs vidéos publiées avec data.**

### S2 — Flux « Créer » complet  ⬜
Étape **photo-first explicite par scène** (générer/uploader l'environnement AVANT les plans,
via `api.uploadFile`), + **sélecteurs Style/Template optionnels** qui grainent le décrypteur
(un Style graine `style_identity`, un Template contraint `n_scenes`/la structure). Rend le
parcours de création complet et guidé.

### S3 — Garde-fous coût (finir R5)  ⬜
`draft` par défaut en revue (existe), **estimation AVANT génération** (`estimate_cost` existe)
affichée dans « Créer »/revue, **confirmation explicite** avant un run « final », **tableau de
coût par épisode**. C'est le cœur du « pas cher » côté UX.

### S4 — Socle monétisation  ⬜
Crédits + **Lemon Squeezy** (ou équivalent) + **tier gratuit watermarké**. Plan déjà esquissé
(crédits décomptés par nœud généré via l'idempotence existante). À n'attaquer qu'une fois S1
fiable (pas de sens de facturer une génération qui casse).

### S5 (option) — Rangement legacy  ⬜
Retirer le chemin `resolve.py`/preview basé sur les **briques plates** une fois la revue
`ClipBrick` pleinement consommée ; ranger les routes de création éparpillées derrière
« Avancé » ; garder le NLE `Editor` pour les power users.

---

## 6. Décisions encore ouvertes (à trancher en temps voulu)

- **Vidéo longue** : enchaîner N scènes concentrées (le modèle le permet déjà) — cadrer le
  nombre de scènes / durée cible par défaut dans « Créer ».
- **Multi-format / séries** (`series/bible.md`) : réutiliseront le même rail briques plus tard.
- **`validate_assignment=True`** sur `ClipBrick` (revalider à la mutation en place) : à peser
  quand l'éditeur mutera intensément des briques.
- **Retrait des briques plates** : quand la revue `ClipBrick` a tout absorbé (cf. S5).

---

## 7. Protocole par étape

modèle/code → tests cheap offline (fakes, sans réseau) → `python -m mypy src` (cliquet 0) +
`python -m pytest -q` (rapide ~6 s ; `--runheavy` pour tout) + `cd frontend && npm run build`
→ (option `bash scripts/verify.sh --heavy` pour la boucle complète) → commit → PR vers `dev`,
CI verte, merge → cocher la table §4 / avancer la ligne ⬜ de §5.
