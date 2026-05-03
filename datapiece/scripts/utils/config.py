"""
A module for handling JSON configuration files and checking file existence.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict[str, Any]:
    """
    Loads a JSON config file.

    Args:
        config_path (str): Path to the config file.

    Returns:
        dict: Loaded config as a dictionary.

    Raises:
        SystemExit: If the file is missing or not valid JSON.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: config file not found: {config_path}")
        logger.error("Config file not found: %s", config_path)
        raise SystemExit(1)
    except json.JSONDecodeError as e:
        print(f"Error: config file is not valid JSON: {config_path}: {e}")
        logger.error("Config JSON parse error in %s: %s", config_path, e)
        raise SystemExit(1)


def get_key_dict(d: dict[str, Any], key: str) -> dict[str, Any]:
    """
    Returns the value of a key from a dictionary as a dict.
    """
    return d.get(key, {})


def get_key_str(d: dict[str, Any], key: str) -> str:
    """
    Returns the value of a key from a dictionary as a str.
    """
    return d.get(key, "")


def get_key_list(d: dict[str, Any], key: str) -> list[str]:
    """
    Returns the value of a key from a dictionary as a list.
    """
    return d.get(key, [])
