# REFONTE v7 — pipeline « fil rouge » (cohérence + sens + uniformité)

> ⚠️ **ARCHIVE — supersédé par [`ROADMAP.md`](ROADMAP.md).** Le format Aventure (script,
> voix) est intégré au rail unique ; l'image-first restant est la R4 du ROADMAP.
> Conservé pour l'historique.

> Remodelage demandé après le 1er épisode complet. Objectif : une vidéo qui a
> du SENS de bout en bout, une DA et un personnage UNIFORMES, un montage propre
> par la VITESSE (jamais d'allongement). Une phase par session, tests verts.

## Analyse de l'existant (état au 1er épisode complet)

Ce qui marche : génération image-first réelle (Replicate), voix conteur clonée,
montage MoviePy (timers/sous-titres), intro via le système historique
(`intro.py`), studio connecté (DB+API+front).

Ce qui cloche (demandes auteur) :
1. **Intro pauvre** : un seul perso « parle » (clip unique), pas angoissant, pas
   personnalisé. Manque : les DEUX persos parlent, chacun tente de convaincre
   (« choisis-moi » / « ne me choisis pas… »), dit son NOM, s'approche lentement
   en restant cadré ; + un texte qui introduit le CARACTÈRE de chaque perso.
2. **Transition d'issue manquante** : avant de décrire ce qui se passe, le
   narrateur doit dire « Si tu as choisi X… » AVEC un ZOOM sur le côté du perso
   énuméré.
3. **Timing par allongement (à remplacer)** : on prolongeait avec la photo →
   désormais on joue sur la VITESSE. Narration trop longue → accélérer la
   narration. Vidéo trop longue → accélérer la vidéo. JAMAIS allonger/figer.
4. **DA/perso non uniformes** : chaque image est générée indépendamment → le
   perso et le décor dérivent. Il faut une RÉFÉRENCE : cropper le perso choisi
   (modèle de vision / split, sur fond uni) et générer toutes les images en
   image-to-image (réf perso + décor décrit) → même perso, même DA partout.
5. **Sens / langage** : les descriptions doivent être en mots SIMPLES et
   courants ; parfois la narration n'a pas de sens. Besoin d'un FIL ROUGE
   cohérent du début à la fin.
6. **Ordre de génération** : générer d'abord TOUS les textes (narration,
   répliques, actions, environnement) cohérents, PUIS les visuels en CHAÎNANT :
   photo → vidéo, puis récupérer la DERNIÈRE FRAME de la vidéo pour faire la
   suivante, et ainsi de suite (continuité visuelle).

## Pipeline remodelé — génération en 3 temps

```
1) TEXTE (1 passe LLM cohérente, langage simple, fil rouge)
   → script complet : intro (2 persos : nom + caractère + réplique angoissante),
     rounds (action/environnement/réplique/choix/issues), lignes narrateur
     « si tu as choisi X ». Tout se tient, mots courants.

2) RÉFÉRENCE PERSONNAGE (ancre d'uniformité)
   → générer les 2 persos, cropper chacun sur FOND UNI (modèle de vision /
     split Grounding DINO) = réf canonique. Le perso suivi devient l'ancre.

3) VISUELS CHAÎNÉS (fil rouge visuel)
   → 1re image = perso (réf) dans la scène d'ouverture (image-to-image : réf +
     décor décrit). image→vidéo. Puis DERNIÈRE FRAME de la vidéo = base de la
     vidéo suivante (continuité), en réinjectant la réf perso + le nouveau
     décor. Chaînage sur toute l'aventure → DA + perso uniformes.
```

## Montage remodelé (vitesse, jamais allongement)

- Caler durée d'un plan sur la parole en **accélérant** : `atempo` sur l'audio
  narration si trop longue, `speed`/setpts sur la vidéo si trop longue. Jamais
  de figeage/photo de remplissage.
- **« Si tu as choisi X »** : ZOOM sur le côté de X (depuis l'image intro 2
  persos ou la réf) juste avant l'issue.
- **Intro** : les 2 persos parlent (clips séparés, angoissant, nom prononcé,
  approche lente cadrée), overlay nom + texte de caractère, puis timer de choix.

## Contrat de création (front dashboard — ce que le créateur saisit)

