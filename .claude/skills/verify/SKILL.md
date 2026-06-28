---
name: verify
description: Lancer la boucle de vérification native (mypy cliquet + pytest + build front, +e2e en option) et résumer pass/fail. Source unique = scripts/verify.sh.
---

# /verify — boucle de vérification

But : confirmer qu'on n'a rien cassé, de façon déterministe. **Une seule source** :
`scripts/verify.sh` (la même qu'utilisent la CI et le hook de session).

## Commande

```bash
bash scripts/verify.sh            # mypy cliquet (baseline 40) + pytest rapide + build front
bash scripts/verify.sh --fast     # mypy + pytest rapide seulement (~20 s)
bash scripts/verify.sh --heavy    # pytest complet (--runheavy : render + intégration)
bash scripts/verify.sh --e2e      # + Playwright (front en mock)
```

(En local avec Docker, `make verify` reste équivalent ; `make verify-native ARGS="--heavy"`
appelle ce même script sans Docker.)

## Rapport attendu
- mypy : nombre d'erreurs vs **baseline 40** (régression si > 40).
- pytest : passed/failed (nommer les tests rouges) ; skipped attendus sans ffmpeg.
- build front / e2e : OK/KO si lancés.
- Conclusion : le script imprime un bloc `VERIFY` avec `✅ PASS` ou `❌ FAIL` et un exit code.
  Relayer ce verdict ; si FAIL, lister précisément ce qui casse.
