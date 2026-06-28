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
   - `python -m mypy src/<zone>` (ne pas dépasser la baseline cliquet = 40) ;
   - `python -m pytest -q` (rapide ~6 s ; `--runheavy` si le changement touche le rendu) ;
   - **commit** avec un message clair référant l'étape (ex. `feat(editor): R2 …`) ;
   - **cocher la ligne dans le tableau §5** de `ROADMAP.md` (⬜ → ✅) et résumer en 1–2 lignes.
5. Si la boucle Docker est dispo : `make verify` ; sinon chemin natif ci-dessus.

## Garde-fous
- Ne pas étendre le legacy `src/app.py` (Streamlit, en retrait).
- En cas d'ambiguïté sur l'étape ou un choix d'archi, demander avant d'implémenter.