Le wizard « New Episode » doit présenter CLAIREMENT 3 blocs :
1. **L'aventure** (`prompt`, requis) — 1-3 phrases : décor + danger. Aide :
   « une descente dans une mine inondée qui s'effondre ».
2. **Personnage A** : `char_left_name` (requis, prénom FR) + `char_left_desc`
   (optionnel, ~200 car., apparence concrète + caractère). Placeholder :
   « homme maigre, veste de mineur trempée, regard fuyant, calme ».
3. **Personnage B** : idem (`char_right_name` + `char_right_desc`).

Garde-fous à afficher : description COURTE et visuelle (nourrit l'image de réf
R2) ; si vide → l'IA invente ; tu écris en français, l'IA traduit l'apparence en
EN ; la voix est auto-générée (2 voix contrastées). Backend prêt : route
`POST /api/episodes/{id}/script` accepte `{prompt, char_left_name, char_right_name,
char_left_desc, char_right_desc}` (commit `c0255b9`).

## Phases de la refonte

| Phase | Sujet | Statut | Commit |
|---|---|---|---|
| R1 | **Script v2** : LLM langage simple (règle 8) + fil rouge (règle 9) ; schéma + `char_*_personality_fr` + `char_*_intro_line_fr` (dit son nom, angoissant). Fake + tests + schéma régénéré. 58 passed. | ✅ fait | `7df3ed8` |
| R2 | **Référence perso** ✅ : pivot validé — seedream-4.5 `image_input` garde le même perso + DA. Réf perso (fond uni) en tête du plan, passée en image_input à toutes les images. `generate_image(+image_input)`. Tests verts (23 img/56 assets). | ✅ fait | `ca14014` |
| R3 | **Génération chaînée** ✅ : dernière frame de la vidéo N (ffmpeg + upload) → image_input de la frame N+1, en plus de la réf perso. Mapping timeline (action←survie-1, env←action, char←env, fatal/survival←char). Best-effort (repli R2). 58 passed. | ✅ fait | `77d32f8` |
| R4 | **Montage vitesse + zoom + intro 2 voix** ✅ : R4a vitesse (narration/vidéo même durée, `6233f59`) ; R4b zoom « si tu as choisi X » sur le choix (`12d671c`) ; R4c intro 2 persos parlent + caractère via narration (`f28beaf`). Golden intact, 58 passed. | ✅ fait | `f28beaf` |
| R5 | **Orchestration + test bout-en-bout** ✅ : route `/produce` (assets+intro+montage, R5a) ; contrat créateur (décrire les 2 persos) ; 1re vraie génération GPT (train-grotte, Louis tête d'horloge / Pierre tête de lune) → final 100s. UI (mosaïque/wizard/2 modes) = repris dans STUDIO_V2_PLAN.md. | ✅ fait | `f1ca634` |

**Refonte v7 TERMINÉE (R1→R5).** Prochaines pistes : (a) réglage prompts —
plans d'aventure plus rapprochés/clairs sur le perso ; (b) front « refonte v7 »
puis Studio v2 (templates + UX SaaS) → voir STUDIO_V2_PLAN.md.

## Paliers de modèles choisis (recherchés via le MCP Replicate — prix exacts à
confirmer sur les pages modèles en phase B)
- **Image / référence** : draft `bytedance/seedream-4.5` (2K) · value `seedream-4.5`
  + `google/nano-banana` (édition par référence) · premium `black-forest-labs/flux-2-pro`
  (8 images de référence) ou `google/nano-banana-pro`.
- **Image→vidéo** : draft `prunaai/p-video` (draft) · value `p-video` / `bytedance/seedance-1-lite`
  · premium `kwaivgi/kling-v2.5-turbo-pro` / `bytedance/seedance-1.5-pro` (audio) /
  `google/veo-3.1-fast` (support last-frame → chaînage R3).
- **Voix** : draft `jaaari/kokoro-82m` · value+premium **conteur cloné**
  `minimax/speech-02-hd` (signature de la chaîne).

## Risques / points à valider
- **Image-to-image seedream** (R2) : à confirmer (sinon modèle de référence
  alternatif, ex. un modèle de cohérence de personnage). C'est le pivot de
  l'uniformité — à valider EN PREMIER dans R2.
