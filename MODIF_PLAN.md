# Plan de modification (vivant) — co-construit avec l'auteur

> Processus : l'auteur dicte ses souhaits → on précise ensemble → une équipe
> d'agents implémente (front + back). Document VIVANT : il grossit à chaque retour.

## Souhaits captés (batch 1)

- **M1 — Génération d'assets SÉQUENTIELLE / step-by-step.** Pouvoir faire
  « Suivant » asset par asset, voir chaque asset, juger s'il est utile,
  le régénérer / le garder / l'écarter. (mode revue guidée)
- **M2 — Assets inutiles / mal utilisés.** L'auteur a repéré des assets non
  utilisés dans la vidéo et des assets mal employés au montage. → à identifier
  précisément puis corriger (plan d'assets ↔ montage).
- **M3 — Accès aux projets cassé/absent dans le front.** Impossible de rouvrir
  un projet créé et ses épisodes. → navigation projets/épisodes.
- **(bug connexe déjà diagnostiqué) — Intro absente si on passe par « Monter ».**
  L'intro n'est générée que par « Produire ». Fix prévu : intro = asset généré
  pendant la génération d'assets (toujours présente). [cf. discussion]

## Questions ouvertes (à préciser ensemble)
- M1 : sur chaque asset, quelles actions ? (valider / régénérer / éditer le
  prompt / écarter «inutile» / passer au suivant) — et un récap final avant montage ?
- M2 : lesquels précisément sont inutiles / mal utilisés ?
- M3 : tu veux un dashboard avec projets cliquables → liste d'épisodes → épisode ?

## À compléter (l'auteur continue de dicter)
- …

## Exécution
Une fois le plan figé : équipe d'agents (front + back), une couche par agent,
tests verts à chaque étape, commits traçables.
