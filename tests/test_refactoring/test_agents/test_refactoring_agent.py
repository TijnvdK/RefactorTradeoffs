from src.globals.types import UserPrompt
from src.refactoring.agents.refactoring_agent import refactoring_agent
from json import loads as json_loads


class TestRefactoringAgent:
    def test_refactoring_agent(self, tmp_path, mocker, backend_handler):
        models = ['model1', 'model2']
        user_prompts = [
            UserPrompt(prompt='code1', php_file='file1.php'),
            UserPrompt(prompt='code2', php_file='file2.php'),
        ]
        output_path = tmp_path / 'output.json'

        call_llm = mocker.patch(
            'src.refactoring.agents.refactoring_agent.call_llm'
        )
        call_llm.side_effect = [
            ('<?php echo "refactored code1";', 1.0),
            ('<?php echo "refactored code2";', 2.0),
            ('<?php echo "refactored code1";', 1.5),
            ('<?php echo "refactored code2";', 2.5),
        ]

        is_valid = mocker.patch(
            'src.refactoring.agents.refactoring_agent.is_valid_php_code'
        )
        is_valid.return_value = True

        refactoring_agent(
            backend_handler, models, user_prompts, output_path, max_attempts=3
        )

        result = json_loads(output_path.read_text())
        assert len(result) == 4

        assert result[0]['model'] == 'model1'
        assert result[0]['php_file'] == 'file1.php'
        assert result[0]['code'] == '<?php echo "refactored code1";'
        assert result[0]['energy_consumed_refactor'] == 1.0
        assert result[0]['total_energy_consumed'] == 1.0
        assert result[0]['amount_of_refactoring_retries'] == 1

        assert result[1]['model'] == 'model1'
        assert result[1]['php_file'] == 'file2.php'
        assert result[1]['code'] == '<?php echo "refactored code2";'
        assert result[1]['energy_consumed_refactor'] == 2.0
        assert result[1]['total_energy_consumed'] == 2.0
        assert result[1]['amount_of_refactoring_retries'] == 1

        assert result[2]['model'] == 'model2'
        assert result[2]['php_file'] == 'file1.php'
        assert result[2]['code'] == '<?php echo "refactored code1";'
        assert result[2]['energy_consumed_refactor'] == 1.5
        assert result[2]['total_energy_consumed'] == 1.5
        assert result[2]['amount_of_refactoring_retries'] == 1

        assert result[3]['model'] == 'model2'
        assert result[3]['php_file'] == 'file2.php'
        assert result[3]['code'] == '<?php echo "refactored code2";'
        assert result[3]['energy_consumed_refactor'] == 2.5
        assert result[3]['total_energy_consumed'] == 2.5
        assert result[3]['amount_of_refactoring_retries'] == 1
