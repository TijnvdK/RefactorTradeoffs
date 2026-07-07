import tree_sitter_php

from src.pipeline.code_checks.correctness_checks.engineblock import (
    correctness_check_eb,
)
from src.pipeline.repository_registry.registry import (
    RepositoryProfile,
    register_repository,
)
from src.pipeline.code_checks.syntax_checks.php import syntax_check_php

_PHP_FUNCTION_NODES = frozenset(
    {
        'function_definition',
        'method_declaration',
        'anonymous_function',
        'arrow_function',
    }
)


register_repository(
    'engineblock',
    RepositoryProfile(
        language_name='PHP',
        language_extension='php',
        syntax_check=syntax_check_php,
        correctness_check=correctness_check_eb,
        tree_sitter_language=tree_sitter_php.language_php(),
        function_node_types=_PHP_FUNCTION_NODES,
    ),
)
