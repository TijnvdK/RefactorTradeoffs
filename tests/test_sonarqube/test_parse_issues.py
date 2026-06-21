import json
import tempfile
from pathlib import Path
from src.sonarqube.parse_issues import (
    parse_sonarqube_debt_string,
    write_sonarqube_issues_to_disk,
)


class TestParseIssues:
    def test_parse_debt_string(self):
        assert parse_sonarqube_debt_string(None) == 0
        assert parse_sonarqube_debt_string('2h 30min') == 150
        assert parse_sonarqube_debt_string('30min') == 30

    def test_write_sonarqube_issues_to_disk(self, mocker):
        mock_issues = [
            {
                'rule': 'python:S1234',
                'severity': 'MAJOR',
                'component': 'my_project:src/module.py',
                'line': 42,
                'debt': '2h 30min',
                'message': 'This is a major issue',
            },
            {
                'rule': 'python:S5678',
                'severity': 'MINOR',
                'component': 'my_project:src/other.py',
                'line': 10,
                'debt': '30min',
                'message': 'This is a minor issue',
            },
        ]

        mocker.patch(
            'src.sonarqube.parse_issues._fetch_all_pages',
            return_value=mock_issues,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'test_issues.json'
            write_sonarqube_issues_to_disk(output_path=output_path)

            assert output_path.exists()
            with open(output_path, 'r') as f:
                written_issues = json.load(f)

            assert len(written_issues) == 2
            assert written_issues[0]['rule_key'] == 'python:S1234'
            assert written_issues[0]['severity'] == 'MAJOR'
            assert written_issues[0]['file_path'] == 'my_project:src/module.py'
            assert written_issues[0]['line'] == 42
            assert written_issues[0]['debt_minutes'] == 150
            assert written_issues[0]['message'] == 'This is a major issue'

            assert written_issues[1]['rule_key'] == 'python:S5678'
            assert written_issues[1]['severity'] == 'MINOR'
            assert written_issues[1]['line'] == 10
            assert written_issues[1]['debt_minutes'] == 30
