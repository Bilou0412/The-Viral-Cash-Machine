# Plan de modification (vivant) — co-construit avec l'auteur

> Processus : l'auteur dicte ses souhaits → on précise ensemble → une équipe
> d'agents implémente (front + back). Document VIVANT : il grossit à chaque retour.

---

## PARTIE A — Souhaits captés

### Batch 1 (revue & accès)
- **M1 — Génération d'assets SÉQUENTIELLE / step-by-step.** Faire « Suivant »
  asset par asset, voir chaque asset, juger s'il est utile, le régénérer /
  garder / écarter. (mode revue guidée) — *rendu sûr par la chronologie, cf. C5.*
- **M2 — Assets inutiles / mal utilisés.** L'auteur a repéré des assets non
  utilisés et des assets mal employés au montage. → corriger plan d'assets ↔ montage.
- **M3 — Accès aux projets cassé/absent dans le front.** Rouvrir un projet et
  ses épisodes. → navigation projets/épisodes.
- **(bug connexe)** Intro absente si on passe par « Monter » (générée seulement
  par « Produire »). Fix : intro = brique générée normalement (toujours présente).

### Batch 2 (le vrai cap : vidéo composable)
- **M4 — Composition libre par briques.** L'auteur ne décrit pas des blocs figés :
  il **choisit quelles briques mettre** dans chaque partie. Toujours une INTRO et
  une OUTRO ; au milieu, N **séquences-choix** (N configurable).
- **M5 — DA = THÈME sélectionnable** (cf. couche 2).
- **M6 — Chronologie / fil narratif** (cf. couche 5).

---

## PARTIE B — Architecture cible

### Vue d'ensemble
```
VIDÉO = INTRO (obligatoire) + SÉQUENCE-CHOIX × N (N choisi) + OUTRO (obligatoire)
Tu choisis un THÈME (DA) → tu COMPOSES chaque partie depuis la PALETTE de briques
→ tu décris persos + aventure → l'IA écrit le script PROCÉDURALEMENT (chronologie)
et remplit les briques → moteurs génération + montage → vidéo.
```
Principe : les moteurs **itèrent des briques**. Ajouter une brique / un thème =
une **définition**, pas une réécriture.

### Couche 1 — Palette de briques (existe déjà en code, à formaliser)
| Brique | Type | Arguments |
|---|---|---|
| Image | générateur | prompt (+ image réf optionnelle) → seedream |
| Vidéo | générateur | prompt + photo (+ durée, résolution… args Replicate) → p-video |
| Narration / Voix | générateur | texte + voix → minimax (conteur / native) |
| Timer | montage | image de fond + décompte → overlay |
| Plaque de prénom | montage (OPTION) | reconnaissance perso (têtes), posable sur image OU vidéo |
| Sous-titres | montage | audio → mots synchronisés |
| Zoom / Ken Burns / eye-open | montage | image/vidéo → effet |
Interfaces uniformes + **registre** de briques.

### Couche 2 — DA = Thème (cascade)
Le `Thème` (ex. « horreur ») = paquet de fragments DA (style visuel, ton, voix,
règles) + cover, choisi au départ. Résolution en **cascade** (= « à quel niveau
on choisit la DA ») :
```
DA d'un asset = surcharge ASSET ▸ sinon surcharge BLOC ▸ sinon défaut du THÈME
```
Tout hérite du thème ; on surcharge une séquence ou une image précise au besoin.

### Couche 3 — Structure composable
Intro (obligatoire) + N séquences-choix + outro (obligatoire). Dans chaque
partie, on **compose depuis la palette** (ex. séquence = vidéo + narration +
timer + plaque optionnelle). Rien d'imposé.

### Couche 4 — Script par IA (gardé)
On garde le comportement actuel : décrire **persos + aventure** suffit, l'IA
écrit le script (pas besoin de détailler). Le script **remplit les slots** des
briques composées ; le thème injecte la DA dans les prompts.

