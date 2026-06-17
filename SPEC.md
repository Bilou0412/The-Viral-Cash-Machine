# SPEC — Histoire à choix (Horreur)

> **Document de référence du produit. Anti-dérive.**
> Tout ce qui n'est pas ici n'est pas dans le produit. La partie générique
> (éditeur de briques, timeline libre, catalogue de modèles) existe dans le code
> mais devient **infrastructure d'arrière-plan** : l'utilisateur ne la voit pas.

Statut : **cible verrouillée le 2026-06-17.** La « partie finale » est en attente
de description (section 7).

---

## 1. La vision en une phrase

> **À partir d'une prompt (un pitch d'horreur), le logiciel génère une vidéo
> verticale 9:16 complète d'« histoire à choix » — intro + 3 scènes de choix —
> et l'exporte en MP4.**

L'utilisateur ne monte rien à la main. Il décrit, le moteur produit.

---

## 2. Le modèle mental (les 5 invariants)

1. **L'atome, c'est l'IMAGE.** Tout visuel part d'une image générée.
2. **Une VIDÉO = une image qu'on ANIME** (image-to-video). Une **PHOTO** = la même
   image **qu'on n'anime pas**. La seule différence entre photo et vidéo, c'est
   l'étape d'animation.
3. **Le SON se greffe sur le visuel** : voix du narrateur + voix des personnages
   + ambiance. Le visuel est le parent, le son l'enfant.
4. **La NARRATION est la colonne vertébrale.** Le texte du narrateur dicte :
   (a) quels visuels générer (1 visuel par action/élément décrit),
   (b) le timing (un visuel dure le temps de la phrase qu'il illustre),
   (c) où placer les timers.
5. **La vidéo est LINÉAIRE.** Aucune interactivité, aucun clic. On *montre à
   l'écran* les conséquences des deux options (« si tu fais X tu meurs / si tu
   fais Y tu vis »). Le timer est dramatique, le « jeu » est mental.

---

## 3. Structure du template

```
VIDÉO = INTRO  +  3 × SCÈNE DE CHOIX  +  PARTIE FINALE (§7, à venir)
```

### 3.1 INTRO (générée une fois, en tête)

