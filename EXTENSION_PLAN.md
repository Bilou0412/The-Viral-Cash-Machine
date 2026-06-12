# Plan d'extension — « L'Aventure » (format complet 3 rounds)

> Extension du template intro existant vers le format complet : intro → choix du
> personnage → 3 rounds d'aventure à dilemmes → épilogue de l'autre branche.
> Une phase par session, tests verts à chaque étape, commit + cocher le tableau.
> **Mode draft obligatoire pour tous les essais.**

## Format final de la vidéo (validé avec l'auteur)

```
INTRO (existant, inchangé)        eye-open → dialogue 2 persos → narration → TIMER
                                  « Choisis ton personnage »
TRANSITION          [VIDÉO]       Narrateur : « Si tu as choisi Étienne... » —
                                  la ligne peut se poser sur le début de l'action
ROUND 1..3 (le chemin suivi = happy path : on survit)
  a. ACTION         [VIDÉO]       le perso avance (grotte, château, échelle...) —
                                  séquence immersive, narrée par-dessus
  b. ENVIRONNEMENT  [VIDÉO]       hostile par nature (pierres suspendues, lave,
                                  structures instables) — narré par-dessus
  c. LE PERSO PARLE [VIDÉO]       face caméra, manière décrite (chuchote, murmure,
                                  susurre...) : pose son dilemme — voix native p-video
  d. NARRATEUR      [2 PHOTOS+ZOOM] énonce les deux choix — DEUX images qui se
                                  succèdent, une par choix, chacune illustrant
                                  son option pendant que le narrateur l'énonce.
                                  Le seul segment photo du format.
  e. TIMER 3-2-1    [brique]      existante — un des deux choix est fatal
  f. ISSUE FATALE   [VIDÉO]       « Si tu as choisi [A]... » la mort en mouvement,
                                  angoissante, POV (ce qu'il te fait, comment tu réagis)
  g. ISSUE SURVIE   [VIDÉO]       « Si tu as choisi [B]... » — on continue
ÉPILOGUE            [VIDÉO]       « Si tu avais choisi [l'autre perso]... »
Durée cible : ~2 min – 2 min 30. Rounds 2-3 enchaînent depuis l'issue survie.
Les deux issues de chaque round sont montrées l'une après l'autre.
```

**Répartition photo/vidéo (décision auteur)** : TOUT est vidéo en séquences
(immersion), avec UNE seule exception — l'écran des choix (photo + zoom Ken
Burns, brique narration existante) : la pause dramatique avant le timer.
→ Par vidéo complète : **~16-17 clips vidéo** (intro + 3×5 + épilogue) +
**6 images** (3 rounds × 2 choix : une image par option, en succession).
**Audio des séquences narrées** : la voix narrateur (TTS clonée) se MIXE
par-dessus l'ambiance native du clip (volume ambiance baissé).

## Doctrine voix (hybride — décision auteur)

**Le narrateur : une voix générée UNE FOIS, puis clonée — la signature de la chaîne.**
- Audition : p-video génère des candidats de voix narrateur décrits au prompt
  (clips courts jetables), l'auteur choisit à l'oreille.
- Clonage : `minimax/voice-cloning` (⚠️ `model` ∈ {speech-2.6-turbo, speech-2.6-hd,
  speech-02-turbo, speech-02-hd}) → `voice_id` permanent stocké dans
  `assets/narrator_voice.json` (+ le sample wav archivé).
- Toutes les lignes narrateur = TTS minimax avec CE voice_id, posées sur les
  photos+zoom. Cohérence totale sur les ~12 lignes par vidéo, et d'une vidéo à
  l'autre (identité de chaîne).

**Les personnages : voix natives p-video, uniquement sur leurs clips face-cam.**
- Le script GPT génère une description de voix par perso, courte et distinctive.
- Description réinjectée VERBATIM dans chaque prompt de clip du même perso
  (~3-4 clips par vidéo) : cohérence best-effort à valider en phase P.
- Bonus : ambiance sonore native cohérente sur les face-cam.

Les sous-titres restent Whisper (transcription des audios finaux, mot à mot).

## L'enjeu n°1 : les prompts (décision auteur — « optimiser un maximum sans diluer »)

Tout le système repose sur le fait que les instructions des prompts sont
RESPECTÉES : voix, dialogue exact, caméra statique, style, absence de texte.
Les prompts sont un **composant à part entière**, centralisé, versionné, testé.

Règles d'or acquises en tests réels (à encoder dans les templates) :
1. **Une ligne = une contrainte fonctionnelle.** Court et dense > long et dilué
   (le modèle dilue son attention sur les pavés).
