---
name: resume
description: Reprendre le travail sur le rail ViralCashMachine — ouvre ROADMAP.md, identifie la prochaine étape ⬜ et l'exécute selon le protocole par étape (une étape par session).
---

# /resume — reprendre le travail (protocole ROADMAP)

Tu reprends le développement de ViralCashMachine. **Source unique de vérité = `ROADMAP.md`.**

## Étapes

1. **Lire `ROADMAP.md`** : §4 (état consolidé, déjà fait — *ne pas refaire*) puis §5
   (étapes restantes). La **première ligne ⬜** du §5 est la prochaine étape.
2. **Annoncer** brièvement quelle étape tu prends et ce qu'elle livre. **Une seule étape par
   session** — ne pas enchaîner R2 puis R3.
3. **Implémenter** en respectant la direction produit : *« l'IA écrit → je révise en
   briques »* (pas d'éditeur vierge), les ports `typing.Protocol`, l'immutabilité de
   `VideoSpec`, l'idempotence de génération.
4. **Protocole de fin d'étape (ROADMAP §7)** :
   - tests cheap offline d'abord ;
   - **`bash scripts/verify.sh`** (mypy cliquet baseline 40 + pytest rapide + build front ;
     ajouter `--heavy` si le rendu est touché, `--e2e` si le front est touché) ;
   - **commit** avec un message clair référant l'étape (ex. `feat(editor): R2 …`) ;
   - **cocher la ligne dans le tableau §5** de `ROADMAP.md` (⬜ → ✅) et résumer en 1–2 lignes.

## Mode boucle autonome (opt-in : déclenché par `/loop /resume`)

Quand l'auteur lance `/loop /resume`, enchaîner les étapes ROADMAP **une par tour**, avec
`scripts/verify.sh` entre chaque, en **s'arrêtant au jalon** pour validation. Garde-fous :
- **Une étape, puis verify, puis stop** : ne pas empiler plusieurs étapes sans vérif verte.
- **S'arrêter et demander** dès qu'il y a une **décision de goût/UX** (typiquement **R2**,
  l'UI de revue), une ambiguïté sur le ROADMAP, ou un choix d'archi non tranché.
- Ne **jamais** committer rouge : si `verify` échoue, corriger ou revenir en arrière.
- Résumer à chaque jalon ce qui a avancé + l'état `verify`.

## Garde-fous
- Rester sur le rail v5 : les prompts se **compilent** (`compile_shot`), pas de 2e système de
  prompts ni d'UI hors document v5 (cf. `.claude/rules/architecture.md`).
- En cas d'ambiguïté sur l'étape ou un choix d'archi, demander avant d'implémenter.
