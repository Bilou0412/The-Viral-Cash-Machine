# Plan d'extension — « L'Aventure » (format complet 3 rounds)

> Extension du template intro existant vers le format complet : intro → choix du
> personnage → 3 rounds d'aventure à dilemmes → épilogue de l'autre branche.
> Même philosophie que le refactor : une phase par session, tests verts à chaque
> étape, commit + cocher le tableau. **Mode draft obligatoire pour tous les essais.**

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

## Les 3 identités vocales

Perso gauche, perso droit, narrateur — tous distincts. Le TTS stock Minimax est
jugé insuffisant ; p-video invente de bonnes voix décrites au prompt (validé en
test). Stratégie **banque de voix** : audition par p-video → clonage
`minimax/voice-cloning` → `voice_id` permanents stockés en banque. La manière de
parler (chuchotement...) est **clonée avec la voix** : la banque est organisée
par registre (le chuchoteur, le caverneux, le doucereux...). Le narrateur garde
UNE voix fixe = signature sonore de la chaîne.

⚠️ Acquis des tests : `minimax/voice-cloning` exige `model` ∈
{speech-2.6-turbo, speech-2.6-hd, speech-02-turbo, speech-02-hd} ;
seedream exige `size` ∈ {2K,4K,custom} ; p-video exige `resolution` ∈ {720p,1080p}.

## État d'avancement — POINT DE REPRISE

| Phase | Sujet | Statut | Commit |
|---|---|---|---|
| V | **Banque de voix** : audition p-video (5-6 registres décrits) → extraction → clonage → `assets/voices.json` {nom, registre, description, voice_id, sample}. Voix narrateur signature choisie par l'auteur. Port `VoiceBank` + extension `AssetProvider`. | ⬜ à faire | |
| S | **Script d'aventure** : structured output GPT — `AdventureScript` Pydantic (3 rounds : action, environnement, réplique perso + manière de dire, 2 choix, issue fatale, issue survie, lignes narrateur ; + épilogue autre branche). Règles : visuels EN, dialogues FR, caméra statique. Extension du port `ScriptDecomposer`. | ⬜ à faire | |
| A | **Step 1 étendu** : génération des assets de rounds — images env (seedream), clips action/face-cam/issues (p-video, audio = voix clonées), audios narrateur. Parallélisé. Flag `draft` global. Manifest d'assets par instance (extension metadata.json). Estimation de coût AVANT lancement. | ⬜ à faire | |
| M | **Step 2 étendu** : nouveaux constructeurs de segments dans le compositor (transition, action narrée + subs, face-cam + subs, écran de choix A/B, issues, épilogue) en réutilisant les briques existantes (SubtitleOverlay, TimerOverlay, GaugeOverlay, NameplateOverlay). Timeline complète intro + 3 rounds + épilogue. Golden intro inchangé. | ⬜ à faire | |
| U | **Streamlit max** : onglets (① Script & casting éditable avant génération, ② Assets — galerie par round avec **régénération à l'unité** + toggle draft/final, ③ Montage & preview, ④ Bibliothèque des vidéos produites). Barres de progression, coût estimé affiché, état de projet persistant (reprendre une vidéo en cours). | ⬜ à faire | |

**Prochaine étape : Phase V — banque de voix.**

## Protocole par phase

1. Implémenter la phase. 2. `pytest tests/` vert (le golden intro ne doit JAMAIS
casser). 3. Démo concrète à l'auteur (écouter les voix / lire un script généré /
voir les assets / regarder le montage). 4. Cocher le tableau + commit.

## Risques identifiés

- **Coût par vidéo complète** : ~12-15 clips p-video (≈ ×4 vs intro seule) →
  draft obligatoire pour itérer, rendu final uniquement après validation du
  script et des assets dans l'UI.
- **Cohérence vocale intra-vidéo** : les répliques face-cam des persos passent
  par p-video AVEC audio cloné en entrée (identité garantie), pas en voix native.
- **Temps de génération** : parallélisation Step 1 indispensable (déjà le cas
  pour la détection de têtes ; à généraliser aux clips).