2. **Dialogue exact entre guillemets**, manière de dire AVANT la réplique
   (« says in French, whispering: "..." »). Répliques COURTES (moins de paraphrase).
3. **Description de voix verbatim** — jamais reformulée d'un clip à l'autre.
4. **Ne jamais mentionner ce qu'on ne veut PAS voir** (nommer un objet = le
   faire apparaître). Formuler en positif.
5. **Jamais de texte demandé à l'image** (charabia garanti) — tout texte réel
   vient des briques overlay au montage.
6. Caméra statique : bloc anti-dérive existant, conservé tel quel.
7. Visuels EN, dialogues FR (règle projet existante).

## État d'avancement — POINT DE REPRISE

| Phase | Sujet | Statut | Commit |
|---|---|---|---|
| P | **Prompts + voix narrateur** : ① module `src/features/scripting/prompts.py` — templates à slots par type d'asset (image action/environnement/choix/issues/épilogue, clip face-cam dilemme) + blocs réutilisables (voix verbatim, caméra statique, style). ② Voix narrateur : audition p-video → choix auteur → clonage → `assets/narrator_voice.json`. ③ Test de cohérence : 2-3 clips face-cam d'un même perso, validation à l'oreille. | ⬜ à faire | |
| S | **Script d'aventure** : structured output GPT — `AdventureScript` Pydantic (3 rounds : action, environnement, réplique perso + manière de dire, 2 choix, issue fatale, issue survie, lignes narrateur ; épilogue ; descriptions de voix des 2 persos). Extension du port `ScriptDecomposer`. Le script remplit les slots des templates P. | ⬜ à faire | |
| A | **Step 1 étendu** : génération des assets de rounds — images (seedream) + clips face-cam (p-video audio natif) + audios narrateur (TTS voice_id cloné). Parallélisé. Flag `draft` global. Manifest d'assets par instance. Estimation de coût AVANT lancement. | ⬜ à faire | |
| M | **Step 2 étendu** : nouveaux constructeurs de segments dans le compositor — la plupart réutilisent la brique narration existante (photo + zoom + audio + subs Whisper) ; face-cam + subs ; écran de choix A/B (overlays) ; timer existant. Timeline complète intro + 3 rounds + épilogue. Golden intro inchangé. | ⬜ à faire | |
| U | **Streamlit max** : onglets (① Script & voix éditables avant génération, ② Assets — galerie par round, régénération à l'unité, écoute par asset, toggle draft/final, ③ Montage & preview, ④ Bibliothèque). Barres de progression, coût estimé, état de projet persistant. | ⬜ à faire | |

**Prochaine étape : Phase P — prompts + voix narrateur.**

## Protocole par phase

1. Implémenter la phase. 2. `pytest tests/` vert (le golden intro ne doit JAMAIS
casser). 3. Démo concrète à l'auteur (écouter les voix / lire un script généré /
voir les assets / regarder le montage). 4. Cocher le tableau + commit.

## Acquis techniques des tests réels (ne pas re-découvrir)

- seedream : `size` ∈ {2K, 4K, custom} ; jamais de texte dans l'image.
- p-video : `resolution` ∈ {720p, 1080p} ; `duration` se cale sur l'audio fourni,
  sinon sur le paramètre ; `save_audio: true` pour l'audio natif.
- minimax/voice-cloning : `voice_file` requis ; `model` ∈ {speech-2.6-turbo,
  speech-2.6-hd, speech-02-turbo, speech-02-hd}.
- API en HTTP direct (package `replicate` absent de l'hôte, token `.env`).
- Upload de fichiers locaux : Files API (`/v1/files`, multipart) → URL signée.

## Risques identifiés

- **Cohérence vocale des persos inter-clips** (~3-4 face-cam par perso) :
  best-effort via description verbatim — à VALIDER en phase P ; repli : réduire
  à 1 réplique face-cam par round.
- **Paraphrase du dialogue natif** : répliques courtes + écoute par clip dans
  l'UI + régénération à l'unité.
- **Qualité du clone narrateur** : le sample d'audition doit être propre
  (voix seule, sans ambiance) — prompt d'audition « no background music,
  no ambient sound » à tester ; sinon nettoyage ffmpeg avant clonage.
- **Coût par vidéo complète** : ~16-17 clips p-video + 6 images → le mode
  draft est OBLIGATOIRE pour les essais ; rendu final uniquement après
  validation du script et des assets dans l'UI. Estimation affichée avant
  chaque lancement (phase A). C'est le poste de coût n°1 du format.
- **Mixage narration/ambiance** sur les clips d'action : équilibre des volumes
  à régler en phase M (la voix doit toujours dominer).
