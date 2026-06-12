import datetime


def log_terminal(level: str, message: str) -> None:
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m",
    }
    color = colors.get(level, colors["RESET"])
    print(f"{color}[{timestamp}] [{level}] {message}{colors['RESET']}")
