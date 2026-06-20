# BRIQUES_PLAN.md — Présentation en briques composables (vidéo/photo)

> Plan validé par équipe d'agents (exploration UI + assets + plans + tests).
> **Décisions utilisateur** : surface = **frontend React** (Timeline/Palette existants) ;
> hiérarchie = **VIDÉO et PHOTO sont les briques parentes**, les appels API enfants
> (narration, dialogue, photo first-frame) vivent **à l'intérieur** de la brique.
> **Ne pas coder sans valider chaque étape** (1 étape / session, comme le refactor).

---

## 0. Pourquoi ce plan (constats des agents)

1. **La « brique » existe déjà, mais à plat.**
   - Backend : `src/editor/document.py` → `EditorDocument.bricks: List[Brick]` où
     `Brick = GenerativeBrick(image|video|voice) | MediaBrick | TextBrick`, chacune avec
     `layers: List[Layer]` (enfants) + `placement: TimelinePlacement`.
   - Frontend : `frontend/src/components/editor/Timeline.tsx` + `BrickPalette.tsx` +
     `brick-helpers.ts` (couleurs par type). Briques posées **côte à côte**, pas imbriquées.
   - **Manque** : une brique VIDÉO qui *contient* sa photo first-frame + sa narration. C'est
     exactement la méthodo « image-first » d'`EXTENSION_PLAN.md` (vidéo = image générée d'abord
     + p-video motion-only). On rend cette imbrication **explicite et présentée**.

2. **« Asset » ≠ « brique ».** (point clé de la demande)
   - **Asset** = fichier produit sur disque (`base_image.png`, `video.mp4`, `narrator.mp3`) —
     déjà modélisé : `AssetBundle`, table `Asset` (`src/studio/db/models.py`).
   - **Générateur** = l'appel API (Replicate/OpenAI) — port `AssetProvider`
     (`image.seedream`, `video.pvideo`, `voice.minimax` dans `features/compositing/registry.py`).
   - **Brique** = la **déclaration** « voici quoi générer + avec quels params ». La brique
     **transpose l'appel API**, elle n'est pas l'asset. On travaille la couche brique, pas l'asset.

3. **Les tests de script sont déjà quasi gratuits.**
   - `test_adventure.py` (21), `test_chronology.py` (9, faux client OpenAI), `test_prompts.py` (6),
     `test_adventure_to_spec.py` (4), `test_studio_services.py` (9, `FakeAssetProvider`) →
     **0 appel API réel, ~quelques secondes**.
   - Le coût réel vient de : **golden SSIM ffmpeg** (`test_golden.py` regression, ~30 s) et
     **render MoviePy** (`test_videospec_render.py`, ~3-5 s). Donc « alléger » = **isoler ces 2-3
     là** + garder/renforcer le scripting. On ne casse rien du scripting.

---

## 1. Modèle cible — la brique composite imbriquée

Une **brique parente** = une sortie média visible sur la timeline. Deux types : `video`, `photo`.
Elle porte sa propre génération **et** ses enfants (chaque nœud = un appel API transposé).

```
MediaBrick                       (posée sur la timeline ; couleur selon kind)
├─ id
├─ kind: "video" | "photo"
├─ placement: { track, start, duration }
├─ context_overrides            (surcharge du NarrativeContext global ; DA, perso…)
│
├─ image: ImageGen              (TOUJOURS présent)
│    ├─ model_ref   ex. "image.seedream"
│    ├─ prompt / params (taille, aspect, seed…)        ← appel text→image transposé
│    └─ pour kind=video : c'est la PHOTO first-frame (enfant intrinsèque)
│
├─ motion: VideoGen?            (UNIQUEMENT kind=video)
│    ├─ model_ref   ex. "video.pvideo"
│    └─ params (duration, motion prompt, draft…)       ← appel image→video transposé
│
├─ zoom: ZoomEffect?            (UNIQUEMENT kind=photo — Ken Burns)
│    └─ params (from/to scale, focus, durée)           ← pas un appel API : effet de rendu
│         agence une PHOTO fixe « zoomée » (= NarrationSegment de VideoSpec)
│
└─ children: List[ChildNode]    (0..n — « des enfants ou pas »)
     ├─ NarrationChild   { model_ref:"voice.minimax", text_fr, voice_id }   ← TTS transposé
     ├─ DialogueChild    { text_fr, delivery, voice_source }                ← voix perso
     └─ OverlayChild     { text | png | timer | nameplate }                 (calques visuels)
```

