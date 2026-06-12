# Refactor : procédural → feature-driven + ports (typing.Protocol)

> Feuille de route persistante entre sessions. **Une étape (−1 → 9) par session**, commit + diff contre le golden à chaque fois.

> **Changement de périmètre (2026-06-09)** : l'**upscale IA (Step 3)** a été retiré du projet — `ai_upscale`,
> Real-ESRGAN, `color_grade_tiktok` et `tiktok_final.mp4` n'existent plus. Le pipeline est désormais
> **Step 1 (assets) → Step 2 (compilation)**, `final_video.mp4` étant le livrable final. En conséquence,
> les **Étapes 1 (grading) et 2 (upscaling) du roadmap ci-dessous sont supprimées** (marquées ~~barrées~~).
> La numérotation des étapes restantes est conservée pour ne pas casser les références croisées (couture 4↔5,
> renvois vers l'étape 8, etc.).

## État d'avancement — POINT DE REPRISE

> **Pour reprendre :** en début de session, dire « reprends le refactor ». Lire ce tableau → la 1re ligne ⬜
> est la prochaine étape. Travailler sur la branche **`refactor/feature-driven`**. **Une seule étape par session.**
> Protocole par étape : (1) faire l'étape, (2) `mypy infra features pipeline.py` vert, (3) produire une vidéo
> Step 1→2 et `GOLDEN_CANDIDATE=<export> pytest tests/test_golden.py` vert (voir `tests/README.md`),
> (4) cocher la ligne ici + commit. Mettre à jour ce tableau à CHAQUE étape — c'est la source de vérité.

| Étape | Sujet | Statut | Commit |
|---|---|---|---|
| −1 | Gel du golden (oracle de caractérisation) | ✅ fait | `a9fa0c1` |
| — | Suppression upscale (Step 3) | ✅ fait | `a9fa0c1` |
| 0 | Scaffold paquets + infra (`log_terminal`/`download_file`/`save_key_to_env` → `infra/`) | ✅ fait | `fdf4eac` |
| ~~1~~ | ~~grading~~ — supprimée (upscale retiré) | ❌ N/A | |
| ~~2~~ | ~~upscaling + port `Upscaler`~~ — supprimée (upscale retiré) | ❌ N/A | |
| 3 | `features/transcription/` + `Transcriber` + types immuables | ✅ fait | `c75e37f` |
| 4 | `Overlay` Protocol + 4 overlays un par un + `srt.py` | ✅ fait | `fd6dea2` |
| 5 | `heads.py` + `HeadDetector` (port I/O) | ✅ fait | `aa8ce8b` |
| 6 | `compositor.py` (corps de `compile_video_raw`) | ✅ fait | `dde5ae6` |
| 7 | `features/assets/` + `AssetProvider` | ✅ fait | `73e15fe` |
| 8 | `pipeline.py` + sorties immuables (8a parallèle, 8b coupe le JSON) | ✅ fait | `2821f0f` |
| 9 | `app.py` = câblage seul + mypy `--strict` sur `app.py` | ✅ fait | `d4a2a41` |

**Prochaine étape : 0 — Scaffold + infra.**

## Contexte

`ViralCashMachine` est aujourd'hui procédural : toute la logique vit dans `app.py` (UI Streamlit + appels
Replicate/OpenAI + état) et `compiler.py` (rendu, sous-titres, détection dans un seul module).
Le graphe `graphify` a isolé deux **god nodes** qui concentrent le couplage :

- **`compile_video_raw()`** (`compiler.py:289`, 13 relations) : une fonction de ~100 lignes qui appelle en dur
  4 fabriques de clips (`_make_text_clip_exact`, `create_styled_subtitle_pil`, `create_circular_timer_pil`,
  `create_dark_fantasy_gauge`) + Whisper + détection de têtes. Toute la composition est inline.
- **`VideoInstance`** (`app.py:20`, dataclass mutable de 31 champs, centralité 0.304) : à la fois modèle
  d'édition UI **et** schéma de `metadata.json` (`asdict()` / `VideoInstance(**meta)`). Muté étape par étape ;
  `compile_video_raw` lit/réécrit `metadata.json` directement (`compiler.py:294,302`) — couplage par JSON.

