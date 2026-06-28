# EDITOR_PLAN — Éditeur de vidéo par briques (le vrai produit)

> ⚠️ **ARCHIVE — supersédé par [`ROADMAP.md`](ROADMAP.md).** L'idée « éditeur vierge à
> composer de zéro » est **abandonnée** ; le front devient une **surface de revue** de
> l'arbre de briques généré par l'IA (ROADMAP §3, R2). E2/E3/E4 (contrats, catalogue,
> form) sont faits et réutilisés. Conservé pour l'historique.

> Correction de cap (2026-06-14). Le produit n'est PAS un wizard guidé : c'est un
> **éditeur** type Remotion/DaVinci pour briques IA. Palette à gauche → glisser-
> déposer sur une **timeline** → cliquer une brique → éditer **tous** ses arguments
> (schéma du modèle via MCP Replicate) → composer (calques, texte, média importé) →
> alimenter le tout par un **contexte récit** (texte → contexte → prompts d'assets).
>
> Supersède la direction « wizard » de MODIF_PLAN LOT 2 (front). Le backend LOT 0/1
> est réutilisé. `STUDIO_V2_PLAN.md` (templates-scénario) est absorbé ici (templates
> = presets opinionated de briques). LOT 3 (tokens) reste pour plus tard.

## Décisions verrouillées
- **Contexte = global hérité + surcharges locales** par brique.
- **Modèles par brique = 3 préférés** (low-cost / qualité-prix / premium) **+ recherche
  libre filtrée** par le *contrat de capacité* de la brique (le modèle doit exposer les
  args requis).
- **Éditeur 100 % manuel d'abord** ; assistant IA (décomposeur existant) plus tard.

## Concepts

### 1. Brique (Brick)
Une unité posée sur la timeline. Types :
- **Photo** (génération image) · **Vidéo** (image→vidéo) · **Narration** (TTS) —
  briques *génératives* (ont un modèle + des args).
- **Texte** (overlay) · **Média importé** (photo/vidéo fournie, non générée) ·
  **Calque** (overlay invisible/PNG, masque) — briques *locales* (pas de modèle).

Chaque brique générative porte : `type`, `model_id`, `params: dict` (libre, validé
contre le schéma du modèle), `context_overrides` (texte local), `layers` (overlays
empilés), position timeline (track + start + durée).

### 2. Contrat de capacité (par type de brique)
Définit les arguments **requis** → sert (a) de garde-fou sur les params, (b) de filtre
pour la recherche libre de modèles.
- **Photo** : `prompt` (req) · `image_input`/réf (opt) · taille/ratio.
- **Vidéo** : `prompt` (req) · `duration` (req) · `image_input` (req — image-first) ·
  `audio`/son (souhaité) · description de **mouvement** · ratio/résolution.
- **Narration** : `text` (req) · `voice` (req) · modèle TTS.
Les 3 modèles préférés par type sont validés à la main ; la recherche libre n'affiche
que les modèles dont le schéma d'inputs couvre les champs requis.

### 3. Inspecteur d'arguments (piloté par le MCP Replicate)
Clic sur une brique → formulaire **généré dynamiquement** depuis le schéma d'inputs du
modèle (`mcp__replicate__get_models` / `get_models_versions` → OpenAPI input schema).
**Tous** les arguments du modèle sont éditables, avec défauts. **Changer de modèle**
régénère le formulaire (les params communs sont conservés, le reste réinitialisé aux
défauts). Une photo peut être la valeur d'un argument (image d'entrée).

### 4. Presets / Templates / Profils
- **Preset** : valeurs d'args par défaut d'une brique.
- **Template (opinionated)** : une intention + des **inputs typés** + un **prompt système
  préfait**. Ex. « illustrer une action » inspiré des **plans de cinéma** (plan large,
  gros plan, contre-plongée…) → propose des champs guidés et compose le prompt.
- **Profil** : un preset/template **enregistré par l'utilisateur** (profils photo,
  narration, etc.), réutilisable.

### 5. Composition / calques
Narration incrustable sur **n'importe quelle** occurrence photo/vidéo ; **calques**
importés (PNG/masques) ; **texte** ; **média propre** non généré. Programmable (ordre
des calques, position, durée).

### 6. Contexte récit (le cœur)
Un **contexte global** (texte → la trame, les persos, la DA) hérité par défaut par toutes
les briques + des **surcharges locales** par brique. Le contexte est **compilé** en
matière de prompt pour chaque asset génératif (le « texte qui devient contexte pour les
descriptions d'assets »). C'est la couche qui relie récit et montage.

## Réutilisation de l'existant
- **`src/videospec/models.py`** → base du **document timeline** (segments/assets/effets/
  placement déjà validés). À étendre pour `params: dict` libre + calques + contexte.
- **`src/features/compositing/registry.py`** → **catalogue de briques** (étendre : contrat
  de capacité + 3 modèles préférés par type).
- **Générateurs** (`AssetProvider` image/vidéo/voix) → **exécution** des briques.
- **MCP Replicate** → schémas d'args + recherche/filtre de modèles.
- **`themes.py`** → 1er type de **preset** (DA) ; à généraliser en profils.
- **`generation.py` / `montage.py`** → exécution + montage depuis la timeline (réutilise
  la revue unitaire = clic brique → régénérer).
- **Superséd é** : front LOT 2 (wizard + AssetReview) ; la revue survit intégrée à l'éditeur.

## Phases

| Phase | Sujet | Statut |
|---|---|---|
| **E1** | Modèle de document éditeur (Timeline + Brick + params libres + calques + contexte global/local) — pur, sérialisable, validé ; compile vers exécution. Tests. | ⬜ |
| **E2** | Catalogue de briques + **contrats de capacité** + 3 modèles préférés/type (registry étendu). Tests. | ⬜ |
| **E3** | Service **MCP** : schéma d'inputs d'un modèle → descripteur de formulaire ; recherche/filtre de modèles compatibles avec un contrat. Cache. | ⬜ |
| **E4** | **Presets / Templates / Profils** (DB) : presets par défaut, templates opinionated (plans cinéma), enregistrement de profils. | ⬜ |
| **E5** | **Front éditeur** : palette gauche + timeline glisser-déposer + inspecteur d'args dynamique (switch modèle) + calques/texte/média importé. (agent designer → prototype React) | ⬜ |
| **E6** | **Contexte récit** : contexte global + surcharges locales → compilation des prompts d'assets. | ⬜ |
| **E7** | **Exécution + revue + montage** depuis la timeline (réutilise generation/montage ; régénération unitaire). | ⬜ |
| (plus tard) | Assistant IA (décomposeur pré-remplit la timeline) · LOT 3 tokens/billing. | ⬜ |

## Méthodo
Plan figé → exécution par équipe d'agents (un agent par couche), mypy + tests verts +
commits traçables, comme LOT 0/1. E1→E2→E3 (backend) parallélisables avec E5 (front,
contre contrat). E6 (contexte) après E1.
