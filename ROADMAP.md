# ROADMAP.md — Source unique de vérité

> Ce document **remplace et consolide** les 5 plans précédents. Ils deviennent des
> archives (bannière en tête de chacun) :
> `ARCHITECTURE_PLAN.md`, `EDITOR_PLAN.md`, `MODIF_PLAN.md`, `EXTENSION_PLAN.md`,
> `BRIQUES_PLAN.md`. **Pour reprendre le travail : lire CE fichier**, section
> « État consolidé » puis « Étapes restantes » (première ligne ⬜ = prochaine étape).

---

## 1. Le résultat visé (north star)

Produire des **vidéos verticales virales** (format aventure à choix) **vite et pas
cher**, avec une présentation où l'on **voit et ajuste des briques vidéo/photo**
(leurs **arguments d'API** + leur **agencement**), et où l'on **ne régénère que ce
qu'on touche**.

Décision produit (tranchée) : **« l'IA écrit → je révise en briques »**, PAS un
éditeur de montage vierge. La brique est l'**unité de REVUE d'une génération** —
on n'assemble pas une vidéo de zéro, on **ajuste ce que l'IA a produit**, et on
régénère ciblé pour maîtriser le coût.

---

## 2. Le rail retenu (pipeline unique)

```
Idée / thème
   │
   ▼  [IA]   openai_adventure_decomposer  →  AdventureScript        (✅ existe)
   │
   ▼  [R1]   adventure_to_bricks          →  arbre de ClipBrick      (⬜ MANQUANT — connecteur clé)
   │            (briques composites VIDÉO/PHOTO + enfants, ÉDITABLES)
   │
   ▼  [R2]   UI de REVUE (React)          →  on déplie, on édite les
   │            args (form_descriptor) + l'agencement, on régénère ciblé
   │
   ▼  [B1]   document_to_spec             →  VideoSpec               (✅ fait)
   │
   ▼  [IR]   resolve_real + MoviePyRenderEngine → MP4 final          (✅ existe)
```

Principe directeur : **la brique = revue de la génération**. `adventure_to_bricks`
(R1) est le **chaînon manquant** qui rend la génération de l'IA éditable. Une fois
posé, tout le reste (compiler → spec → rendu) existe déjà.

---

## 3. Ce qu'on ABANDONNE / absorbe (pour lever le flou)

- **Éditeur timeline vierge (Remotion-like, composer de zéro)** — abandonné. Le
  front React n'est pas un éditeur blanc : c'est une **surface de revue** de
  l'arbre de briques généré (R2 reformule l'ancien `EDITOR_PLAN` E5–E7).
- **Briques PLATES (`GenerativeBrick` image/video/voice) comme modèle d'autoring**
  — legacy. Conservées uniquement pour le `resolve.py`/preview existant tant que
  R2 ne les a pas remplacées par les `ClipBrick` composites ; à retirer ensuite.
- **Wizard guidé `MODIF_PLAN` LOT 2** — déjà supersédé (cf. mémoire).
- **`adventure_to_spec` direct (script → VideoSpec sans briques)** — gardé comme
  chemin rapide « sans revue », mais le chemin **canonique éditable** devient
  `script → briques (R1) → VideoSpec (B1)`. À terme, `adventure_to_spec` peut se
  redériver comme `document_to_spec(adventure_to_bricks(script))`.

---

## 4. État consolidé (déjà fait — ne pas refaire)

| Domaine | Statut | Où |
|---|---|---|
| Refactor feature-driven (ports, immutabilité, pipeline pur) | ✅ | `src/features/`, `src/pipeline.py` |
| IR déclarative `VideoSpec` + ports `RenderEngine`/`AssetResolver` | ✅ | `src/videospec/` |
| Rendu `MoviePyRenderEngine` (interprète le spec) | ✅ | `src/videospec/render_moviepy.py` |
| `RealAssetResolver` (Step-1 piloté par manifest) | ✅ | `src/videospec/resolve_real.py` |
| Script aventure + décomposeur LLM (+ chronologie) | ✅ | `src/features/scripting/` |
| Génération idempotente (ne pas repayer un asset prêt) | ✅ | commit `85bd441` |
| Contrats de capacité + 3 modèles préférés/kind | ✅ | `src/features/compositing/registry.py` |
| Catalogue Replicate + `form_descriptor` (schéma→formulaire) | ✅ | `src/studio/api/services/model_catalog.py` |
| **Brique composite `ClipBrick`** (VIDÉO/PHOTO + enfants + zoom) | ✅ | `src/editor/document.py` (B0) |
| **`document_to_spec`** : briques → `VideoSpec` | ✅ | `src/editor/compile_spec.py` (B1) |
| **`validate_clip`** cohérent avec le compilateur (`_fields`) | ✅ | `src/editor/capabilities.py` (B2) |
| **Tests allégés** : défaut ~6 s, `--runheavy` pour tout | ✅ | `tests/conftest.py` (T) |
| **`adventure_to_bricks`** : script → arbre `ClipBrick` éditable | ✅ | `src/features/scripting/adventure_to_bricks.py` (R1) |
| **Durcissement `ClipBrick`** : bornes, `allow_inf_nan`, ids non vides | ✅ | `src/editor/document.py` |
| **Entrée du rail câblée** : `POST /api/episodes/{id}/editor-document` | ✅ | `src/studio/api/app.py` |
| **Génération des `ClipBrick`** (image→motion→narration) + idempotence | ✅ | `src/studio/api/services/editor_generation.py` (R1b) |

