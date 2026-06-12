"""SRT subtitle utilities."""


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def save_srt(subs_data: list[dict], output_path: str) -> None:
    """Save subtitles to SRT file."""
    if not subs_data:
        return
    with open(output_path, "w", encoding="utf-8") as f:
        for i, s in enumerate(subs_data, 1):
            f.write(
                f"{i}\n{format_timestamp(s['start'])} --> {format_timestamp(s['end'])}\n{s['text']}\n\n"
            )
