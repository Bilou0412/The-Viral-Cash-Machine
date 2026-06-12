"""OpenAI GPT script decomposer implementation."""

import json
from typing import Optional

from openai import OpenAI

from .ports import ScriptDecomposition, ScriptDecomposer


class OpenAIScriptDecomposer:
    """Decomposes scripts using OpenAI GPT models."""

    def __init__(self, client: OpenAI, model: str):
        """Initialize with OpenAI client and model.

        Args:
            client: Authenticated OpenAI client.
            model: Model identifier (e.g., "gpt-5.4-mini").
        """
        self.client = client
        self.model = model

    def decompose(
        self,
        script: str,
        instance_type: str = "intro",
        char_left_gender: str = "Male",
        char_right_gender: str = "Female",
    ) -> ScriptDecomposition:
        """Decompose script into visual elements.

        Args:
            script: User-provided script description.
            instance_type: Type of instance ("intro", "mid", "final").
            char_left_gender: Gender of left character.
            char_right_gender: Gender of right character.

        Returns:
            ScriptDecomposition with filled visual slots.

        Raises:
            ValueError: If script decomposition fails or returns invalid data.
        """
        if instance_type == "intro":
            sys_msg = f"""You are a master of horror video architecture.
Task: Decompose the script into behavioral slots for a ViralCashMachine_V2 instance.

CONTEXT:
- Left Monster: Gender is {char_left_gender}.
- Right Monster: Gender is {char_right_gender}.

LANGUAGE RULE:
- All descriptions (visuals, movements, environment) MUST be in ENGLISH.

VISUAL RULE:
- NEVER use terms like 'hunched', 'crawling', 'leaning forward', 'predatory posture', 'sway', 'breathing', 'shifting', or 'floating'. These cause the video model to move the camera or the character's root.
- SAFE HORROR: Use terms like 'weathered', 'ashen', 'pale', 'aged', 'rough textured' instead of 'decayed', 'zombie', 'naked', or 'raw'.
- Describe monsters as STANDING UPRIGHT and FACING FORWARD. NO head movement. Only eyes and mouth animate.

Requirements:
1. Output a JSON with specific slots.
2. monster_left_desc: Visual description (ENGLISH).
3. monster_right_desc: Visual description (ENGLISH).
4. monster_left_idle: Movement (ENGLISH).
5. monster_right_idle: Movement (ENGLISH).
6. environment_desc: Background (ENGLISH).

JSON Format:
{{
    "monster_left_desc": "...",
    "monster_right_desc": "...",
    "monster_left_idle": "...",
    "monster_right_idle": "...",
    "environment_desc": "..."
}}"""
        else:
            sys_msg = "Standard decomposition. ALL descriptions MUST be in English. Use safe horror terms (weathered, ashen)."

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": script},
                ],
            )
            data = json.loads(resp.choices[0].message.content)

            # Extract and validate required fields
            monster_left_desc = data.get("monster_left_desc", "")
            monster_right_desc = data.get("monster_right_desc", "")
            monster_left_idle = data.get("monster_left_idle", "")
            monster_right_idle = data.get("monster_right_idle", "")
            environment_desc = data.get("environment_desc", "")

            if not all(
                [
                    monster_left_desc,
                    monster_right_desc,
                    monster_left_idle,
                    monster_right_idle,
                    environment_desc,
                ]
            ):
                raise ValueError("One or more required decomposition fields are empty")

            return ScriptDecomposition(
                monster_left_desc=monster_left_desc,
                monster_right_desc=monster_right_desc,
                monster_left_idle=monster_left_idle,
                monster_right_idle=monster_right_idle,
                environment_desc=environment_desc,
            )

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse GPT response as JSON: {e}")
        except Exception as e:
            raise ValueError(f"Script decomposition failed: {e}")
