---
name: ship
description: Livrer en une commande — lance la vérification complète puis, si vert, commit et push sur la branche de travail. Propose une PR sans la créer sans accord.
---

# /ship — vérifier, committer, pousser

Livraison sûre d'un incrément. **Ne jamais pousser du rouge.**

## Étapes

1. **Vérifier** : `bash scripts/verify.sh` (complet ; `--heavy`/`--e2e` selon ce qui a changé,
   `--fast` seulement pour un correctif doc/config mineur).
   - Si **❌ FAIL** : s'arrêter, montrer ce qui casse, proposer de corriger. Ne pas committer.
2. **Committer** (si vert) :
   - message clair et scopé (ex. `feat(editor): …`, `fix(studio): …`, `chore(ci): …`) ;
   - si plusieurs sujets distincts, **plusieurs commits** (rester revert-able).
3. **Pousser** : `git push -u origin <branche-courante>` (retries avec backoff si erreur
   réseau). Ne **pas** pousser vers une autre branche que la branche de travail.
4. **PR** : proposer d'ouvrir une PR vers `main` **mais ne la créer
   qu'avec l'accord explicite** de l'auteur. Si une PR existe déjà, proposer de s'abonner aux
   événements (`subscribe_pr_activity`) pour auto-corriger les échecs CI.

## Garde-fous
- Pousser uniquement sur `dev` ; **jamais de push direct sur `main`** (passer par une PR).
- Respecter la baseline mypy (40) et la suite verte : le gate, c'est `scripts/verify.sh`.
