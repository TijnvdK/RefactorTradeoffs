from src.pipeline.utils import file_to_str_gen, parse_refactored_code
from tests.random_generate_functions import generate_random_string


class TestFileToStrGen:
    def test_file_to_str_gen(self, tmp_path):
        file1 = tmp_path / 'file1.txt'
        file2 = tmp_path / 'file2.txt'
        file3 = tmp_path / 'file3.md'

        file1.write_text('Content of file 1')
        file2.write_text('Content of file 2')
        file3.write_text('Content of file 3')

        gen = file_to_str_gen(tmp_path, '.txt')
        contents = list(gen)

        assert len(contents) == 2

        file_contents = [content[1] for content in contents]
        assert 'Content of file 1' in file_contents
        assert 'Content of file 2' in file_contents
        assert 'Content of file 3' not in file_contents


class TestParseRefactoredCode:
    ### Case 1: ```{code}``` with and without {language} tag ###
    def test_case_1_no_language(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(f'```{random_string}```') == random_string

    def test_case_1_with_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```python\n{random_string}```')
            == random_string
        )

    def test_case_1_multiline(self):
        random_string = (
            generate_random_string(20)
            + '\n'
            + generate_random_string(20)
            + '\n'
            + generate_random_string(20)
        )
        assert (
            parse_refactored_code(f'```python\n{random_string}```')
            == random_string
        )

    ### Case 2: ```\n{code}\n``` with and without {language} tag ###
    def test_case_2_no_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```\n{random_string}\n```') == random_string
        )

    def test_case_2_with_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```python\n{random_string}\n```')
            == random_string
        )

    def test_case_2_multiline(self):
        random_string = (
            generate_random_string(20)
            + '\n'
            + generate_random_string(20)
            + '\n'
            + generate_random_string(20)
        )
        assert (
            parse_refactored_code(f'```python\n{random_string}\n```')
            == random_string
        )

    ### Case 3: ```\n{code}``` with and without {language} tag ###
    def test_case_3_no_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```\n{random_string}```') == random_string
        )

    def test_case_3_with_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```python\n{random_string}```')
            == random_string
        )

    def test_case_3_multiline(self):
        random_string = (
            generate_random_string(20)
            + '\n'
            + generate_random_string(20)
            + '\n'
            + generate_random_string(20)
        )
        assert (
            parse_refactored_code(f'```python\n{random_string}```')
            == random_string
        )

    ### Case 4: ```{code}\n``` with and without {language} tag ###
    def test_case_4_no_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```{random_string}\n```') == random_string
        )

    def test_case_4_with_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```python\n{random_string}\n```')
            == random_string
        )

    def test_case_4_multiline(self):
        random_string = (
            generate_random_string(20)
            + '\n'
            + generate_random_string(20)
            + '\n'
            + generate_random_string(20)
        )
        assert (
            parse_refactored_code(f'```python\n{random_string}\n```')
            == random_string
        )

    ### Case 5: ```\n{code} with and without {language} tag and newline ###
    def test_case_5_no_language(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(f'```\n{random_string}') == random_string

    def test_case_5_with_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```python\n{random_string}')
            == random_string
        )

    def test_case_5_multiline(self):
        random_string = (
            generate_random_string(20) + '\n' + generate_random_string(20)
        )
        assert (
            parse_refactored_code(f'```python\n{random_string}')
            == random_string
        )

    def test_case_5_no_newline(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(f'```{random_string}') == random_string

    ### Case 6: {code}\n``` with and without newline ###
    def test_case_6(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(f'{random_string}\n```') == random_string

    def test_case_6_multiline(self):
        random_string = (
            generate_random_string(20) + '\n' + generate_random_string(20)
        )
        assert parse_refactored_code(f'{random_string}\n```') == random_string

    def test_case_6_no_newline(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(f'{random_string}```') == random_string

    ### No code fences ###
    def test_no_fences(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(random_string) == random_string

    def test_no_fences_empty_string(self):
        assert parse_refactored_code('') == ''

    def test_no_fences_plain_text(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(random_string) == random_string

    ### Code fences around text ###
    def test_fences_around_text(self):
        random_text = generate_random_string(20)
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'{random_text}```{random_string}```')
            == random_string
        )
        assert (
            parse_refactored_code(f'```{random_string}```{random_text}')
            == random_string
        )
        assert (
            parse_refactored_code(
                f'{random_text}```{random_string}```{random_text}'
            )
            == random_string
        )

    ### Multiple code fences ###
    def test_multiple_code_fences(self):
        random_string_1 = generate_random_string(20)
        random_string_2 = generate_random_string(20)
        assert (
            parse_refactored_code(
                f'```{random_string_1}``````{random_string_2}```'
            )
            == random_string_1
        )

    ### Edge cases ###
    def test_priority(self):
        random_string_1 = generate_random_string(20)
        random_string_2 = generate_random_string(20)
        assert (
            parse_refactored_code(f'{random_string_1}```{random_string_2}```')
            == random_string_2
        )

    def test_with_whitespace_as_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'``` \n{random_string}\n```')
            == random_string
        )

    def test_opening_fence_with_no_code(self):
        assert parse_refactored_code('```\n') == ''
