class LLMCallFailed(Exception):
    """
    Exception raised when a call to the language model fails; the expected
    output is not received.
    """

    def __init__(self, message=None):
        """
        Create an instance of the LMCallFailed class.
        """
        super().__init__(
            'Call to the language model failed.\n' + message
            if message
            else 'The expected output was not received.'
        )
