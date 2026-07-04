import os

from .logging import log_terminal


def save_key_to_env(key_name: str, value: str) -> None:
    if not value:
        return
    try:
        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path) as f:
                lines = f.readlines()
        found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key_name}="):
                new_lines.append(f"{key_name}={value}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key_name}={value}\n")
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        log_terminal("SUCCESS", f"Saved {key_name} to .env file.")
    except Exception as e:
        log_terminal("ERROR", f"Failed to save {key_name} to .env: {e}")
