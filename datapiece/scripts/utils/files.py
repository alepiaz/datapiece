"""
A module for checking file and directory permissions.
"""

import os


def is_path_existent(path: str) -> bool:
    """
    Checks if a path exists.

    Args:
        path (str): Path to check.

    Returns:
        bool: True if path exists, False otherwise.
    """
    try:
        return os.path.exists(path)
    except OSError as e:
        print(f"An OSError occurred while checking if the file exists: {e}")
        return False


def is_path_readable(path: str) -> bool:
    """
    Checks if a path is readable.
    """
    try:
        return os.access(path, os.R_OK)
    except OSError as e:
        print(f"An OSError occurred while checking if the file is readable: {e}")
        return False


def is_path_writeable(path: str) -> bool:
    """
    Checks if a path is writable.
    """
    try:
        return os.access(path, os.W_OK)
    except OSError as e:
        print(f"An OSError occurred while checking if the file is writable: {e}")
        return False


def is_readable_existing_file(file_path: str) -> bool:
    """
    Checks if a file exists and is readable.
    """
    return is_path_existent(file_path) and is_path_readable(file_path)


def is_writeable_existing_file(file_path: str) -> bool:
    """
    Checks if a file exists and is writable.
    """
    return is_path_existent(file_path) and is_path_writeable(file_path)


def is_existing_file_in_writeable_directory(file_path: str) -> bool:
    """
    Checks if a file exists and its containing directory is writable.
    """
    dir_path = os.path.dirname(os.path.abspath(file_path))
    return is_path_existent(file_path) and is_path_writeable(dir_path)
