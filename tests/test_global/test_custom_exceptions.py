from src.globals.custom_exceptions import LLMCallFailed


class TestCustomExceptions:
    def test_LLMCallFailed_with_message(self):
        message = 'The language model did not respond as expected.'
        exception = LLMCallFailed(message)
        assert str(exception) == (
            'Call to the language model failed.\n' + message
        )

    def test_LLMCallFailed_without_message(self):
        exception = LLMCallFailed()
        assert str(exception) == 'The expected output was not received.'
