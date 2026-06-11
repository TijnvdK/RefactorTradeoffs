from json import dumps as json_dumps
from typing import List, Optional

### Xdebug trace column definitions ###

TRACE_ENTRY_TYPE = 2
FUNCTION_NAME = 5
IS_USER_DEFINED = 6

### Parser ###


def parse_xdebug_trace(
    trace_file_path: str,
    output_path: Optional[str] = None,
    prefixes_to_keep: Optional[List[str]] = None,
) -> None:
    """
    Parse an Xdebug trace file and output the results in JSONL format.

    Args:
        *trace_file_path (str): The path to the Xdebug trace file.
        output_path (Optional[str]): The path to the output file. If not
            provided, the current directory will be used.
        prefixes_to_keep (Optional[List[str]]): A list of function name prefixes
            to keep. If provided, only functions whose names start with
            any of the specified prefixes will be included in the output.
            If not provided, all functions will be included.
    """
    counts = {}

    # latin-1 encoding seems to be necessary to properly read Xdebug trace
    # files, since they may contain non-UTF-8 characters.
    with open(trace_file_path, 'rt', encoding='latin-1') as file_:
        for line in file_:
            parts = line.split('\t')

            # Check if the lines contains at least 7 columns (with zero index),
            # meaning it contains the necessary information for our analysis:
            # 1. The entry type (column 2) should be '0'
            #    (indicating a function call instead of function exit).
            # 2. The function should be user-defined (column 6 should be '1').
            if len(parts) <= 6:
                continue
            if (
                parts[TRACE_ENTRY_TYPE].strip() != '0'
                or parts[IS_USER_DEFINED].strip() != '1'
            ):
                continue

            function_name = parts[FUNCTION_NAME].strip()
            if not function_name or (
                prefixes_to_keep
                and not any(
                    function_name.startswith(prefix)
                    for prefix in prefixes_to_keep
                )
            ):
                continue

            counts[function_name] = counts.get(function_name, 0) + 1

    output_file_path = output_path or 'xdebug_trace_output.jsonl'
    with open(output_file_path, 'w', encoding='utf-8') as f:
        for function_name, count in counts.items():
            f.write(
                f'{json_dumps({"count": count, "function_name": function_name})}\n'
            )


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description='Parse Xdebug trace files and output JSONL.'
    )
    parser.add_argument(
        '--trace-file', help='Path to the Xdebug trace file', required=True
    )
    parser.add_argument(
        '--output',
        help='Path to the output JSONL file (optional)',
        default=None,
    )
    parser.add_argument(
        '--prefixes-to-keep',
        action='append',
        help='List of function name prefixes to keep (optional)',
        default=None,
    )
    args = parser.parse_args()

    parse_xdebug_trace(
        trace_file_path=args.trace_file,
        output_path=args.output,
        prefixes_to_keep=args.prefixes_to_keep,
    )
