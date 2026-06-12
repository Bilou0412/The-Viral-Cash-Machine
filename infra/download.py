import os
import requests
from typing import Optional
from .logging import log_terminal


def download_file(url: str, folder: str, filename: str) -> Optional[str]:
    if not url:
        return None
    try:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            log_terminal("SUCCESS", f"Downloaded: {filename}")
            return path
    except Exception as e:
        log_terminal("ERROR", f"Failed to download {url}: {e}")
    return None
