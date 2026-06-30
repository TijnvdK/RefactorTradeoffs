from typing import Dict, FrozenSet, List, Optional, Tuple, TypedDict
from tree_sitter import Language, Node, Parser

from src.pipeline.code_checks.registry import get_repository_profile
from src.settings import settings

_PARSER_CACHE: Dict[str, Tuple[Parser, FrozenSet[str]]] = {}


def _get_parser() -> Tuple[Parser, FrozenSet[str]]:
    """
    Return the parser for the configured repository. Will build and cache
    on first use.

    Returns:
        Tuple[Parser, FrozenSet[str]]: The parser and function_node_types
            for the configured repository.
    """

    key = settings.repository_profile
    cached = _PARSER_CACHE.get(key)
    if cached is not None:
        return cached

    profile = get_repository_profile()
    parser = Parser(Language(profile.tree_sitter_language))
    entry = (parser, profile.function_node_types)
    _PARSER_CACHE[key] = entry
    return entry


class FunctionInfo(TypedDict):
    name: str
    start_line: int
    end_line: int
    source: str
    LOC: int


def _collect_functions(
    node: Node,
    lines: List[str],
    results: List[FunctionInfo],
    function_node_types: FrozenSet[str],
) -> None:
    """
    Walk a node tree and retrieve information about function nodes.

    Args:
        node (Node): The root node to start walking from.
        lines (List[str]): The lines of the source code file, used to retrieve
            the source code of each function.
        results (List[FunctionInfo]): A list to store the retrieved function
            information.
        function_node_types (FrozenSet[str]): The tree-sitter node types that
            represent a function for the configured language.
    """

    if node.type in function_node_types:
        name_node = node.child_by_field_name('name')

        if name_node and name_node.text:
            name = name_node.text.decode()
        else:
            name = 'anonymous'

        start_line = node.start_point[0]
        end_line = node.end_point[0]
        source = '\n'.join(lines[start_line : end_line + 1])

        sloc = sum(
            1 for line in lines[start_line : end_line + 1] if line.strip()
        )

        results.append(
            FunctionInfo(
                name=name,
                start_line=start_line,
                end_line=end_line,
                source=source,
                LOC=sloc,
            )
        )

        # Do not descend into a captured function.
        return

    for child in node.children:
        _collect_functions(child, lines, results, function_node_types)


def extract_functions(source: str, min_loc: int = 0) -> List[FunctionInfo]:
    """
    Parse a source code file and retrieve information about every function
    within that source code file, using the parser for the configured
    language.

    Args:
        source (str): The source code file.
        min_loc (int, optional): Only return functions that have at minimum
            this amount of LOC. Defaults to 0.

    Returns:
        List[FunctionInfo]: A list of FunctionInfo objects, each containing
            information about a function in the source code.
    """

    parser, function_node_types = _get_parser()
    tree = parser.parse(source.encode())
    lines = source.splitlines()

    results: List[FunctionInfo] = []
    _collect_functions(tree.root_node, lines, results, function_node_types)
    return [f for f in results if f['LOC'] >= min_loc]


def splice_function(
    source: str, function_info: FunctionInfo, new_function: str
) -> str:
    """
    Replace the lines occupied by function in source with the new_function.

    Args:
        source (str): The source file with the original function.
        function_info (FunctionInfo): The information about the function to
            be replaced.
        new_function (str): The new function definition.

    Returns:
        str: The source file with the updated function.
    """

    lines = source.splitlines(keepends=True)

    before = lines[: function_info['start_line']]
    after = lines[function_info['end_line'] + 1 :]
    replacement = (
        new_function if new_function.endswith('\n') else new_function + '\n'
    )

    return ''.join(before) + replacement + ''.join(after)


def relocate_function(
    source: str, function_info: FunctionInfo
) -> Optional[FunctionInfo]:
    """
    Find a function's *current* location in ``source`` by re-parsing it.

    Function line numbers captured when a file is first scanned go stale as
    soon as another function in the same file is spliced (the line count
    shifts).

    The match is keyed first on the original function text, then falls back to
    a unique name match. Returns the up-to-date FunctionInfo,
    or None if the function can no longer be located.

    Args:
        source (str): The current contents of the file.
        function_info (FunctionInfo): The function to relocate, as captured at
            scan time (its ``source`` and ``name`` are used as match keys).

    Returns:
        Optional[FunctionInfo]: The function's current location, or None.
    """

    candidates = extract_functions(source)

    by_source = [
        fn for fn in candidates if fn['source'] == function_info['source']
    ]
    if len(by_source) == 1:
        return by_source[0]

    by_name = [fn for fn in candidates if fn['name'] == function_info['name']]
    if len(by_name) == 1:
        return by_name[0]

    return None


def find_enclosing_function(source: str, line_number: int) -> FunctionInfo:
    """
    Find the function that encloses a given line number in the source code.

    Args:
        source (str): The source code file.
        line_number (int): The line number to find the enclosing function for.

    Returns:
        FunctionInfo: The information about the enclosing function. If no
            enclosing function is found (i.e. issue is the global scope),
            ten lines above and ten lines below the line number are returned
            as the function information, with the name 'global_scope'.
    """

    functions = extract_functions(source)
    for function in functions:
        if function['start_line'] <= line_number <= function['end_line']:
            return function

    lines = source.splitlines()
    start_line = max(0, line_number - 10)
    end_line = min(len(lines) - 1, line_number + 10)
    source_slice = '\n'.join(lines[start_line : end_line + 1])
    return FunctionInfo(
        name='global_scope',
        start_line=start_line,
        end_line=end_line,
        source=source_slice,
        LOC=end_line - start_line + 1,
    )
