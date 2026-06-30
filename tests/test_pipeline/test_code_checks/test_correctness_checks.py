from src.pipeline.code_checks.correctness_checks.engineblock import (
    parse_and_format_eb_test_results,
)


class TestCorrectnessCheckEB:
    def test_eb_empty_directory_returns_empty_string(self, tmp_path):
        result = parse_and_format_eb_test_results(str(tmp_path))
        assert isinstance(result, str)
        assert result == ''

    def test_eb_no_matching_files_returns_empty_string(self, tmp_path):
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
    <testsuite name="unit" tests="1">
        <testcase name="test_failure">
            <failure type="Error">This should be ignored.</failure>
        </testcase>
    </testsuite>
</testsuites>
        """
        (tmp_path / 'wrong-prefix.xml').write_text(xml_content)

        result = parse_and_format_eb_test_results(str(tmp_path))
        assert result == ''

    def test_eb_all_passing_tests_produce_empty_string(self, tmp_path):
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
    <testsuite name="unit" tests="2">
        <testcase name="test_success_one" />
        <testcase name="test_success_two" />
    </testsuite>
</testsuites>
        """
        (tmp_path / 'phpunit-unit.xml').write_text(xml_content)

        result = parse_and_format_eb_test_results(str(tmp_path))
        assert result == ''

    def test_eb_failures_format_correctly(self, tmp_path):
        integration_xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
    <testsuite>
        <testcase name="test_integration_error">
            <error type="RuntimeError">Integration Error Detail</error>
        </testcase>
        <testcase name="test_integration_success" />
    </testsuite>
</testsuites>
        """

        unit_xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
    <testsuite>
        <testcase name="test_unit_failure_one">
            <failure type="AssertionError">Unit Failure 1</failure>
        </testcase>
        <testcase name="test_unit_failure_two">
            <failure type="AssertionError">Unit Failure 2
Line 2</failure>
        </testcase>
    </testsuite>
</testsuites>
        """

        (tmp_path / 'phpunit-integration.xml').write_text(integration_xml)
        (tmp_path / 'phpunit-unit.xml').write_text(unit_xml)

        expected = (
            'SUITE:  integration\n'
            'TEST:   test_integration_error\n'
            'Integration Error Detail\n'
            '---\n'
            'SUITE:  unit\n'
            'TEST:   test_unit_failure_one\n'
            'Unit Failure 1\n'
            '---\n'
            'SUITE:  unit\n'
            'TEST:   test_unit_failure_two\n'
            'Unit Failure 2\n'
            'Line 2\n'
            '---\n'
        )

        result = parse_and_format_eb_test_results(str(tmp_path))

        print()
        print(f'Actual result:\n{result}\n\n')
        print(f'Expected result:\n{expected}')

        assert result == expected
