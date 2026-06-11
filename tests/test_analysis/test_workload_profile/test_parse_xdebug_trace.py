from pathlib import Path
from tempfile import TemporaryDirectory


class TestParseXdebugTrace:
    def test_parse_invalid_xdebug_trace(self):
        from src.repository_analysis.workload_profile.parse_xdebug_trace import (
            parse_xdebug_trace,
        )

        with TemporaryDirectory() as temp_dir:
            temp_file_path = Path(temp_dir) / 'temp_invalid_trace.xt'
            temp_file_path.write_text('This is not a valid Xdebug trace file.')

            output_file_path = Path(temp_dir) / 'output.jsonl'
            parse_xdebug_trace(
                str(temp_file_path), output_path=str(output_file_path)
            )

            assert output_file_path.exists()
            output_content = output_file_path.read_text()
            # Expecting an empty output for invalid trace file
            assert output_content == ''

    def test_parse_xdebug_trace(self):
        from src.repository_analysis.workload_profile.parse_xdebug_trace import (
            parse_xdebug_trace,
        )

        with TemporaryDirectory() as temp_dir:
            temp_file_path = Path(temp_dir) / 'temp_valid_trace.xt'
            # A minimal file that is valid according to our parsing logic.
            temp_file_path.write_text(
                '1\t0\t0\t0\t0\tfunction\t1\n'  # Valid
                '2\t0\t0\t0\t0\tfunction\t1\n'  # Valid
                '3\t0\t0\t0\t0\totherFunction\t0\n'  # Not user defined
                '4\t0\t1\t0\t0\totherOtherFunction\t1\n'  # Not a function call
            )

            output_file_path = Path(temp_dir) / 'output.jsonl'
            parse_xdebug_trace(
                str(temp_file_path), output_path=str(output_file_path)
            )

            assert output_file_path.exists()
            output_content = output_file_path.read_text()
            # Expecting counts for myFunction and otherFunction
            assert output_content == (
                '{"count": 2, "function_name": "function"}\n'
            )
            assert 'otherFunction' not in output_content
            assert 'otherOtherFunction' not in output_content