- **Chaînage dernière-frame** (R3) : séquentiel (pas de parallélisme), plus lent ;
  risque de dérive cumulée → la réf perso recadre à chaque étape.
- **Accélération** (R4) : garder l'audio intelligible (atempo ≤ ~1.3x) ; au-delà,
  raccourcir le texte plutôt (boucle qualité).

---

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

## Doctrine POV/FPS immersif (décision auteur après 1er montage test)

Le format n'est PAS du b-roll illustratif : c'est une **immersion POV/FPS** où le
spectateur EST quelqu'un qui suit le protagoniste.

1. **POV first-person partout** (vidéo ET photo) : nos mains visibles en bas du
   cadre, comme un jeu FPS / comme l'intro.
2. **Le protagoniste est TOUJOURS dans le cadre** : de dos quand il marche devant
   nous (on le suit), de face quand il s'arrête pour nous parler.
3. **Une seule DA, cohérente de l'intro jusqu'à la fin** : horreur cinématique
   photoréaliste, palette froide désaturée, ombres profondes, torche unique,
   grain. Tout asset partage ce bloc DA (constante `DA` dans prompts.py).
4. **Descriptions vidéo = ce qu'on VOIT**, riche et immersif (l'action POV, le
   décor, la lumière), PAS un écho du dialogue. Plus de contexte que de paroles.
5. **Le personnage annonce les choix lui-même**, à SA manière (selon son
   caractère), en s'adressant à nous (« tu préfères ça, suis-moi, ou tu pars »),
   en caractérisant chaque option, et en nous STRESSANT (« choisis vite, t'as
   pas vraiment le choix »). Il ne dit jamais « qu'est-ce que je fais ».
6. **Zéro silence** : la durée de chaque plan se cale sur la parole (narration ou
   réplique). Le montage trime le clip à la longueur de l'audio + court tail.
7. **Immersion réelle** : caméra POV en mouvement avant pour l'action (pas de
   plan fixe « carte postale »), mains qui bougent. Plan fixe seulement quand le
   perso s'arrête face caméra.

## Méthodologie « image-first » (décision auteur après les tests POV)

### Analyse — pourquoi le texte→vidéo seul échoue
Tout le contrôle (look + mouvement + dialogue) entassé dans UN prompt
texte→vidéo → le modèle improvise le mouvement (le perso court au lieu de
suivre tranquille) et la fidélité visuelle est aléatoire. Diagnostic confirmé
sur `aventure-test-pov` : POV/mains/DA OK, mais le MOUVEMENT ne correspond pas.

### Le principe (best practice de la vidéo IA)
**Génération en 2 temps, séparation look / mouvement :**
1. **Première frame = IMAGE** (seedream, texte→image) : décrit TOUT le visuel —
   cadrage POV, perso (apparence, pose, expression), mains au bord du cadre,
   décor, lumière, DA, composition. C'est ici que vit 100 % du contrôle visuel.
