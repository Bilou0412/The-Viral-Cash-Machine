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

- **Format CYOA / horreur** (2 choix/1 fatal, 2 persos scalaires, beats fatal/survie,
  `_GOLDEN_RULES`) — abandonné comme cadre produit. Le décrypteur de scènes est **neutre**
  (`src/features/scenes/`). Le décrypteur aventure reste dispo mais n'est plus le défaut.
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

---

## 5. Étapes restantes (ordonnées — 1 étape / session)

> Le rail tourne **en réel** (dogfood 7/7) et la couche **Format** + la **boucle virale** sont
> posées (§4). La spine restante est **l'endgame** (E1–E4) : `idée → moule → 3 variantes →
> prédiction → publication`, agents + perfs réelles. Les concerns produit historiques (flux
> Créer, coût, monétisation, legacy) restent en support (S2–S5).

### S1 — Fermer la boucle réelle (dogfood)  ✅
Fait : vraie vidéo idée → scènes → assets Replicate prouvée (7/7), breakers hors-mock corrigés,
harnais `scripts/dogfood_editor.py`. Voir §4.

### E1 — Réalisateur autonome : AUTO-SPLIT (le FIX)  ⬜  ← PROCHAINE ÉTAPE
La diagnose existe (`shot-audit`, DIR-1). Le fix : un **`ShotSplitter`** (port + Fake + OpenAI)
qui **re-découpe** un plan `over_horizon`/`multi_beat` en **beats distincts** (pas un split
mécanique qui duplique). **Ne PAS** s'appuyer sur l'heuristique `multi_beat` pour piloter sans
la durcir (note dans `_beat_count`). Câblé dans le pipeline scènes → aucun doc généré ne dépasse
l'horizon.

### E2 — Cohérence i2v (start_image par plan)  ⬜
Chaque plan génère **sa** `start_image` depuis la `LocationEntry` + l'établissement de scène en
**image de référence** (`image_input` seedream), + la dernière frame du plan précédent → cohérence
visuelle auto entre plans (perso/décor stables). Touche `editor_generation` (chaînage des refs).

### E3 — Sélecteur de format + publication  ⬜
Front « Créer » : **sélecteur de moule** (route `GET /api/formats` déjà là) — variante (a)
légère d'abord (fixe `Episode.format`, happy path scènes intact). Puis **publication** : export
MP4 → post plateforme (needs creds plateforme).

### E4 — Boucle de perfs réelles (le MOAT)  ⬜
Les perfs des vidéos publiées (rétention/complétion/hook) **re-nourrissent** le prédicteur de
viralité et la structure des formats — le prédicteur `ViralityPredictor` (port déjà posé, VIR-1)
passe de LLM-juge (proxy) à **signal réel**. Le template n'est plus deviné, il est **appris**.

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
