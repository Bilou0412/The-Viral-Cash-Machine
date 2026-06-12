# Plan d'extension — « L'Aventure » (format complet 3 rounds)

> Extension du template intro existant vers le format complet : intro → choix du
> personnage → 3 rounds d'aventure à dilemmes → épilogue de l'autre branche.
> Une phase par session, tests verts à chaque étape, commit + cocher le tableau.
> **Mode draft obligatoire pour tous les essais.**

## Format final de la vidéo (validé avec l'auteur)

```
INTRO (existant, inchangé)        eye-open → dialogue 2 persos → narration → TIMER
                                  « Choisis ton personnage »
TRANSITION                        Narrateur : « Si tu as choisi Étienne... »
ROUND 1..3 (le chemin suivi = happy path : on survit)
  a. ACTION                       le perso avance (grotte, château, échelle...)
  b. ENVIRONNEMENT                hostile par nature (pierres suspendues, lave,
                                  structures instables) — narré + illustré
  c. LE PERSO PARLE               face caméra, manière décrite (chuchote, murmure,
                                  susurre...) : pose son dilemme lié à l'environnement
                                  ou une question simple
  d. NARRATEUR                    énonce les deux choix, illustrés
  e. TIMER 3-2-1                  (brique existante) — un des deux choix est fatal
  f. ISSUE FATALE                 « Si tu as choisi [A]... » description angoissante
                                  POV (ce qu'il te fait, comment tu réagis)
  g. ISSUE SURVIE                 « Si tu as choisi [B]... » — on continue
ÉPILOGUE                          « Si tu avais choisi [l'autre perso]... » résumé
                                  de ce que l'autre chemin aurait été
Durée cible : ~2 min – 2 min 30. Les rounds 2-3 enchaînent depuis l'issue survie.
Les deux issues de chaque round sont montrées l'une après l'autre (pas de branche réelle).
```

## Doctrine voix (simplifiée — décision auteur)

**Pas de TTS, pas de clonage, pas de banque : chaque clip embarque sa propre
voix, générée nativement par p-video depuis la description dans le prompt.**

- Le script GPT (phase S) génère UNE description de voix par identité —
  perso gauche, perso droit, narrateur — courte et ultra-distinctive
  (ex. « voix masculine jeune, rauque, qui chuchote, débit lent, française »).
- Cette description est **réinjectée VERBATIM dans chaque prompt de clip** où
  cette identité parle : c'est le mécanisme de cohérence vocale intra-vidéo.
- Les segments narrés (action, environnement, choix, issues, épilogue) sont des
  clips p-video dont le prompt fait parler le narrateur en voix off, avec la
  même description verbatim.
- Bonus gratuit : ambiance sonore native cohérente avec l'image sur chaque clip.
- Les sous-titres restent Whisper : on transcrit l'audio des clips finaux.

## L'enjeu n°1 : les prompts (décision auteur — « optimiser un maximum sans diluer »)

Tout le système repose sur le fait que les instructions des prompts sont
RESPECTÉES : voix, dialogue exact, caméra statique, style, absence de texte.
Les prompts sont donc un **composant à part entière**, centralisé, versionné et
testé — pas des strings éparpillées.

Règles d'or acquises en tests réels (à encoder dans les templates) :
1. **Une ligne = une contrainte fonctionnelle.** Pas de littérature. Court et
   dense > long et dilué (le modèle dilue son attention sur les pavés).
2. **Dialogue exact entre guillemets**, précédé de la manière de dire
   (« says in French, whispering: "..." »). Répliques COURTES (le natif
   paraphrase moins sur du court).
3. **Description de voix verbatim** — jamais reformulée d'un clip à l'autre.
4. **Ne jamais mentionner ce qu'on ne veut PAS voir** (l'épisode lunettes de
   soleil : nommer un objet = le faire apparaître). Formuler en positif.
5. **Jamais de texte demandé à l'image** (charabia garanti) — tout texte réel
   vient des briques overlay au montage.
6. Caméra statique : bloc anti-dérive existant, conservé tel quel.
7. Visuels EN, dialogues FR (règle projet existante).

## État d'avancement — POINT DE REPRISE

| Phase | Sujet | Statut | Commit |
|---|---|---|---|
| P | **Bibliothèque de prompts** : module `src/features/scripting/prompts.py` — templates à slots pour CHAQUE type de clip (action, environnement, face-cam dilemme, issue fatale, issue survie, narration over, épilogue) + blocs réutilisables (voix verbatim, caméra statique, style). Test réel : générer 2-3 clips d'un même perso et vérifier à l'oreille la cohérence vocale inter-clips. | ⬜ à faire | |
| S | **Script d'aventure** : structured output GPT — `AdventureScript` Pydantic (3 rounds : action, environnement, réplique perso + manière de dire, 2 choix, issue fatale, issue survie, lignes narrateur ; épilogue ; + les 3 descriptions de voix). Extension du port `ScriptDecomposer`. Le script remplit les slots des templates de la phase P. | ⬜ à faire | |
| A | **Step 1 étendu** : génération des assets de rounds — images env (seedream) + clips p-video (audio natif). Parallélisé. Flag `draft` global. Manifest d'assets par instance (extension metadata.json). Estimation de coût AVANT lancement. | ⬜ à faire | |
| M | **Step 2 étendu** : nouveaux constructeurs de segments dans le compositor (transition, action, face-cam, écran de choix A/B, issues, épilogue) en réutilisant les briques existantes (SubtitleOverlay, TimerOverlay, GaugeOverlay, NameplateOverlay). Sous-titres = Whisper sur l'audio des clips. Timeline complète. Golden intro inchangé. | ⬜ à faire | |
| U | **Streamlit max** : onglets (① Script & voix éditables avant génération, ② Assets — galerie par round avec **régénération à l'unité** + écoute audio de chaque clip + toggle draft/final, ③ Montage & preview, ④ Bibliothèque). Barres de progression, coût estimé, état de projet persistant. | ⬜ à faire | |

**Prochaine étape : Phase P — bibliothèque de prompts.**

## Protocole par phase

1. Implémenter la phase. 2. `pytest tests/` vert (le golden intro ne doit JAMAIS
casser). 3. Démo concrète à l'auteur (écouter les clips / lire un script généré /
voir les assets / regarder le montage). 4. Cocher le tableau + commit.

## Acquis techniques des tests réels (ne pas re-découvrir)

- seedream : `size` ∈ {2K, 4K, custom} ; jamais de texte dans l'image.
- p-video : `resolution` ∈ {720p, 1080p} ; `duration` se cale sur l'audio fourni,
  sinon sur le paramètre ; `save_audio: true` pour l'audio natif.
- API appelée en HTTP direct (package `replicate` absent de l'hôte, token `.env`).
- Upload de fichiers locaux : Files API (`/v1/files`, multipart) → URL signée.

## Risques identifiés

- **Cohérence vocale inter-clips** (le narrateur sur 10+ clips) : best-effort
  via description verbatim — à VALIDER en phase P avant tout le reste ; si
  insuffisant, repli : une seule longue piste narrateur générée en un clip et
  redécoupée au montage.
- **Paraphrase du dialogue natif** : répliques courtes + écoute par clip dans
  l'UI (phase U) + régénération à l'unité.
- **Coût par vidéo complète** : ~12-15 clips p-video → draft obligatoire,
  rendu final uniquement après validation dans l'UI.
