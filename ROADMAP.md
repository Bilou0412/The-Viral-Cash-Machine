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

> Note pivot (2026-07) : le produit est passé du format « aventure à choix / horreur » (CYOA)
> à un **créateur de scènes neutre et générique**. Le rail bas (`ClipBrick` → `VideoSpec` →
> MP4) est **inchangé et réutilisé** ; seul le décrypteur du haut a changé (aventure → scènes).
> Le rail aventure (`openai_adventure_decomposer` → `adventure_to_bricks`) **survit** comme
> chemin alternatif, mais le **happy path** est désormais « Créer » (idée → scènes).

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

---

## 5. Étapes restantes (ordonnées — 1 étape / session)

> Le rail tourne de bout en bout **en backend et en mock**. Les étapes historiques R1–R4
> sont livrées (voir §4). Restent la **boucle réelle** (dogfood), le **flux Créer complet**,
> les **garde-fous coût** et le **socle monétisation**.

### S1 — Fermer la boucle réelle (dogfood)  ⬜  ← PROCHAINE ÉTAPE
Générer une **vraie vidéo** depuis « Créer » avec de **vraies clés** (OpenAI + Replicate) :
idée → scènes (OpenAI 2 phases) → photo d'environnement + plans (image-first) → MP4. Objectif :
**trouver et corriger ce qui casse hors mock** (schéma OpenAI réel, mapping des modèles
Replicate, i2v env→plan, coûts). C'est le prérequis pour dogfooder. Vérifier d'abord sur un
épisode court (1 scène, 2 plans) pour limiter le coût.

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
