from logging import getLogger
from re import compile as re_compile, DOTALL as re_DOTALL

logger = getLogger(__name__)

_CODE_FENCED = re_compile(
    r'(`{3,})(?:[^\n`]+\n(?!\1)|\n?)(.*?)(?:\n?\1|$)', re_DOTALL
)
_CODE_TRAILING_FENCH = re_compile(r'^(.*?)\n?```', re_DOTALL)


def parse_refactored_code(raw_output: str) -> str:
    r"""
    Parses the raw output from the LLM to extract the refactored code snippet.
    The function considers the following cases (the function extracts {code}):
    1. \`\`\`{code}\`\`\` w and w/o {language} tag
    2. \`\`\`\\n{code}\\n\`\`\` w and w/o {language} tag
    3. \`\`\`\\n{code}\`\`\` w and w/o {language} tag
    4. \`\`\`{code}\\n\`\`\` w and w/o {language} tag
    5. \`\`\`\\n{code} w and w/o {language} tag and newline
    6. {code}\\n\`\`\` w and w/o newline
    The function tries to parse on order of priority. Where case 1 has the
    highest priority and case 6 the lowest.

    Limitations:
    - The function always retrieves the first code snippet if multiple code
        snippets are present in the raw output.
    - In case 5, it will retrieve everything after the opening code fence.
    - The correctness of the function is not guaranteed with nested code fences.
    - The function returns the code exactly as is, without any additional
        formatting or cleanup.

    Args:
        raw_output (str): String with a supposed code snippet,
            possibly with code fences.

    Returns:
        str: The extracted code snippet without code fences, or the original
            string if no code fences are found.
    """

    match = _CODE_FENCED.search(raw_output)
    if match and not (
        match.group(2) == ''
        and match.start() > 0
        and match.end() == len(raw_output)
    ):
        return match.group(2)

    match = _CODE_TRAILING_FENCH.search(raw_output)
    if match:
        return match.group(1)

    return raw_output
