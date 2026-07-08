---
paths:
  - "src/**/*.py"
---

# Backend Python — règles

- **Architecture feature-driven à ports.** Chaque feature de `src/features/` expose un
  `ports.py` (`typing.Protocol`). Dépendre du **port**, pas de l'implémentation concrète ;
  injecter l'implémentation (Replicate, Whisper, fake…) au bord.
- **IR `VideoSpec` immuable.** Ne pas muter un spec construit ; le rendu (`render_moviepy.py`)
  ne fait qu'**interpréter** le spec. Le chemin canonique éditable est
  `idée → scenes (décomposeur) → scene_plan_to_document → EditorDocument v5 → compile_shot →
  document_to_spec → VideoSpec` (le `adventure_to_bricks` legacy est superseded).
- **Idempotence de génération.** Un nœud/asset `ready` (fichier présent) n'est ni régénéré
  ni repayé. Toute nouvelle génération doit réutiliser ce garde-fou (`_existing_done`/manifest).
  « 1 nœud de brique = 1 ligne `Asset` » (`beat = {id}.image|{id}.motion|{child.id}`).
- **mypy strict par zones** (`pyproject.toml`) : `src.infra.*`, `src.features.*`,
  `src.studio.db.*` sont en `strict`. Y ajouter du code = typer complètement.
- **`src/app.py` (Streamlit) est legacy** : mypy tolérant, en cours de retrait. Ne pas y
  ajouter de logique produit — elle va dans `src/studio/api/` + `frontend/`.
- **Avant commit** : `python -m mypy src` (baseline cliquet = **0** : toute nouvelle erreur
  casse le build, cf. `scripts/verify.sh`) et `python -m pytest -q` (rapide ~6 s ; `--runheavy` pour tout).