2. **Vidéo = image→vidéo** (p-video avec l'image en première frame) : le prompt
   ne décrit QUE le MOUVEMENT (avec sa VITESSE/intensité) + ce qui est DIT.
   Rien d'autre — le look est déjà verrouillé par l'image.

**RÈGLE : toute vidéo a TOUJOURS sa première-frame image générée d'abord.**

### Règles de prompt engineering (encodées dans prompts.py)
- **Image (first frame)** : ordonnée, dense, tout le visuel. Structure :
  [cadrage POV] + [perso : apparence, pose, expression] + [mains POV] +
  [décor] + [lumière] + [DA] + [mots-clés de composition]. Front-load
  l'important. Réutilise la constante `DA` (cohérence).
- **Vidéo (motion)** : minimal. [Qui bouge + COMMENT, avec la vitesse :
  « calm, steady, unhurried » vs « sudden, violent »] + [dialogue : manière
  puis réplique exacte] + [comportement caméra]. Jamais de re-description du
  look. La VITESSE explicite corrige le « court au lieu de marcher ».
- **Cohérence inter-vidéos** : la première frame peut elle-même être seedée
  depuis une référence perso (image→image) pour stabiliser le visage/tenue.

### Impact technique
- `prompts.py` : pour chaque plan vidéo, DEUX builders — `frame_*()` (image
  riche) et `motion_*()` (mouvement + dialogue minimal). Les images de choix
  restent de simples images riches.
- Schéma `AdventureScript` : champs déjà séparables — atomes VISUELS
  (`environment_desc`, `danger_desc`, `image_desc`, `char_*_desc`) nourrissent
  les `frame_*`, atomes MOUVEMENT (`action_desc`, `fatal_kill_desc`,
  `survival_outcome_desc`, `character_line_fr`) nourrissent les `motion_*`.
  Les contenus de mouvement portent désormais la VITESSE (calme par défaut).
- Step 1 (phase A) : par plan vidéo → générer l'image, puis image→vidéo.

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
| P | **Prompts + voix narrateur** : ① `prompts.py` ✅ (templates + 7 règles d'or, 6 tests verts). ② Voix narrateur ✅ — **LE CONTEUR cloné**, `voice_id=R8_3HPKBKXB`, modèle TTS `speech-02-hd`, fiche `assets/narrator_voice.json`, test réutilisable OK (`conteur-clone-TEST.mp3`). Procédé retenu : concaténer ~27 s de parole (3 clips) → data URI `audio/mpeg` → `minimax/voice-cloning model=speech-02-hd`. ③ Cohérence persos : `coherence-1/2/3.mp3`, **verdict auteur en attente** (non bloquant). | ✅ fait | `7dcb7a6` |
| S | **Script d'aventure** ✅ (équipe phase-s-script) : `adventure.py` (schéma Pydantic AdventureScript, validators 3 rounds/2 choix/1 fatal), port `AdventureDecomposer`, `openai_adventure_decomposer.py` (structured output + validation + retry, 7 règles d'or, narrateur non généré), `fake_adventure_decomposer.py` (offline grotte/mine), `adventure_to_prompts.py` (mapping pur champ→slot), `schemas/adventure.schema.json`, +17 tests. Suite : 33 passed. | ✅ fait | `2916292` |
| A | **Step 1 étendu** : génération des assets de rounds — images (seedream) + clips face-cam (p-video audio natif) + audios narrateur (TTS voice_id cloné). Parallélisé. Flag `draft` global. Manifest d'assets par instance. Estimation de coût AVANT lancement. | ⬜ à faire | |
| M | **Step 2 étendu** : nouveaux constructeurs de segments dans le compositor — la plupart réutilisent la brique narration existante (photo + zoom + audio + subs Whisper) ; face-cam + subs ; écran de choix A/B (overlays) ; timer existant. Timeline complète intro + 3 rounds + épilogue. Golden intro inchangé. | ⬜ à faire | |
| U | **Streamlit max** : onglets (① Script & voix éditables avant génération, ② Assets — galerie par round, régénération à l'unité, écoute par asset, toggle draft/final, ③ Montage & preview, ④ Bibliothèque). Barres de progression, coût estimé, état de projet persistant. | ⬜ à faire | |

**Prochaine étape : Phase P2 — méthodologie image-first dans prompts.py + preuve d'un plan, PUIS Phase A.**

| Phase | Sujet | Statut | Commit |
|---|---|---|---|
| P2 | **Image-first** : `prompts.py` scindé en `frame_*()` (image riche, tout le visuel) + `motion_*()` (mouvement+dialogue minimal, avec vitesse) ; contenus mouvement avec pace calme ; tests ; preuve = 1 plan généré image→vidéo (mouvement contrôlé). | ⬜ à faire | |

## Protocole par phase

1. Implémenter la phase. 2. `pytest tests/` vert (le golden intro ne doit JAMAIS
casser). 3. Démo concrète à l'auteur (écouter les voix / lire un script généré /
voir les assets / regarder le montage). 4. Cocher le tableau + commit.

## Acquis techniques des tests réels (ne pas re-découvrir)

- **RÈGLE ABSOLUE — les liens Replicate expirent.** On ne stocke et on ne
  réutilise JAMAIS une URL `replicate.delivery` comme référence. Tout asset
  (image, clip, audio, preview) est **téléchargé en local immédiatement** après
  génération, et seul le chemin local est conservé. La seule référence durable
  qu'on garde est le `voice_id` du clone (ça, ça ne périme pas). Tout le reste =
  fichier sur disque. Vaut pour Step 1, le montage, et tout script de test.
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
