"""Compilateur de contexte récit (E6).

Le « récit » de l'éditeur = un `NarrativeContext` GLOBAL hérité par toutes les briques,
+ des **surcharges locales** par brique. `compile_prompt` fond les deux puis assemble la
matière de prompt finale pour une brique générative (texte → contexte → prompt d'asset).

Cascade (généralise `themes.resolve` : le plus spécifique gagne) :
    surcharge BRIQUE ▸ (profil/template — branché en E5) ▸ contexte GLOBAL

Module pur (aucune I/O) — `editor_generation` l'appelle avant `run_model`.
"""

from typing import Optional

from .document import NarrativeContext


def merge_context(
    global_ctx: NarrativeContext, override: Optional[NarrativeContext] = None
) -> NarrativeContext:
    """Fond le contexte global et la surcharge locale (le local gagne s'il est rempli).

    - `text` / `art_direction` : la surcharge non vide l'emporte, sinon le global.
    - `characters` / `extra` : fusion (les clés locales écrasent/complètent les globales).
    """
    if override is None:
        return global_ctx
    return NarrativeContext(
        text=override.text or global_ctx.text,
        art_direction=override.art_direction or global_ctx.art_direction,
        characters={**global_ctx.characters, **override.characters},
        extra={**global_ctx.extra, **override.extra},
    )


def compile_prompt(
    base_prompt: str,
    global_ctx: NarrativeContext,
    override: Optional[NarrativeContext] = None,
    *,
    template_prefix: str = "",
    include_story: bool = True,
) -> str:
    """Assemble le prompt final d'une brique à partir de son prompt + du contexte.

    `template_prefix` : matière injectée par un template opinionated (E5), placée en
    tête. `include_story` : inclure le texte de trame (utile pour image/vidéo, parfois
    superflu pour une voix dont le `text` est déjà la réplique).
    """
    ctx = merge_context(global_ctx, override)
    parts: list[str] = []
    if template_prefix and template_prefix.strip():
        parts.append(template_prefix.strip())
    if base_prompt and base_prompt.strip():
        parts.append(base_prompt.strip())
    if ctx.characters:
        chars = "; ".join(f"{name}: {desc}" for name, desc in ctx.characters.items())
        parts.append(f"Characters — {chars}")
    if include_story and ctx.text:
        parts.append(f"Story context: {ctx.text}")
    if ctx.art_direction:
        parts.append(ctx.art_direction)
    if not parts:
        return ""
    return ". ".join(p.rstrip(".") for p in parts) + "."
