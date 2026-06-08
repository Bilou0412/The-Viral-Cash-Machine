# Refactor : procédural → feature-driven + ports (typing.Protocol)

> Feuille de route persistante entre sessions. **Une étape (−1 → 9) par session**, commit + diff contre le golden à chaque fois.

## Contexte

`ViralCashMachine` est aujourd'hui procédural : toute la logique vit dans `app.py` (UI Streamlit + appels
Replicate/OpenAI + état) et `compiler.py` (rendu, sous-titres, détection, upscale, grading dans un seul module).
Le graphe `graphify` a isolé deux **god nodes** qui concentrent le couplage :

- **`compile_video_raw()`** (`compiler.py:289`, 13 relations) : une fonction de ~100 lignes qui appelle en dur
  4 fabriques de clips (`_make_text_clip_exact`, `create_styled_subtitle_pil`, `create_circular_timer_pil`,
  `create_dark_fantasy_gauge`) + Whisper + détection de têtes. Toute la composition est inline.
- **`VideoInstance`** (`app.py:20`, dataclass mutable de 31 champs, centralité 0.304) : à la fois modèle
  d'édition UI **et** schéma de `metadata.json` (`asdict()` / `VideoInstance(**meta)`). Muté étape par étape ;
  `compile_video_raw` lit/réécrit `metadata.json` directement (`compiler.py:294,302`) — couplage par JSON.

**Objectif** : passer à une structure *feature-driven* (assets, transcription, compositing, upscaling, grading
+ `pipeline` + `app.py` = câblage seul), introduire des **ports `Protocol`** aux bonnes frontières, et remplacer
la mutation de `VideoInstance` par des **sorties d'étape immuables**. Migration **strangler-fig** : l'app reste
fonctionnelle à *chaque* commit. `mypy` doit passer sur le code nouveau/touché.

## Règle de décision pour les Protocol (cadrée avec l'utilisateur)

> Un Protocol se justifie s'il y a **(a)** plusieurs implémentations interchangeables, **ou** **(b)** un bord
> d'I/O qu'on veut simuler en test. Sinon : classe ou fonction concrète.

| Cible | Justification | Décision |
|---|---|---|
| `Overlay` (sous-titre, timer, jauge, nameplate) | (a) 4 impls | **Protocol** |
| `Upscaler` (Real-ESRGAN, binaire lourd) | (b) I/O | **Protocol** |
| `Transcriber` (Whisper/OpenAI) | (b) I/O | **Protocol** |
| `AssetProvider` (Replicate : voix/image/vidéo) | (b) I/O — frontière Replicate | **Protocol unique, 3 méthodes** |
| `HeadDetector` (Grounding DINO/Replicate) | (b) I/O | **Protocol** |
| `grading` (`color_grade_tiktok`, transfo pure) | ni (a) ni (b) | **Fonction concrète** |
| étapes du pipeline | ordre fixe | **Pas de `Stage`** — séquence de fonctions |

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
  upscaling/      ports.py (Upscaler) · realesrgan.py
  grading/        grading.py                                # fonction, pas de Protocol
pipeline.py       séquence fixe : assets → compositing → upscale → grade (fonctions, ports injectés)
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

**Étape −1 — Gel de la référence (test de caractérisation).** AVANT toute modif : produire une vidéo complète
(Step 1 → 2 → 3) sur un projet réel, puis **figer** `final_video.mp4`, `tiktok_final.mp4` et leur `metadata.json`
dans `tests/fixtures/golden/`. Capturer des invariants diffables : durée, nombre de segments, checksums de quelques
frames-clés (intro / hook / narration / choice), et le `metadata.json` complet. C'est l'oracle contre lequel les
étapes 0-9 se comparent — sans ce gel initial, la « comparaison à la référence » de la vérif #2 n'a pas de point fixe.

**Étape 0 — Scaffold + infra.** Créer les paquets (`__init__.py`, `py.typed`), config mypy dans `pyproject`
(`strict` sur `infra/`+`features/`, tolérant sur `app.py` legacy). Déplacer `log_terminal`, `download_file`,
`save_key_to_env` (`app.py:61,89,105`) → `infra/`, ré-importer dans `app.py`. *Pur déplacement, zéro comportement.*

**Étape 1 — `features/grading/` (concret, pas de Protocol).** Déplacer `color_grade_tiktok` (`compiler.py:235`).
Le cas le plus net : transfo pure, isolé, aucune abstraction. Valide la mécanique de découpe.

**Étape 2 — `features/upscaling/` + 1er port I/O `Upscaler`.** Définir `Upscaler` (`upscale(src, dst, scale=2)
-> Path`) ; `RealEsrganUpscaler` = corps actuel de `ai_upscale` (`compiler.py:178`). Le bouton Step 3 d'`app.py`
appelle un `Upscaler` injecté (défaut `RealEsrganUpscaler()`). Comportement identique, `FakeUpscaler` possible en test.

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
   (Step 1 → 2 → 3) ; differ `final_video.mp4` / `tiktok_final.mp4` / `metadata.json` contre le **golden gelé à
   l'étape −1** (durée, nb de segments, checksums frames-clés). Tout écart = régression à expliquer avant de continuer.
3. **Compat données** : recharger un `metadata.json` d'un export *antérieur* au refactor → doit s'ouvrir sans erreur (schéma inchangé).
4. **Tests** (rendus possibles par les ports) : `pytest` avec `FakeUpscaler`/`FakeTranscriber`/`FakeAssetProvider`/
   `FakeHeadDetector` — la suite unitaire ne tape jamais Replicate/OpenAI, ni GPU, ni ffmpeg lourd.
5. **Graphe** : `graphify update .` en fin de parcours — vérifier que `compile_video_raw`/`VideoInstance` ne sont
   plus des god nodes (degré/centralité en baisse, `Overlay` comme nouveau hub de communauté compositing).