### Couche 5 — Chronologie / fil narratif
Pattern « plan d'arc puis expansion procédurale » :
1. **Timeline hypothétique** : N connu d'avance → l'IA pose un squelette d'arc
   (début → montée sur N séquences → climax → fin) ; chaque bloc sait sa position.
2. **État narratif porté** : génération procédurale — chaque bloc est généré en
   connaissant le **résumé de ce qui précède** (lieu, événements, tension, choix
   précédent) et produit un **état mis à jour** pour le bloc suivant.
3. **Continuité visuelle** : chaînage dernière frame vidéo N → réf image N+1 +
   référence perso (déjà partiel), formalisé dans la chronologie.
→ Rend la **régénération unitaire (M1) cohérente** : un bloc régénéré respecte
  l'état narratif autour de lui.

---

## PARTIE C — Méthodologie de travail
1. Formaliser la **palette** (interfaces uniformes) + **registre**.
2. Couche **thème** (DA en cascade).
3. Modèle de **composition** (intro + N + outro, briques par partie).
4. **Moteurs** génération + montage génériques (itèrent les briques) + **chronologie**.
5. **Front** : choisir thème → composer les parties → décrire persos/aventure →
   produire (avec revue step-by-step M1) + accès projets (M3).
6. **Équipe d'agents** : une couche par agent, tests verts + commits traçables.

---

## PARTIE D — Design & modèle économique

### D1 — Design / maquette (via agent designer dans l'équipe)
- Agent **UX/UI designer** instanciable dans l'équipe (+ back, BDD, front,
  paiement, devops).
- Forme retenue de la maquette : **prototype React cliquable dans la stack
  existante** (React/Vite/Tailwind/shadcn), données factices d'abord, modifiable
  en live, puis câblé back + BDD par l'équipe. Pas de travail jetable.
- Livrables designer : design system (tokens + composants), wireframes, prototype
  cliquable couvrant TOUT le plan (thème → composition → revue step-by-step →
  accès projets → écrans de paiement/tokens).

### D2 — Modèle économique : open-core + économie de tokens
- **Open-core** : OSS = moteur créatif (palette, composition, compositeur,
  chronologie, **self-host BYOK**). SaaS propriétaire = hébergé (multi-tenant,
  auth, billing, file gérée, thèmes premium, marketplace, pub récompensée).
- **Unité = token de génération** (= coût réel Replicate/OpenAI + marge).
- **Rails de financement** : BYOK/self-host (gratuit) · packs pay-as-you-go ·
  abonnement (tokens inclus + perks) · pub récompensée (pub → tokens gratuits).
- **Garde-fous** : plafond dur/génération · estimation coût avant dépense ·
  réservation tokens + remboursement si échec · idempotence (no double-débit) ·
  quotas/rate-limit par tier · anti-fraude pub (validation serveur + cap quotidien)
  · journal `CostEntry` = base du billing · séparation stricte OSS/SaaS ·
  modération contenu · paiement via Stripe (PCI géré).

### Décisions en attente (D)
- Forme maquette : prototype React cliquable (reco) / HTML statique d'abord / design-system seul ?
- Licence OSS : cœur permissif MIT-Apache (adoption) / cœur AGPL (protège le SaaS) / tout proprio d'abord ?
- Rails de financement v1 : lesquels d'abord (BYOK / packs / abonnement / pub) ?

---

## Questions ouvertes
- M1 : actions par asset (valider / régénérer / éditer prompt / écarter / suivant)
  + récap final avant montage ?
- M2 : lesquels précisément sont inutiles / mal utilisés ?
- M3 : dashboard projets cliquables → épisodes → épisode ?
- Thème : on part de « horreur » comme 1er thème extrait du code existant ?

## À compléter (l'auteur continue de dicter)
- …

## Exécution
Plan figé → équipe d'agents (front + back), une couche par agent, tests verts à
chaque étape, commits traçables.
