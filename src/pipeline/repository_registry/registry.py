from dataclasses import dataclass, field
from logging import getLogger
from typing import Callable, Dict, FrozenSet, Optional, Tuple

from src.settings import settings

logger = getLogger(__name__)

# A syntax check takes a code snippet and returns (passed, output).
SyntaxCheck = Callable[[str], Tuple[bool, str]]
# A correctness check takes an optional worker index and returns
# (passed, output).
CorrectnessCheck = Callable[[Optional[int]], Tuple[bool, str]]


@dataclass(frozen=True)
class RepositoryProfile:
    """
    Everything the pipeline needs to operate on a particular repository.
    """

    # Human-facing name, e.g. "PHP". Used in prompts and result metadata.
    language_name: str
    # Source file extension without the dot, e.g. "php". Used to glob the
    # repository for source files and to fence code blocks in prompts.
    language_extension: str
    # Validates a code snippet for this language.
    syntax_check: SyntaxCheck
    # Runs the repository's test suite against an isolated environment.
    correctness_check: CorrectnessCheck
    # The tree-sitter Language object used to parse source files of this
    # language.
    tree_sitter_language: object
    # The set of tree-sitter node types that represent a "function" for this
    # language.
    function_node_types: FrozenSet[str] = field(default_factory=frozenset)


_REGISTRY: Dict[str, RepositoryProfile] = {}


def register_repository(key: str, profile: RepositoryProfile) -> None:
    """
    Register a repository profile. Re-registering the same key
    overwrites the previous profile.

    Args:
        key (str): The key to store the profile under.
        profile (RepositoryProfile): The repository profile to store in the
            registry.
    """

    if key in _REGISTRY:
        return

    _REGISTRY[key] = profile


def get_repository_profile() -> RepositoryProfile:
    """
    Return the repository profile selected by ``settings.repository_profile``.
    """

    key = settings.repository_profile
    try:
        return _REGISTRY[key]
    except KeyError:
        raise KeyError(
            f'No repository registered under {key!r}. '
            f'Registered languages: {sorted(_REGISTRY)}. '
            'Register one with register_repository() in '
            'src/pipeline/code_checks/repositories/.'
        )


# Remove circal dependencies of repository definitions trying to import
# RepositoryProfile, while it has not yet been defined.
import src.pipeline.repository_registry.repositories  # noqa: E402,F401
