from typing import Optional
from json import dumps as json_dumps, loads as json_loads

from src.refactoring.agents.fix_agent import fix_agent


def _make_code_record(error_output: Optional[str]) -> dict:
    return {
        'model': 'model',
        'php_file': '/tmp/test.php',
        'code': '<?php echo "test";',
        'energy_consumed_refactor': 1.0,
        'energy_consumed_fix': None,
        'total_energy_consumed': 1.0,
        'amount_of_refactoring_retries': None,
        'amount_of_fix_retries': None,
        'error_output': error_output,
    }


class TestFixAgent:
    def test_fix_agent_skips_records_without_error(
        self, tmp_path, mocker, backend_handler
    ):
        input_path = tmp_path / 'input.json'
        output_path = tmp_path / 'output.json'

        input_path.write_text(json_dumps([_make_code_record(None)]))

        mocker.patch('src.refactoring.agents.fix_agent.call_llm')
        mocker.patch('src.refactoring.agents.fix_agent.is_valid_php_code')

        fix_agent(backend_handler, input_path, output_path)

        result = json_loads(output_path.read_text())
        # No energy should've been consumed since the record should be skipped
        assert result[0]['energy_consumed_fix'] is None
        assert result[0]['total_energy_consumed'] == 1.0
        assert result[0]['amount_of_fix_retries'] is None

    def test_fix_agent(self, tmp_path, mocker, backend_handler):
        input_path = tmp_path / 'input.json'
        output_path = tmp_path / 'output.json'

        input_path.write_text(json_dumps([_make_code_record('Big error')]))

        call_llm = mocker.patch('src.refactoring.agents.fix_agent.call_llm')
        call_llm.side_effect = [
            ('<?php echo "invalid";', 1.0),
            ('<?php echo "valid";', 2.0),
        ]
        is_valid = mocker.patch(
            'src.refactoring.agents.fix_agent.is_valid_php_code'
        )
        is_valid.side_effect = [False, True]

        fix_agent(backend_handler, input_path, output_path)

        result = json_loads(output_path.read_text())
        assert len(result) == 1
        assert result[0]['code'] == '<?php echo "valid";'
        assert result[0]['energy_consumed_fix'] == 2.0
        assert result[0]['total_energy_consumed'] == 4.0
        assert result[0]['amount_of_fix_retries'] == 2

    def test_fix_agent_max_attempts(self, tmp_path, mocker, backend_handler):
        input_path = tmp_path / 'input.json'
        output_path = tmp_path / 'output.json'

        input_path.write_text(json_dumps([_make_code_record('Big error')]))

        call_llm = mocker.patch('src.refactoring.agents.fix_agent.call_llm')
        call_llm.return_value = ('<?php echo "invalid";', 1.0)
        is_valid = mocker.patch(
            'src.refactoring.agents.fix_agent.is_valid_php_code'
        )
        is_valid.return_value = False

        fix_agent(backend_handler, input_path, output_path, max_attempts=3)

        result = json_loads(output_path.read_text())
        assert len(result) == 1
        assert result[0]['code'] == ''
        assert result[0]['energy_consumed_fix'] == 1.0
        assert result[0]['total_energy_consumed'] == 4.0
        assert result[0]['amount_of_fix_retries'] is None
        assert call_llm.call_count == 3
