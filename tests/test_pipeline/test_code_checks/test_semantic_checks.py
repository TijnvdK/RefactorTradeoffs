from unittest.mock import MagicMock
from src.pipeline.code_checks.semantic_checks import semantic_check_php


class TestSemanticCheckPHP:
    def test_valid_php_code(self, mocker):
        code = '<?php echo "Hello, World!";'
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b''
        mocker.patch(
            'src.pipeline.code_checks.semantic_checks.subprocess_run',
            return_value=mock_result,
        )
        mocker.patch(
            'src.pipeline.code_checks.semantic_checks.settings.job_dir', '/tmp'
        )
        result = semantic_check_php(code)
        assert result[0] is True

    def test_invalid_php_code(self, mocker):
        code = '<?php echo "Hello, World!"'
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = b'Code contains syntax errors.'
        mock_result.stderr = b''
        mocker.patch(
            'src.pipeline.code_checks.semantic_checks.subprocess_run',
            return_value=mock_result,
        )
        mocker.patch(
            'src.pipeline.code_checks.semantic_checks.settings.job_dir', '/tmp'
        )
        result = semantic_check_php(code)
        assert result[0] is False
        assert result[1] == 'Code contains syntax errors.'