**Objectif** : passer à une structure *feature-driven* (assets, transcription, compositing
+ `pipeline` + `app.py` = câblage seul), introduire des **ports `Protocol`** aux bonnes frontières, et remplacer
la mutation de `VideoInstance` par des **sorties d'étape immuables**. Migration **strangler-fig** : l'app reste
fonctionnelle à *chaque* commit. `mypy` doit passer sur le code nouveau/touché.

## Règle de décision pour les Protocol (cadrée avec l'utilisateur)

> Un Protocol se justifie s'il y a **(a)** plusieurs implémentations interchangeables, **ou** **(b)** un bord
> d'I/O qu'on veut simuler en test. Sinon : classe ou fonction concrète.

| Cible | Justification | Décision |
|---|---|---|
| `Overlay` (sous-titre, timer, jauge, nameplate) | (a) 4 impls | **Protocol** |
| `Transcriber` (Whisper/OpenAI) | (b) I/O | **Protocol** |
| `AssetProvider` (Replicate : voix/image/vidéo) | (b) I/O — frontière Replicate | **Protocol unique, 3 méthodes** |
| `HeadDetector` (Grounding DINO/Replicate) | (b) I/O | **Protocol** |
| étapes du pipeline | ordre fixe | **Pas de `Stage`** — séquence de fonctions |

> ~~`Upscaler` (Real-ESRGAN) et `grading` (`color_grade_tiktok`)~~ : retirés du projet avec le Step 3.

**Assets vérifié dans le code** (`app.py:446-458`) : voix `{text,voice_id}`, image `{prompt,size,aspect}`,
vidéo `{prompt,image,…}` — contrats *différents*, non interchangeables. Donc pas de polymorphisme, mais une
seule frontière I/O (Replicate) → **un** port `AssetProvider` regroupant les 3 méthodes (un seul fake en test).

**`VideoInstance`** : conservé comme DTO UI + schéma `metadata.json`. Les sorties immuables circulent *en interne*.
`metadata.json` inchangé → exports existants toujours chargeables. (Remplacement total écarté : casse la compat.)

## Structure cible (à la racine, `streamlit run app.py` inchangé)

```
infra/            logging.py · download.py · env.py        # helpers transverses (pas des features)
features/
  assets/         ports.py (AssetProvider, AssetBundle) · replicate_provider.py
  transcription/  ports.py (Transcriber, Cue, Transcription) · whisper.py
  compositing/    overlays.py (Overlay + 4 impls) · compositor.py · srt.py · heads.py (HeadDetector)
pipeline.py       séquence fixe : assets → compositing (fonctions, ports injectés)
app.py            UI Streamlit + câblage seul
```

Forme du port d'overlay (déduite de `compiler.py:317-382`) — chaque overlay est une frozen dataclass qui porte
ses params + `start`/`position`/`duration` ; le placement/timing reste sorti du Protocol :

```python
class Overlay(Protocol):
    def to_clip(self, canvas: tuple[int, int]) -> Clip: ...
```

Le compositeur ne fait plus que : `CompositeVideoClip([base, *[o.to_clip((w, h)) for o in overlays]])`.

## Séquencement strangler-fig (chaque étape = app fonctionnelle + mypy vert)

Ordre = « feature la plus isolée d'abord » puis « Protocol avant tout changement de comportement », overlays un
par un, `VideoInstance` en dernier.

**Étape −1 — Gel de la référence (test de caractérisation). ✅ FAIT (2026-06-09).** AVANT toute modif : figer un
export réel (Step 1 → 2) dans `tests/fixtures/golden/`. Réalisé en gelant l'export existant
`exports/default_project/20260609_183531` (vrai run Docker pré-refactor, donc zéro coût API) : `final_video.mp4`
+ `metadata.json` copiés, et `invariants.json` capturant les invariants diffables — durée (11.71s), nombre de
segments (4 : intro / hook / narration / choice via `segment_plan`), checksums des 4 frames-clés, et le
`metadata.json` complet (31 champs). Outillage : `tests/golden_tools.py` (probe/SSIM, ffmpeg+stdlib seuls),
`tests/capture_golden.py` (figer), `tests/test_golden.py` (comparer un candidat au golden). C'est l'oracle contre
lequel les étapes 0-9 se comparent — sans ce gel initial, la « comparaison à la référence » de la vérif #2 n'a pas
de point fixe.