| # | Beat | Visuel | Son |
|---|------|--------|-----|
| I1 | Présentation des **2 personnages** : physique, attitude, ce qu'ils disent, ce qu'ils font | **VIDÉO** | voix perso (réplique d'accroche) |
| I2 | Narrateur : « choisis ton compagnon pour la nuit » (ton angoissant) | (sur I1) | voix narrateur |
| I3 | **Timer 3 s** (décompte + jauge + tic/bip) | overlay | SFX tic ×3 + bip |
| I4 | **Zoom** sur le compagnon choisi + narrateur « si tu as choisi *X* » | **VIDÉO** (zoom) | voix narrateur |

> Le « si tu as choisi X » + zoom reste **dans l'intro** : on ne le refait pas à
> chaque scène.

### 3.2 SCÈNE DE CHOIX (× 3, chaînables comme des briques)

Chaque scène commence **toujours par le décor** → c'est ce qui les rend
interchangeables et empilables à la suite.

| # | Beat | Visuel | Son |
|---|------|--------|-----|
| C1 | **Mise en scène** : le lieu **et/ou** le perso dedans (décor, le perso qui marche devant, ambiance…) | **VIDÉO(s)** — 1 à 3, 1 par élément décrit | voix narrateur |
| C2 | **Beat histoire** : le perso **agit + parle** dans le MÊME clip — gestes liés à ce qu'il dit (montre les choix, manipule un objet, action en rapport avec les options) | **VIDÉO** (1) | voix narrateur + voix perso (native) |
| C3 | **Les 2 choix** énoncés par le narrateur (option A / option B) | **PHOTO** — 1 par option, calée sur la narration | voix narrateur |
| C4 | **Timer 3 s** (comme I3) | overlay | SFX tic ×3 + bip |
| C5 | **Conséquence MORT** : enchaînement fatal décrit (action par action) | **VIDÉO(s)** — 1 par action | voix narrateur |
| C6 | **Conséquence SURVIE** : le bon choix décrit | **VIDÉO(s)** | voix narrateur |

> **Photo vs vidéo n'est pas un détail** : C3 (les choix) = PHOTO ; tout le reste
> = VIDÉO. C'est une règle du template, pas une décision manuelle.

**Compte d'une scène** : **6 clips** nominaux à la suite — C1(1) · C2(1) · C3(2 photos)
· C4(timer) · C5(1) · C6(1) ; jusqu'à 12 si le fan-out 1-3 est plein. La narration
**se superpose** (jamais un clip séparé). Pour N=3 scènes : ≈ 22 clips (+ intro 3).

### 3.2.1 Règle de production (anti-gaspillage)

- **Une image n'est générée que si elle est montrée** (photo C3) **ou** sert de
  **référence i2i** (cohérence perso/DA). Les `*.frame` des beats vidéo servent
  UNIQUEMENT d'image-source de l'animation — **jamais re-montées figées sous la
  narration** (c'était le doublon « images inutiles »).
- **Pas de plan « face-cam » séparé** : la réplique du perso est dans le clip C2.
  → on **supprime** la génération de `character.frame`.
- **La durée d'un clip = la durée de SA phrase de narration** (colonne vertébrale),
  pas une vidéo unique accélérée pour remplir.

### 3.3 PARTIE FINALE

→ **À décrire** (section 7). Tient en réserve dans la structure.

---

## 4. Ce que le produit N'EST PAS (non-goals)

- ❌ Pas un éditeur libre pour l'utilisateur final (CapCut/timeline). Ça existe
  dans le code, ça reste **en arrière-plan** comme moteur d'assemblage.
- ❌ Pas d'interactivité / branches cliquables. La vidéo est un fichier linéaire.
- ❌ Pas de format autre que 9:16 vertical pour ce produit.
- ❌ Pas de choix manuel photo/vidéo par l'utilisateur : c'est le template qui
  décide.

---

## 5. Le flux (du prompt au MP4)

```
prompt (pitch horreur)
   │  décomposeur (LLM)  →  AdventureScript structuré (2 persos + N scènes)
   ▼
plan de génération  →  pour chaque beat :  IMAGE  → (anime ?) → VIDÉO/PHOTO  + VOIX
   │                    (téléchargement immédiat des sorties Replicate)
   ▼
montage (MoviePy)  →  intro + 3 scènes + final, sous-titres mot-à-mot, timers, zoom
   ▼
final_video.mp4 (9:16)
```

Le **système de briques** (image / animation / voix) est l'outil interne qui
fabrique chaque illustration. Il n'est jamais exposé.

---

## 6. Critères d'acceptation (testables)

Le produit est « fonctionnel » quand, à partir d'**une seule prompt** :

- **A1** — Une vidéo MP4 9:16 unique est produite.
- **A2** — Elle contient, dans l'ordre : INTRO (I1→I4) puis exactement 3 SCÈNES
  DE CHOIX (C1→C6) puis la PARTIE FINALE.
- **A3** — L'intro présente **2 personnages** nommés (noms FR), une accroche par
  perso, la phrase « choisis ton compagnon », un **timer 3 s**, puis un **zoom**
  sur un compagnon avec « si tu as choisi X ».
- **A4** — Dans chaque scène : C3 est rendu en **PHOTO** (2 photos, une par
  option) ; C1/C2/C5/C6 sont rendus en **VIDÉO** (image animée).
- **A5** — Chaque scène montre **les deux issues** (mort ET survie).
- **A6** — La narration porte des **sous-titres mot-à-mot** synchronisés.
- **A7** — Chaque visuel dure le temps de la phrase qu'il illustre (narration =
  colonne vertébrale).
- **A8** — Tout est en **français** (dialogue/narration) ; les prompts visuels
  internes sont en anglais.
- **A9** — Le ton **horreur** s'applique en cascade à tous les visuels (thème).
- **A10** — Aucune URL Replicate n'est réutilisée : chaque sortie est téléchargée
  localement immédiatement.

Critères non-fonctionnels :
- **N1** — Un mode « faux fournisseurs » permet de produire la vidéo de bout en
  bout **sans appel API** (test/CI offline, assets factices).
- **N2** — Les golden tests existants restent verts (pipeline aventure intact).

---

## 7. PARTIE FINALE — à décrire

_Réservé. L'utilisateur décrira cette section ; elle s'ajoutera après les 3
scènes de choix, dans la même logique de beats (narration = colonne, image =
atome, photo/vidéo selon règle)._

---

## 8. Glossaire

- **Beat** : la plus petite unité narrative = une phrase de narration + ses
  visuels + son timing.
- **Scène de choix** : bloc de 6 beats (C1→C6), brique chaînable.
- **i2v** : image-to-video, l'animation d'une image en clip.
- **Cascade (thème)** : valeur résolue brique ▸ profil ▸ template ▸ thème global.
