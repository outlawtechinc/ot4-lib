from loguru import logger
from pathlib import Path
from typing import Optional, Dict, Any
import environ

def read_env(
        env_file: Optional[Path] = None,
        overwrite: bool = False,
        encoding: str = "utf8",
        overrides: Optional[Dict[str, Any]] = None,
        scheme: Optional[Dict[str, tuple[Any, Any]]] = None,
) -> environ.Env:
    """
    Reads the .env file, initializes environment variables, and logs actions.

    Args:
        env_file (Optional[Path]): Path to the .env file.
        overwrite (bool): Whether to overwrite existing environment variables.
        encoding (str): Encoding to use when reading the .env file.
        overrides (Optional[Dict[str, Any]]): Overrides for specific environment variables.
        scheme (Optional[Dict[str, tuple[Any, Any]]]): Scheme defining default values for environment variables.

    Returns:
        environ.Env: The initialized environment object.

    # Example usage
    if __name__ == "__main__":
        env_path = Path(__file__).resolve().parents[2] / ".env"
        env = read_env(env_file=env_path, overwrite=False, scheme={"DEBUG": (bool, False)}, overrides={"DEBUG": "True"})
    """
    env = environ.Env(**(scheme or {}))

    if env_file and env_file.exists():
        env.read_env(env_file=env_file, overwrite=overwrite, encoding=encoding, **(overrides or {}))
        logger.info(f".env file found at: {env_file}")
        entry_count = count_env_lines(env_file)
        logger.info(f"Read {entry_count} valid entries from .env file.")
    else:
        logger.warning(".env file not found. Falling back to environment variables.")

    return env

def count_env_lines(env_file: Path) -> int:
    """
    Counts the number of valid (non-comment, non-empty) lines in the .env file.

    Args:
        env_file (Path): Path to the .env file.

    Returns:
        int: Number of valid lines in the file.
    """
    with env_file.open("r", encoding="utf8") as file:
        return sum(
            1 for line in file if line.strip() and not line.strip().startswith("#")
        )

