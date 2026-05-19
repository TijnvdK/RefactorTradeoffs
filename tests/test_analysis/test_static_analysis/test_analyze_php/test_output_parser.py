from pathlib import Path

import pytest


@pytest.fixture
def base_path():
    _cwd = Path.cwd()
    return (
        _cwd
        / 'analysis'
        / 'static_analysis'
        / 'analyze_php'
        / 'outputs'
        / 'raw_output'
        / 'example_php_code_dir'
    )


class TestOutputParser:
    def test_parse_pdepend(self, base_path):
        from analysis.static_analysis.analyze_php.output_parser import (
            parse_pdepend,
        )

        parsed_output = parse_pdepend(str(base_path / 'pdepend.xml'))

        all_methods = [method['method_name'] for method in parsed_output]
        assert len(all_methods) == 3  # We have three methods
        assert 'add' in all_methods
        assert 'multiply' in all_methods

        first_method = parsed_output[0]
        expected_keys = {
            'file_path',
            'method_name',
            'start_line',
            'end_line',
            'cc',
            'mi',
            'halstead_difficulty',
        }

        assert expected_keys.issubset(first_method.keys())

    def test_parse_phpcs(self, base_path):
        from analysis.static_analysis.analyze_php.output_parser import (
            parse_phpcs,
        )

        parsed_output = parse_phpcs(str(base_path / 'phpcs.xml'))

        assert len(parsed_output) == 1

        parsed_output = next(iter(parsed_output.values()))
        all_errors = sum(
            1 for output in parsed_output if output['type'] == 'error'
        )
        assert all_errors > 0
        all_warnings = sum(
            1 for output in parsed_output if output['type'] == 'warning'
        )
        assert all_warnings > 0

    def test_parse_phpmd(self, base_path):
        from analysis.static_analysis.analyze_php.output_parser import (
            parse_phpmd,
        )

        parsed_output = parse_phpmd(str(base_path / 'phpmd.xml'))

        assert len(parsed_output) == 1

        parsed_output = next(iter(parsed_output.values()))
        assert len(parsed_output) > 0

    def test_phpmetrics(self, base_path):
        from analysis.static_analysis.analyze_php.output_parser import (
            parse_phpmetrics,
        )

        parsed_output = parse_phpmetrics(str(base_path / 'phpmetrics.csv'))

        assert len(parsed_output) == 2  # We have two classes

        parsed_output = next(iter(parsed_output.values()))
        assert len(parsed_output) > 0

        expected_keys = {
            'cc',
            'mi',
            'halstead_difficulty',
        }
        assert expected_keys.issubset(parsed_output.keys())
