from json import dumps as json_dumps


def parse_xdebug_trace(trace_file_path: str) -> None:
    """
    Parse an Xdebug trace file and output the results in JSONL format.

    Args:
        trace_file_path (str): The path to the Xdebug trace file.
    """
    counts = {}
    with open(trace_file_path, 'rt', encoding='latin-1') as file_:
        for line in file_:
            parts = line.split('\t')

            if len(parts) <= 6:
                continue
            if parts[2].strip() != '0' or parts[6].strip() != '1':
                continue

            function_name = parts[5].strip()
            if not function_name:
                continue

            counts[function_name] = counts.get(function_name, 0) + 1

    with open('xdebug_trace_output.jsonl', 'w', encoding='utf-8') as f:
        for functions, count in counts.items():
            f.write(f'{json_dumps({"count": count, "functions": functions})}\n')


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description='Parse Xdebug trace files and output JSONL.'
    )
    parser.add_argument('trace_file', help='Path to the Xdebug trace file')
    args = parser.parse_args()

    parse_xdebug_trace(args.trace_file)
