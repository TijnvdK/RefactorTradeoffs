from typing import List, TypedDict
import tree_sitter_php
from tree_sitter import Language, Node, Parser

_LANGUAGE = Language(tree_sitter_php.language_php())
_PARSER = Parser(_LANGUAGE)

_FUNCTION_NODES = {
    'function_definition',
    'method_declaration',
    'anonymous_function',
    'arrow_function',
}


class FunctionInfo(TypedDict):
    name: str
    start_line: int
    end_line: int
    source: str
    LOC: int


def _collect_functions(
    node: Node, lines: List[str], results: List[FunctionInfo]
) -> None:
    """
    Walk a node tree and retrieve information about function nodes.

    Args:
        node (Node): The root node to start walking from.
        lines (List[str]): The lines of the source code file, used to retrieve
            the source code of each function.
        results (List[FunctionInfo]): A list to store the retrieved function
            information.
    """

    if node.type in _FUNCTION_NODES:
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

    for child in node.children:
        _collect_functions(child, lines, results)


def extract_functions(source: str, min_loc: int = 0) -> List[FunctionInfo]:
    """
    Parse a PHP source code file and retrieve information about every function
    within that PHP source code file.

    Args:
        source (str): The PHP source code file.
        min_loc (int, optional): Only return functions that have at minimum
            this amount of LOC. Defaults to 0.

    Returns:
        List[FunctionInfo]: A list of FunctionInfo objects, each containing
            information about a function in the source code.
    """

    tree = _PARSER.parse(source.encode())
    lines = source.splitlines()

    results: List[FunctionInfo] = []
    _collect_functions(tree.root_node, lines, results)
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


def find_enclosing_function(source: str, line_number: int) -> FunctionInfo:
    """
    Find the function that encloses a given line number in the source code.

    Args:
        source (str): The PHP source code file.
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
