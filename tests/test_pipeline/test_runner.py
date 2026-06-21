from pathlib import Path

import pytest

from src.pipeline.llm_context.tree_parser import FunctionInfo
from src.pipeline.runner import _build_units_active, _build_units_passive
from json import dumps as json_dumps


@pytest.fixture
def override_min_function_loc(monkeypatch):
    def _set(value: int):
        monkeypatch.setattr('src.settings.settings.min_function_loc', value)

    return _set


class TestBuildUnits:
    def test_build_units_passive_empty(
        self, tmp_path: Path, override_min_function_loc
    ):
        override_min_function_loc(0)

        (tmp_path / 'readme.txt').write_text('This is a readme file.')
        units = _build_units_passive(tmp_path)
        assert units == []

    def test_build_units_passive_single_file_no_functions(
        self, tmp_path: Path, override_min_function_loc
    ):
        override_min_function_loc(0)

        php_file = tmp_path / 'test.php'
        php_file.write_text('<?php\n// This file has no functions.\n')
        units = _build_units_passive(tmp_path)
        assert units == []

    def test_build_units_passive_single_file_single_function(
        self, tmp_path: Path, override_min_function_loc
    ):
        override_min_function_loc(0)

        php_file = tmp_path / 'test.php'
        php_file.write_text(
            '<?php\nfunction testFunction() {\n    return 42;\n}\n'
        )
        units = _build_units_passive(tmp_path)
        assert len(units) == 1
        unit = units[0]
        assert unit['file_path'] == php_file
        assert unit['function_info'] == FunctionInfo(
            name='testFunction',
            start_line=1,
            end_line=3,
            source='function testFunction() {\n    return 42;\n}',
            LOC=3,
        )

    def test_build_units_passive_single_file_multiple_functions(
        self, tmp_path: Path, override_min_function_loc
    ):
        override_min_function_loc(0)

        php_file = tmp_path / 'test.php'
        php_file.write_text(
            '<?php\nfunction firstFunction() {\n    return 1;\n}\n\nfunction secondFunction() {\n    return 2;\n}\n'
        )
        units = _build_units_passive(tmp_path)
        assert len(units) == 2
        assert units[0]['function_info']['name'] == 'firstFunction'
        assert units[1]['function_info']['name'] == 'secondFunction'

    def test_build_units_passive_single_file_short_and_long_functions(
        self, tmp_path: Path, override_min_function_loc
    ):
        override_min_function_loc(4)

        php_file = tmp_path / 'test.php'
        php_file.write_text(
            "<?php\nfunction shortFunction() {\n    return 1;\n}\n\nfunction longFunction() {\n    echo 'line 1';\n    echo 'line 2';\n    echo 'line 3';\n}\n"
        )
        units = _build_units_passive(tmp_path)
        assert len(units) == 1
        assert units[0]['function_info']['name'] == 'longFunction'

    def test_build_units_passive_multiple_files(
        self, tmp_path: Path, override_min_function_loc
    ):
        override_min_function_loc(0)

        php_file1 = tmp_path / 'test1.php'
        php_file1.write_text(
            '<?php\nfunction testFunction1() {\n    return 1;\n}\n'
        )
        php_file2 = tmp_path / 'test2.php'
        php_file2.write_text(
            '<?php\nfunction testFunction2() {\n    return 2;\n}\n'
        )
        units = _build_units_passive(tmp_path)
        assert len(units) == 2

        file_paths = {u['file_path'] for u in units}
        assert file_paths == {php_file1, php_file2}

        unit1 = next(u for u in units if u['file_path'] == php_file1)
        unit2 = next(u for u in units if u['file_path'] == php_file2)
        assert unit1['function_info']['name'] == 'testFunction1'
        assert unit2['function_info']['name'] == 'testFunction2'

    def test_build_units_active_no_issues(self, tmp_path: Path):
        issues_path = tmp_path / 'issues.json'
        issues_path.write_text('[]')

        units = _build_units_active(tmp_path, issues_path)
        assert units == []

    def test_build_units_active_with_issues(self, tmp_path: Path, mocker):
        file1 = tmp_path / 'a.php'
        file2 = tmp_path / 'b.php'
        file1.write_text('<?php function fa() {} ?>')
        file2.write_text('<?php function fb() {} ?>')

        issues = [
            {'file_path': 'a.php', 'line': 1, 'message': 'Issue A'},
            {'file_path': 'b.php', 'line': 2, 'message': 'Issue B'},
        ]
        issues_path = tmp_path / 'issues.json'
        issues_path.write_text(json_dumps(issues))

        mocker.patch(
            'src.pipeline.runner.find_enclosing_function',
            side_effect=[{'name': 'fa'}, {'name': 'fb'}],
        )

        result = _build_units_active(tmp_path, issues_path)

        assert len(result) == 2
        assert result[0]['file_path'] == file1
        assert result[1]['file_path'] == file2
        assert 'Issue A' in result[0]['task']
        assert 'Issue B' in result[1]['task']

    def test_build_units_active_with_enclosing_function(
        self, tmp_path: Path, mocker
    ):
        php_file = tmp_path / 'foo.php'
        content = '<?php function bar() { return 1; } ?>'
        php_file.write_text(content)

        issues = [{'file_path': 'foo.php', 'line': 7, 'message': 'msg'}]
        issues_path = tmp_path / 'issues.json'
        issues_path.write_text(json_dumps(issues))

        mock_find = mocker.patch(
            'src.pipeline.runner.find_enclosing_function', return_value=None
        )

        _build_units_active(tmp_path, issues_path)

        mock_find.assert_called_once_with(content, 7)

    def test_build_units_active_no_enclosing_function(
        self, tmp_path: Path, mocker
    ):
        php_file = tmp_path / 'foo.php'
        php_file.write_text('<?php $x = 1; ?>')

        issues = [{'file_path': 'foo.php', 'line': 1, 'message': 'msg'}]
        issues_path = tmp_path / 'issues.json'
        issues_path.write_text(json_dumps(issues))

        mocker.patch(
            'src.pipeline.runner.find_enclosing_function', return_value=None
        )

        result = _build_units_active(tmp_path, issues_path)

        assert len(result) == 1
        assert result[0]['function_info'] is None