---

## 5. Étapes restantes (ordonnées — 1 étape / session)

### R1 — `adventure_to_bricks` : script → arbre de `ClipBrick` éditable  ✅
FAIT (`src/features/scripting/adventure_to_bricks.py` + `adventure_to_document`).
Adaptateur **pur, hors-ligne**, ancré sur `plan_episode_assets` : groupe les
`PlannedAsset` en briques (beat vidéo = VIDÉO image+motion ; image seule = PHOTO ;
narration = enfant). **Invariant testé** : les assets génératifs (prompts image/
motion, textes narration) de `document_to_spec(adventure_to_bricks(s))` sont
IDENTIQUES à ceux d'`adventure_to_spec(s)` — couverture 1:1, rien perdu/ajouté.
Toutes les briques sortent `clip_is_ready`. Overlays montage (countdown, plaques,
eye-open) restent hors briques. mypy clean, +8 tests.
**Entrée du rail câblée** (revue multi-agents 2026-06-21) : `POST
/api/episodes/{id}/editor-document` matérialise et persiste le document de briques
depuis le script. + durcissement `ClipBrick` (le bug inf/NaN → doc irrechargeable
est corrigé). R1 n'est plus du code mort côté entrée.

### R1b — Génération des `ClipBrick` (`EditorGenerationService`) + idempotence  ✅
FAIT (`src/studio/api/services/editor_generation.py`). `generate_document`
dispatche désormais `ClipBrick` (image first-frame → motion image→video → enfants
narration TTS) et briques plates legacy. Chaque nœud = une ligne `Asset`
(`beat = {id}.image|{id}.motion|{child.id}`), via un cœur partagé `_run_node`
(Asset/Job/Cost/SSE). **Idempotence** `_existing_done` : un nœud `ready` + fichier
présent n'est ni régénéré ni repayé. Image-first câblé (URL image → entrée i2v du
motion). `regenerate_brick` gère les `ClipBrick` (force). Test offline bout-en-bout :
56 nœuds générés, 2ᵉ run = 0 appel, régénération ciblée = 3 nœuds. mypy baseline
inchangé (40), suite complète 204 passed. Le rail `ClipBrick` est le chemin éditable
canonique ; le monde `PlannedAsset` reste le « chemin rapide sans revue ».
**Le rail tourne maintenant de bout en bout en backend** : script → briques →
génération idempotente → assets. Reste R2 (le front de revue).

### R2 — UI de REVUE (React)  ⬜
Présenter l'arbre de briques généré : timeline avec briques parentes **dépliables**
(VIDÉO violet / PHOTO cyan), enfants visibles (narration/dialogue/zoom), **inspecteur
d'args** branché sur `form_descriptor`, et **état par nœud** (à générer / prêt /
écarté). PAS de composition à blanc — édition + régénération de l'existant. Réutilise
`frontend/src/components/editor/` (Timeline/BrickPalette) en les **reciblant** sur
`ClipBrick`.

### R3 — Régénération ciblée / idempotence par nœud  ⬜
Brancher la génération **par nœud de brique** sur `AssetProvider` + statut `Asset`/
`GenerationJob`. Un nœud `prêt` n'est ni regénéré ni repayé (réutilise `85bd441`).
Champ « écarter » par nœud. C'est le cœur du « pas cher ».

### R4 — Image-first (vérifier/finir)  ⬜
Garantir que toute brique VIDÉO part d'une **image générée d'abord** (first-frame)
puis motion-only (p-video), sans re-description. Vérifier l'état (ex-`EXTENSION` P2 :
splitters `frame_*`/`motion_*` dans `prompts.py`) et compléter si partiel.

### R5 — Garde-fous coût  ⬜
`draft` par défaut en revue, **estimation avant génération** (`estimate_cost` existe),
et confirmation explicite avant un run « final ». Tableau de coût par épisode.

---

## 6. Décisions encore ouvertes (à trancher en temps voulu)

- **Multi-format** : aventure d'abord ; la série « La Coloc » (`series/bible.md`)
  réutilisera le même rail briques plus tard (pas maintenant).
- **Durcissement du modèle `ClipBrick`** — ✅ FAIT : bornes numériques (durée ≥ 0,
  zoom > 0, focus ∈ [0,1]), `allow_inf_nan=False`, `id` non vide (`Annotated[...]`).
  Reste optionnel : `validate_assignment=True` (revalider à la mutation en place),
  à peser quand l'éditeur mutera des briques.
- **Retrait des briques plates** : quand R2 consomme les `ClipBrick`, retirer le
  chemin `resolve.py`/preview basé sur les briques plates.

---

## 7. Protocole par étape

modèle/code → tests cheap offline → `mypy src/editor` + `pytest tests/` (rapide ~6 s ;
`pytest --runheavy` pour tout, dans `vcm-dev`) → `graphify update .` → commit → cocher
la table de la section 5.
