import pytest

from src.pipeline.llm_context.tree_parser import (
    extract_functions,
    find_enclosing_function,
    splice_function,
)


class TestTreeParser:
    @pytest.fixture
    def php_code_with_functions(self):
        return """<?php
        function add($a, $b) {
            return $a + $b;
        }

        function subtract($a, $b) {
            return $a - $b;
        }
        ?>
        """

    def test_extract_functions_empty(self):
        functions = extract_functions('')
        assert functions == []

    def test_extract_functions(self, php_code_with_functions):
        functions = extract_functions(php_code_with_functions)
        assert len(functions) == 2
        assert functions[0]['name'] == 'add'
        assert functions[1]['name'] == 'subtract'

    def test_splice_function(self, php_code_with_functions):

        functions = extract_functions(php_code_with_functions)
        new_function = """function add($a, $b) {
            return $a + $b + 1; // Modified
        }"""
        updated_code = splice_function(
            php_code_with_functions, functions[0], new_function
        )
        assert 'return $a + $b + 1;' in updated_code

    def test_find_enclosing_function(self, php_code_with_functions):
        enclosing_function = find_enclosing_function(php_code_with_functions, 3)
        assert enclosing_function['name'] == 'add'
