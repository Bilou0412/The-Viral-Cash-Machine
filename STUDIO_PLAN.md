# Plan — VCM Studio (studio de vidéo IA TikTok)

> Refonte du front-end en vrai studio, piloté par une équipe d'agents.
> Une phase = livrable runnable + tests verts. Le lead intègre et commit.

## 1. Analyse de l'existant

- **`src/app.py`** : monolithe Streamlit 562 lignes, encore sur l'ANCIEN format
  monstres (prompt GPT inline, hands-FPS), modes Script/Video/Image/Voice vides,
  bugs latents (`asdict`/`log_terminal` non importés). Ne connaît PAS le format
  Aventure, l'image-first, `AdventureScript`, la voix conteur.
- **Backend déjà propre** (à réutiliser tel quel) : `pipeline.py`, `features/`
  (assets, transcription, compositing, scripting), `videospec/`. Tout le cerveau
  Aventure (phases P/S/P2) est prêt et testé (34 tests).
- **Persistance** : fichiers seulement (`exports/{project}/{instance}/metadata.json`).
  Pas de base de données, pas de suivi de jobs/coûts, pas de bibliothèque de voix
  en base (`assets/narrator_voice.json` isolé).

## 2. Vision — VCM Studio

Une app web soignée qui pilote le format Aventure de bout en bout :
**prompt → script éditable → assets (génération image-first, régen à l'unité,
draft/final) → montage → bibliothèque → publication**. Look studio TikTok :
sombre, dense, previews verticales 9:16, HUD de coût, barres de progression.

## 3. Stack décidée

- **Backend** : **FastAPI** (API REST/SSE) au-dessus du `pipeline`/`features`
  existants (Python, zéro réécriture du cerveau) + **jobs en arrière-plan**.
- **Base de données** : **SQLite via SQLModel** (SQLAlchemy + Pydantic). Les
  BLOBS (images/vidéos/audio) restent sur disque (`exports/`), la DB stocke les
  métadonnées + chemins (best practice : jamais de binaire en base).
- **Frontend** : **React + Vite + TypeScript + Tailwind + shadcn/ui** — le studio.
- Streamlit (`app.py`) devient legacy/fallback, non supprimé tant que le nouveau
  front ne couvre pas tout.

## 4. Modèle de données (où la DB est nécessaire)

| Table | Rôle |
|---|---|
| `Project` | un projet/chaîne (nom, date, réglages) |
| `Episode` | une vidéo Aventure (projet, statut, format, draft/final, durée, chemin final) |
| `AdventureScriptRow` | le script généré (JSON `AdventureScript` sérialisé + éditions) |
| `Asset` | chaque asset (épisode, beat, type image/video/audio, prompt, chemin local, statut, draft/final, hash) |
| `GenerationJob` | suivi d'une génération (asset, modèle Replicate, prediction id, statut, durée, erreur) |
| `VoiceProfile` | banque de voix (registre, description, voice_id, sample) — migre `narrator_voice.json` |
| `CostEntry` | journal de coût (job, modèle, secondes/images, montant estimé) |

Patterns : couche `repository` typée ; les jobs Replicate téléchargent l'asset
en local IMMÉDIATEMENT (règle « liens Replicate expirent »), la DB ne garde que
le chemin local + le `prediction id` (jamais l'URL périssable).

## 5. Architecture

```
React (Vite/TS/Tailwind/shadcn)  ──HTTP/SSE──>  FastAPI
                                                  ├── routes (episodes, script, assets, montage, library, voices, cost)
                                                  ├── services (orchestrent pipeline + features existants)
                                                  ├── jobs (background : génération image-first, montage)
                                                  └── db (SQLModel/SQLite) + repositories
exports/ (BLOBS sur disque) <── téléchargement immédiat des assets
```

## 6. UX/UI — les écrans

1. **Dashboard** : projets, épisodes récents, statuts, coût cumulé.
2. **New Episode (wizard)** : prompt de base → noms persos → génère le script.
3. **Script & Casting** : éditer l'`AdventureScript` (3 rounds, choix, voix),
   relancer un étage. Validation avant génération.
4. **Assets** : galerie par round → pour chaque beat, la **première frame
   (image)** + la **vidéo (image→vidéo)** ; **régénération à l'unité**, toggle
   draft/final, écoute audio, coût estimé AVANT lancement.
5. **Montage & Preview** : assemble (intro + rounds + épilogue), preview 9:16.
6. **Library** : toutes les vidéos produites, filtres, export/publication.

Design : thème sombre studio, previews 9:16 partout, barres de progression
(SSE), HUD coût, états de job en temps réel.

## 7. Phases

| Phase | Sujet | Statut |
|---|---|---|
| U0 | **DB** : SQLModel + SQLite, modèles + repositories + migration voices/exports. Tests. | ⬜ |
| U1 | **API FastAPI** : routes + services au-dessus du pipeline + jobs background + coût/SSE. Tests. | ⬜ |
| U2 | **Frontend React** : scaffold Vite/TS/Tailwind/shadcn + écrans (dashboard, wizard, script, assets, montage, library) câblés à l'API. | ⬜ |
| U3 | **Intégration & polish** : thème studio, previews 9:16, progress SSE, HUD coût, responsive. | ⬜ |

**Protocole** : par phase → tests/lint verts → démo → commit. Le golden intro et
les 34 tests Aventure ne cassent jamais (backend additif).

## 8. Équipe

- **lead** (moi) : coordination, intégration, revue, commits, garde-fou tests.
- **db-dev** : phase U0 (SQLModel/SQLite + repositories + migration).
- **api-dev** : phase U1 (FastAPI + services + jobs + coût) — dépend de U0.
- **front-dev** : phase U2 (React studio) — démarre en parallèle (contrat d'API
  défini), câble dès que U1 expose les routes.

## 9. Risques

- Scope énorme → livrer FONDATION runnable d'abord (DB+API solides), front v1
  fonctionnel ensuite, polish itéré. Mieux vaut un studio simple qui tourne
  qu'un beau front à moitié branché.
- Stack frontend nouvelle (TS/React) à côté du Python → contrat d'API clair en
  U1 pour découpler front et back.
- Node/build : si l'hôte n'a pas Node, le front se build dans le conteneur/CI ;
  l'API et la DB tournent indépendamment.
