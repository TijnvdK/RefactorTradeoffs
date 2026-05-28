from src.refactoring.verifiers.engineblock_verifier import _parse_phpunit_output


class TestEngineblockVerifier:
    def test__parse_phpunit_output_empty(self):
        assert _parse_phpunit_output('') == ''

    def test__parse_phpunit_output_no_failures(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuites>
            <testsuite name="Suite1">
                <testcase class="TestClass1" name="test1"/>
                <testcase class="TestClass1" name="test2"/>
            </testsuite>
        </testsuites>"""
        assert _parse_phpunit_output(xml) == ''

    def test__parse_phpunit_output_with_failures(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <testsuites>
            <testsuite name="Suite1">
                <testcase class="TestClass1" name="test1" file="/path/to/file1.php" line="10">
                    <failure>Failure message 1</failure>
                </testcase>
                <testcase class="TestClass1" name="test2" file="/path/to/file2.php" line="20">
                    <failure>Failure message 2</failure>
                </testcase>
            </testsuite>
        </testsuites>"""
        expected = (
            'file1.php:10 (TestClass1):\n\tFailure message 1\n'
            'file2.php:20 (TestClass1):\n\tFailure message 2'
        )
        assert _parse_phpunit_output(xml) == expected
