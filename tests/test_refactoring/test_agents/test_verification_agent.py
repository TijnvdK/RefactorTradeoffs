from json import dumps as json_dumps, loads as json_loads
from pathlib import Path

from src.refactoring.agents.verification_agent import verification_agent


class TestVerificationAgent:
    def test_verification_agent_skip_empty_code_records(self, tmp_path, mocker):
        input_path = tmp_path / 'input.json'
        output_path = tmp_path / 'output.json'
        original_code_path = tmp_path / 'original.php'

        original_code_path.write_text('<?php echo "original code";')

        input_path.write_text(
            json_dumps(
                [
                    {
                        'model': '',
                        'php_file': '',
                        'code': '',
                        'energy_consumed_refactor': 1.0,
                        'total_energy_consumed': 1.0,
                        'amount_of_refactoring_retries': 1,
                        'error_output': None,
                    }
                ]
            )
        )

        verifier = mocker.Mock()
        result = verification_agent(
            input_path, output_path, original_code_path, verifier
        )

        assert result is True
        verifier.assert_not_called()

    def test_verification_agent(self, tmp_path, mocker):
        input_path = tmp_path / 'input.json'
        output_path = tmp_path / 'output.json'
        original_code_path = tmp_path / 'original.php'

        original_code_path.write_text('<?php echo "original code";')

        input_path.write_text(
            json_dumps(
                [
                    {
                        'model': '',
                        'php_file': '',
                        'code': '<?php echo "refactored code";',
                        'energy_consumed_refactor': 1.0,
                        'total_energy_consumed': 1.0,
                        'amount_of_refactoring_retries': 1,
                        'error_output': None,
                    }
                ]
            )
        )

        verifier = mocker.Mock()
        verifier.return_value = (False, 'Syntax error')

        result = verification_agent(
            input_path, output_path, original_code_path, verifier
        )

        assert result is False
        verifier.assert_called_once_with(
            original_code_path, Path(''), '<?php echo "refactored code";'
        )

        output_records = json_loads(output_path.read_text())
        assert len(output_records) == 1
        assert output_records[0]['error_output'] == 'Syntax error'