**Étape 0 — Scaffold + infra.** Créer les paquets (`__init__.py`, `py.typed`), config mypy dans `pyproject`
(`strict` sur `infra/`+`features/`, tolérant sur `app.py` legacy). Déplacer `log_terminal`, `download_file`,
`save_key_to_env` (`app.py:61,89,105`) → `infra/`, ré-importer dans `app.py`. *Pur déplacement, zéro comportement.*

**~~Étape 1 — `features/grading/`~~ — SUPPRIMÉE.** `color_grade_tiktok` a été retiré du projet (faisait partie
du Step 3). Plus de feature `grading`.

**~~Étape 2 — `features/upscaling/` + port `Upscaler`~~ — SUPPRIMÉE.** `ai_upscale` / Real-ESRGAN ont été retirés
du projet. Plus de feature `upscaling`, plus de port `Upscaler`, plus de `tiktok_final.mp4`.

**Étape 3 — `features/transcription/` + `Transcriber` + types immuables.** Frozen `Cue(text,start,end)` et
`Transcription`. `Transcriber.transcribe(audio) -> tuple[Cue,...]`, impl `WhisperTranscriber`. **Dédupe** les deux
copies de `get_whisper_subtitles` (`compiler.py:18` + `app.py:67`). `compile_video_raw` reçoit un `Transcriber`
injecté. Premier endroit où les sous-titres deviennent typés/immuables (tremplin vers l'étape 8).

**Étape 4 — `Overlay` Protocol + overlays UN PAR UN.** Dans `features/compositing/overlays.py`, définir le
Protocol, puis migrer dans cet ordre (1 commit chacun, compositeur réécrit incrémentalement) :
- `NameplateOverlay` ← `_make_text_clip_exact` (la math de position depuis les head-coords reste dans le compositeur)
- `SubtitleOverlay` ← `create_styled_subtitle_pil`
- `TimerOverlay` ← `create_circular_timer_pil`
- `GaugeOverlay` ← `create_dark_fantasy_gauge`
À la fin, `compile_video_raw` itère `list[Overlay]` par segment. Sortir aussi `save_srt`/`format_timestamp`
→ `srt.py`. **Couture 4↔5** : `NameplateOverlay` consomme des coords *déjà résolues* (`pos: tuple[int,int]`),
jamais le `HeadDetector`. Définir cette signature dès l'étape 4 pour ne pas re-refactorer l'overlay quand le port
détection arrive à l'étape 5. **Note (dette assumée)** : le retour `Clip` fait fuiter MoviePy dans `compositing` —
acceptable (cette couche *est* un adaptateur MoviePy), mais c'est précisément la couture à neutraliser le jour d'un
backend ffmpeg/Rust ; le port pourrait alors rendre une repr neutre. Ne pas le faire maintenant, juste le tracer.

**Étape 5 — `heads.py` + `HeadDetector` (port I/O).** Déplacer `detect_side_entity`/`get_ai_head_positions_split`
(`compiler.py:125,150`) ; `HeadDetector.detect(image) -> HeadLayout`, impl Grounding DINO. Injecté dans le compositeur.

**Étape 6 — `compositor.py`.** Déplacer le corps de `compile_video_raw` → classe/fonction concrète (orchestration,
pas un bord I/O → **pas** de Protocol), prenant `Transcriber` + `HeadDetector` injectés.

**Étape 7 — `features/assets/` + `AssetProvider`.** Port à 3 méthodes (`synthesize_voice`/`generate_image`/
`animate_video`), impl `ReplicateAssetProvider` (corps de `app.py:443-459`), sortie frozen `AssetBundle`. Le bouton
Step 1 appelle le provider injecté. (Décompo GPT OpenAI = port séparé `ScriptDecomposer`, optionnel — à noter.)
**Tension ISP assumée** : le port à 3 méthodes force un consommateur « voix seule » à dépendre des 3, et le
`FakeAssetProvider` à stubber les 3. Défendable vu la frontière Replicate unique → on garde. Si un jour ces appels
deviennent vraiment indépendants, scinder en 3 ports étroits tous implémentés par `ReplicateAssetProvider`.

**Étape 8 — `pipeline.py` (séquence) + sorties immuables (VideoInstance EN DERNIER).** C'est le vrai morceau du
refactor (les étapes 0-7 sont surtout du déplacement + ports) — donc scindé en deux pour ne pas faire le saut risqué
d'un coup :

- **8a — sorties immuables EN PARALLÈLE de l'existant.** Introduire frozen `AssetBundle`, `Transcription`,
  `HeadLayout`, `CompiledVideo` comme valeurs de retour des étapes, *sans* couper l'écriture JSON actuelle. Chaque
  étape produit son immutable ET continue de muter `VideoInstance`/`metadata.json` comme avant. Asserter l'égalité
  (le `HeadLayout` retourné == ce qui est écrit dans `metadata.json`) → on prouve que les nouveaux contrats sont corrects.
- **8b — couper l'effet de bord (lecture ET écriture).** Une fois l'égalité vérifiée, supprimer l'écriture directe
  de `metadata.json` dans le compositeur (`compiler.py:300-302`) **et aussi la lecture directe** (`compiler.py:294`,
  `meta = json.load(f)`) : le compositeur reçoit désormais ses entrées **par paramètres** (les immutables des étapes
  amont), il ne relit plus le disque. Le `HeadLayout` retourné est persisté par `app.py` au niveau câblage.
  `pipeline.produce(...)` enchaîne les fonctions d'étape dans l'ordre fixe, ports injectés, en passant les immutables
  d'une étape à l'autre. Couper l'écriture sans couper la lecture laisserait le couplage JSON à moitié — les deux
  partent ensemble. Disparition de l'arête INFERRED `shares_data_with` du god node.

`VideoInstance` reste le DTO UI/persistance ; `metadata.json` inchangé (toujours `asdict(VideoInstance)`).

**Étape 9 — `app.py` = câblage seul.** `app.py` construit les impls concrètes, les passe au `pipeline`. Le sync
widgets ↔ `VideoInstance` (`app.py:124,141`) reste (préoccupation UI). **Réflexe Streamlit** : le script est
réexécuté à chaque interaction → construire `ReplicateAssetProvider`/`WhisperTranscriber`/etc. en tête de script les
recrée à chaque rerun. Les envelopper dans `@st.cache_resource` (factory de ports) pour qu'elles persistent. À
vérifier sur le code actuel au moment de réduire `app.py` au câblage.

## Fichiers clés touchés

- `app.py` — extraction infra (ét. 0), boutons Step 1/2/3 → appels de ports injectés (ét. 2,4,7), réduction à câblage (ét. 9)
- `compiler.py` — vidé progressivement vers `features/` ; supprimé/transformé en shims puis retiré (ét. 1-6)
- Nouveaux : `infra/*`, `features/*/ports.py` + impls, `pipeline.py`, `pyproject` (config mypy)

## Vérification

1. **mypy** : `mypy infra features pipeline.py` vert à chaque étape ; legacy `app.py` toléré au début mais
   `--strict` sur `app.py` **doit** réellement arriver à l'étape 9 (non-négociable, pas perpétuellement repoussé) —
   `app.py` concentre tout le câblage, donc l'endroit le plus exposé aux erreurs d'injection (mauvaise impl → port).
2. **Comportement** : après chaque étape, `streamlit run app.py` et produire une vidéo de bout en bout
   (Step 1 → 2) ; differ `final_video.mp4` / `metadata.json` contre le **golden gelé à l'étape −1**
   (durée, nb de segments, checksums frames-clés, SSIM). Tout écart = régression à expliquer avant de continuer.
3. **Compat données** : recharger un `metadata.json` d'un export *antérieur* au refactor → doit s'ouvrir sans erreur (schéma inchangé).
4. **Tests** (rendus possibles par les ports) : `pytest` avec `FakeTranscriber`/`FakeAssetProvider`/
   `FakeHeadDetector` — la suite unitaire ne tape jamais Replicate/OpenAI ni ffmpeg lourd.
5. **Graphe** : `graphify update .` en fin de parcours — vérifier que `compile_video_raw`/`VideoInstance` ne sont
   plus des god nodes (degré/centralité en baisse, `Overlay` comme nouveau hub de communauté compositing).
