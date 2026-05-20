class LMCallFailed(Exception):
    """
    Exception raised when a call to the language model fails; the expected
    output is not received.
    """

    def __init__(self):
        """
        Create an instance of the LMCallFailed class.
        """
        super().__init__(
            'Call to the language model failed; '
            'the expected output was not received.'
        )
