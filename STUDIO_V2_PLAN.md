# Studio v2 — Plan « templates de scénario » + UX (vers un SaaS)

> Plan POUR PLUS TARD (après la refonte v7 / R5). Vision : un SaaS de création de
> vidéos IA verticales, où l'**UI/UX est le produit**. À ne démarrer qu'une fois
> le format unique « Aventure » pleinement validé bout-en-bout.

## 1. Analyse de l'existant

Un seul format « Aventure » codé en dur :
- prompts système (dans `openai_adventure_decomposer.py`),
- schéma `AdventureScript`, prompts visuels (`prompts.py`),
- compositeur (`adventure_compositor.py` : timer, nameplates, sous-titres, choix),
- studio DB/API (FastAPI/SQLite) + front (React/Vite/Tailwind/shadcn).

Pas de notion de **template** : un autre thème = dupliquer du code. C'est ce
qu'on veut casser.

## 2. Le paradigme cible — fabrique de templates

```
TEMPLATE de scénario = une SAVEUR (prompts système) sur un SQUELETTE partagé.
  • PARTAGÉ (jamais redéveloppé) : schéma AdventureScript, validation, prompts
    visuels, compositeur (timer/nameplates/sous-titres/choix), les 3 paliers,
    la méthodo image-first + réf perso + chaînage.
  • PROPRE au template : le system prompt (ton, archétypes, DA), nom, cover,
    éventuels overrides de style visuel.
→ « Aventure horreur » devient le 1er template. On en crée d'autres SANS coder,
  juste en écrivant un nouveau system prompt (« Aventure SF », « Médiéval »…).
```

**Garde-fou clé** : le system prompt d'un template = une **zone « saveur » libre**
PLUS un **socle de règles d'or VERROUILLÉ** (visuels EN / dialogues FR, structure
3 rounds, langage simple, jamais de texte à l'image, caméra/POV…). Sans ce socle,
un template casserait la conformité.

## 3. Modèle de données

- `Template` : id, name, description, cover_image_path, **flavor_prompt** (la
  saveur éditable), visual_style (override DA optionnel), owner_id, created_at,
  is_public (pour un futur marketplace).
- Seed : « Aventure horreur » (la saveur actuelle extraite du code).
- `Episode.template_id` → l'épisode sait de quel template il vient.

## 4. Architecture

- Le décomposeur compose `socle_règles_verrouillé + flavor_prompt(template)` au
  lieu du system prompt hardcodé. Le reste (schéma, validation, prompts visuels,
  compositeur, paliers) reste partagé.
- Générateur de template = CRUD `Template` + éditeur de `flavor_prompt` (aide,
  preview d'un script de test, génération de la cover via seedream).

## 5. UX — le cœur du produit (SaaS : l'UX EST la valeur)

```
🏠 HOME = MOSAÏQUE DE THÈMES (tuiles avec cover)            [+ Créer un thème]
        │  chaque tuile = un Template
        ▼  click
🧙 WIZARD GUIDÉ (par template)
   Étape 1 — Inputs du contrat (vides au départ, placeholders d'aide) :
       • L'aventure (1-3 phrases)
       • Perso A : nom + description courte (apparence + caractère)
       • Perso B : nom + description courte
       • Palier : 🟢 Draft   💰 Rapport q/p   💎 Premium  (+ coût estimé live)
   Étape 2 — MODE de production :
       ① « Tout créer d'un coup » → produce → 1 barre de progression → vidéo
       ② « Étape par étape » → script → assets par round → montage :
            chaque étape présentée, RÉVISABLE / régénérable à l'unité,
            barres de chargement (SSE) + coût estimé puis réel.
```

### Principes UI/UX (non négociables — c'est le produit)
- **Clair, non surchargé, bien cadré** : à chaque écran on comprend le but et la
  prochaine action. Une action principale par écran.
- **Progressive disclosure** : l'avancé (voix, style) est replié par défaut.
- **Toujours montrer le coût** avant de dépenser ; états de chargement explicites.
- **Réversibilité** : tout asset est régénérable à l'unité, rien n'est figé.
- **Aperçu vertical 9:16** partout (c'est le livrable).
- **Feedback temps réel** (SSE) pendant les générations longues.
- Thème studio sombre, soigné, cohérent.

## 6. Dimension SaaS (vision)

- **Multi-tenant** : comptes, projets par utilisateur, isolation des données.
- **Auth** + quotas.
- **Facturation à la génération** : les 3 paliers = grille de prix (le coût
  Replicate réel + marge). Le journal de coûts (déjà en base : `CostEntry`) est
  la fondation du billing.
- **Marketplace de templates** (plus tard) : `Template.is_public` → partager /
  vendre des thèmes.
- **Bibliothèque** par utilisateur (déjà : `/library`).
- L'UX guidée + la fabrique de templates = le différenciateur produit.

## 7. Phases

| Phase | Sujet | Statut |
|---|---|---|
| T1 | Modèle `Template` (DB) + seed « Aventure horreur » + décomposeur paramétré (socle verrouillé + flavor) + `Episode.template_id` | ⬜ |
| T2 | Générateur de template : CRUD + éditeur de flavor_prompt + cover auto (seedream) + preview script | ⬜ |
| T3 | Front : mosaïque de thèmes + wizard guidé (contrat + 3 paliers) — *absorbe le R5c* | ⬜ |
| T4 | Front : 2 modes (tout d'un coup / step-by-step) avec progression SSE, régén, coûts | ⬜ |
| T5 | Polish UX (principes ci-dessus) + préparation SaaS (auth/billing = lot séparé) | ⬜ |

## 7b. Backlog UX (retours live après 1re utilisation Docker)

- **Barre de progression temps réel** pendant la génération d'assets (et la
  production complète) : afficher l'avancement (n/total assets, beat en cours).
- **Pas de rafraîchissement manuel** : la page se met à jour seule (vidéo finale
  qui apparaît automatiquement quand c'est prêt).
- ✅ Faisable SANS refonte : l'infra SSE existe déjà — `src/studio/api/events.py`
  (bus), route `GET /api/events/{episode_id}`, hook `frontend/src/hooks/use-job-events.ts`.
  Le backend publie déjà : `generation_started/asset_started/asset_ready/
  asset_failed/generation_done` + `produce_started/produce_done`. Reste à :
  (a) connecter le hook SSE à une barre de progression sur les pages Assets &
  Montage ; (b) invalider la query épisode/vidéo sur `produce_done` (auto-refresh).

## 8. Remarques / critiques

- **Garder le squelette PARTAGÉ** : les templates ne changent que la saveur.
  Sinon chaque thème = re-dev → ingérable. Décision structurante.
- **Socle de règles verrouillé** dans le décomposeur : la zone éditable du
  template ne peut pas casser la conformité (langue, structure, no-text…).
- **Step-by-step ≈ déjà là** côté backend (generate/regenerate/montage séparés) ;
  « tout d'un coup » = route `/produce` (faite en R5a). T4 = surtout de l'UX.
- **R5c se fond dans T3** (le wizard, rendu « par template »).
- **Auth/billing** : lot SaaS séparé, à ne pas mélanger avec la fabrique de
  templates (faire tourner le moteur créatif d'abord, monétiser ensuite).