Lecture de la demande → modèle :
- *« les brique c'est video ou photo »* → `kind ∈ {video, photo}`, **types parents**.
- *« dans les brique on transpose les différents appel api »* → `image` / `motion` / `children`
  pointent chacun vers un générateur du `registry` + portent les params de l'appel.
- *« dans les brique on des enfant ou pas, ex. narration ou même photo pour la brique video »* →
  `children` (narration/dialogue) + la **photo first-frame** comme nœud `image` interne du `video`.
- *« il y a des moments où on a juste des photo zoomées »* → brique **PHOTO autonome** posée
  sur la timeline (pas enfant d'une vidéo), avec `zoom` (Ken Burns) + narration enfant optionnelle.
  Se compile en `NarrationSegment` (image fixe zoomée + voix off + sous-titres).
- *« asset c'est déjà généré, plutôt les brique qui vont générer ces asset »* → la brique est la
  **déclaration de génération** ; l'asset produit reste en base (`Asset` row) et n'est pas re-payé
  (idempotence, commit `85bd441`).

> On **ne supprime pas** `VideoSpec`/`Segment` (l'IR de rendu) ni `AdventureScript` (le script).
> La brique composite se **compile** vers `VideoSpec` (assets + segments) via le chemin existant
> (`adventure_to_spec.py` / `produce.py`). La brique = couche **authoring** ; VideoSpec = couche **rendu**.

---

## 2. Présentation (frontend React) — « la présentation doit être différente »

- **Timeline** : la brique parente est un bloc unique. Couleur par `kind` (video=violet,
  photo=cyan — réutilise `brick-helpers.ts`). **Pas** une piste par appel API : un seul bloc
  qui se **déplie**.
- **Vue dépliée / inspecteur** : à l'intérieur, on voit les nœuds enfants empilés —
  `image` (la photo), `motion` (si video), puis `children` (narration verte, dialogue, calques).
  Chaque nœud = un mini-formulaire de params (prompt, modèle, durée, voix…).
- **Palette** : on glisse une brique **VIDÉO** ou **PHOTO** ; depuis la brique on **ajoute des
  enfants** (« + narration », « + dialogue », « + calque »). C'est la différence visuelle clé :
  on ne présente plus 5 champs texte « script » à plat, mais des briques média qui contiennent
  leurs générateurs.
- **État par nœud** : badge `à générer / en cours / prêt / écarté` (réutilise statut `Asset` +
  champ `excluded` M1/M2). Re-génération = uniquement le nœud modifié (idempotence).

---

## 3. Étapes (1 étape / session, protocole refactor : modèle → tests cheap → commit)

### Étape B0 — Modèle de brique composite (Python, backend)
- Dans `src/editor/document.py` : ajouter `MediaBrick(kind=video|photo)` avec `image` (ImageGen),
  `motion` (VideoGen optionnel), `children` (union NarrationChild/DialogueChild/OverlayChild).
- Bump `schema_version` + **migration** des `EditorDocument.doc_json` existants (briques plates
  → briques composites). Sérialisation JSON round-trip.
- Tests : **purs, offline, cheap** (style `test_editor_document.py`). À garder.
- ✅ Sortie : modèle + schéma JSON + migration testés, **0 appel API**.

### Étape B1 — Compilateur brique → VideoSpec
- `MediaBrick` → `assets` (`ImageAsset` pour la photo/first-frame, `VideoAsset` pour le motion,
  `VoiceAsset` pour narration/dialogue) + `Segment` (Intro/Footage/Narration/Countdown).
- Réutiliser les patterns d'`adventure_to_spec.py`. Intégrité référentielle des `id`.
- Tests : offline avec `FakeAssetResolver` (style `test_adventure_to_spec.py`). Cheap. À garder.

### Étape B2 — Catalogue de briques + contrats de capacité
- Par `kind` et par nœud : `required_args`, `optional_args`, `preferred_models` (3 modèles/type :
  `image.seedream`, `video.pvideo`, `voice.minimax`). Étend `features/compositing/registry.py`.
- Service MCP Replicate : schéma d'inputs du modèle → descripteur de formulaire (pour l'inspecteur).
- Tests : data-only, cheap (style `test_registry.py` / `test_model_catalog.py`).

### Étape B3 — Frontend React (présentation imbriquée)
- `frontend/src/lib/types.ts` : type `MediaBrick` imbriqué (miroir du modèle Python).
- `Timeline.tsx` : bloc parent dépliable, couleur par `kind`, sous-lignes enfants.
- `BrickPalette.tsx` : briques VIDÉO/PHOTO + actions « ajouter enfant ».
- Inspecteur dynamique : formulaire par nœud depuis le contrat de capacité (B2).
- Pas de tests lourds : `test_render_contract.py` (Python↔zod) déjà skip si Node absent.

### Étape B4 — Câblage génération idempotente sur l'arbre de briques
- Brancher la génération par **nœud** sur `AssetProvider` + statut `Asset`/`GenerationJob`.
- Réutiliser l'idempotence (commit `85bd441`) : un nœud déjà `prêt` n'est ni regénéré ni repayé.
- Champ « écarter » par nœud (M1/M2). Revue step-by-step (M1) au niveau brique.

### Étape T — Allègement des tests (indépendante, peut se faire en premier)
But : *« sans faire de teste trop poussé, que le test sur la génération de script »*.
- Ajouter des **markers** pytest dans `pyproject.toml` :
  `golden_regression` (ffmpeg SSIM), `render` (MoviePy), `slow`.
- Run par défaut = **scripting + logique pure** : `addopts = -m "not golden_regression and not render"`.
  (Le golden regression ne tourne déjà que si `GOLDEN_CANDIDATE` est set — on le formalise.)
- **Suite « source de vérité » à garder/renforcer** (génération de script) :
  `test_adventure.py`, `test_chronology.py`, `test_prompts.py`, `test_adventure_to_spec.py`,
  `test_studio_services.py`.
- **Opt-in lourd** (cibles séparées) : `golden_regression` (post-refactor manuel),
  `render` (CI nightly éventuel).
- Cible `make test-fast` (ou alias) = la suite scripting + modèle, ~quelques secondes.
- Aucune suppression de couverture script ; on **déplace** le lourd derrière un marker.

---

## 3 bis. État d'avancement — POINT DE REPRISE

| Étape | Statut | Sujet | Commit |
|-------|--------|-------|--------|
| B0 | ✅ FAIT | Modèle `ClipBrick` composite + migration v1→v2 | `63df007` |
| B1 | ✅ FAIT | Compilateur `document_to_spec` : ClipBrick → VideoSpec | (en cours) |
| B2 | ⬜ | Catalogue briques + contrats de capacité + 3 modèles/type | |
| B3 | ⬜ | Frontend React : brique parente dépliable + inspecteur | |
| B4 | ⬜ | Génération idempotente câblée par nœud | |
| T  | ⬜ | Markers pytest (golden_regression/render en opt-in) | |

Protocole/étape : modèle/code → tests cheap offline → `mypy src/editor` +
`pytest tests/` (dans `vcm-dev`) → `graphify update .` → commit → cocher la table.

---

## 4. Ce qu'on ne touche PAS (anti-régression)
- `AdventureScript` et `openai_adventure_decomposer` (le script reste le cœur testé).
- `VideoSpec`/`Segment`/ports de rendu (IR de rendu inchangée ; on compile vers elle).
- L'idempotence de génération (commit `85bd441`) — on la réutilise telle quelle.
- Le golden oracle self-integrity (3 tests cheap) reste actif.

## 5. Décisions encore ouvertes (à trancher en temps voulu)
- Imbrication à **2 niveaux** (parent média → enfants) suffit-elle, ou faut-il des sous-briques
  récursives ? → démarrer à 2 niveaux (couvre la demande), garder l'union extensible.
- La brique VIDÉO peut-elle avoir **plusieurs** photos (séquence de frames) ou une seule
  first-frame ? → une seule first-frame en B0/B1 ; multi-frames = extension ultérieure.
- Faut-il garder `AdventureScript` comme **générateur** de briques (script IA → arbre de briques)
  en plus de l'édition manuelle ? → oui à terme (étape post-B4), hors périmètre initial.
