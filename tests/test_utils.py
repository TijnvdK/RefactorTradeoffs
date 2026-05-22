from src.utils import file_to_str_gen


class TestUtils:
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
        assert 'Content of file 1' in contents
        assert 'Content of file 2' in contents
        assert 'Content of file 3' not in contents
