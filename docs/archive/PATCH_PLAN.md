# Plan de patch — corrections post-visionnage (épisode train-grotte)

> Retours auteur après la 1re vraie vidéo. Analyse ancrée sur le script généré.

## Problème racine (constaté dans le script)

Les choix des rounds étaient écrits « Suivre Louis » vs « Suivre Pierre » → le
format **re-choisit le personnage à chaque round** au lieu de **suivre l'unique
compagnon choisi**. D'où « l'histoire n'a pas de sens » et « les choix ne sont
pas sur l'aventure ».

**Paradigme correct (confirmé par l'auteur) :** intro = choisir UN compagnon ;
puis on SUIT ce compagnon ; les choix des rounds sont des **décisions d'aventure
(chemins/actions)**, pas un re-choix Louis/Pierre ; l'issue = **TOI** tu survis
ou tu meurs (POV) ; le compagnon réagit (il ne « disparaît » pas comme un choix).

## Les 6 patchs

- **P1 — Narrateur d'intro = phrase FIXE.** *« Choisis ton compagnon pour cette
  nuit : {NomA} ou {NomB} »* — seuls les prénoms varient, jamais régénérée.
  (logique template). Couche : intro.py (constante).
- **P2 — Dialogue d'intro = conseil angoissant + réponse courte, ordre ALÉATOIRE.**
  Un perso donne un conseil angoissant au spectateur, l'autre répond court ; seul
  leur texte change ; ordre gauche/droite tiré au hasard. Couches : R1 (répliques)
  + montage/intro (ordre random).
- **P3 — Voix natives + lip-sync, lèvres visibles** à l'intro (on voit les lèvres
  bouger). Couche : cadrage intro + voix natives (pas de conteur par-dessus).
- **P4 — Étape « Si tu as choisi {nom} » + zoom (ENTRÉE, oubliée).** Après l'intro,
  le narrateur dit « Si tu as choisi {nom} » + action/environnement où l'on va,
  AVEC zoom sur la vidéo du compagnon. Couches : R1 (transition) + montage (segment).
- **P5 — Choix = AVENTURE (un seul compagnon) + narrateur présente les choix AVEC
  les images.** Rounds suivent UN compagnon ; choix = chemins/actions ; issue =
  survie/mort DU SPECTATEUR ; compagnon réagit. Le narrateur nomme chaque option
  quand son image s'affiche. Couches : R1 (gros : prompts + Fake) + montage.
- **P6 — Cohérence (fil rouge).** Réglé en grande partie par P5 ; renforcer la
  règle de descente continue. Couche : R1.

## Ordre d'implémentation

1. **Patch A (scripting / R1)** : P5+P6 (reframe : un compagnon, choix = aventure,
   issue = spectateur) + P2-script (répliques conseil/réponse) + P1 (phrase fixe).
   → openai_adventure_decomposer (system prompt), fake, intro.py, tests.
2. **Patch B (montage / intro)** : P4 (segment d'entrée « si tu as choisi » + zoom),
   P5-montage (présentation des choix synchronisée aux images), P2-montage (ordre
   aléatoire), P3 (lip-sync lèvres visibles à l'intro).

## Statut
| Patch | Couche | Statut |
|---|---|---|
| A — script reframe (P5/P6/P2/P1) | R1 | ✅ `97b408a` |
| B — montage/intro (P4/P5/P2/P3) | montage+intro | ✅ `f68e77e` |

Reste à vérifier sur une VRAIE génération (les patchs sont codés + tests verts ;
l'effet visuel — un compagnon suivi, choix d'aventure, intro 2 voix lip-sync,
entrée « si tu as choisi » + zoom — se confirme à la prochaine production réelle).
