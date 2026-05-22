from pathlib import Path
from typing import Generator, Tuple
from tiktoken import get_encoding


def estimate_token_count(text: str) -> int:
    encoding = get_encoding('cl100k_base')
    return len(encoding.encode(text))


def file_to_str_gen(
    dir_path: Path, extension: str
) -> Generator[Tuple[Path, str], None, None]:
    """
    Generates strings from files with a specific extension in a directory.
    Function returns a generator such that not all files are read into memory
    at once.

    Args:
        dir_path (Path): The path to the directory containing the files.
        extension (str): The file extension to filter by (e.g., '.php').

    Yields:
        Tuple[Path, str]: A tuple containing the relative file path from
            dir_path and the file content as a string.
    """

    for file in dir_path.glob(f'**/*{extension}'):
        with open(file, 'r', encoding='utf-8') as f:
            yield (file.relative_to(dir_path), f.read())
