class UnsupportedOperationError(Exception):
    """
    Exception raised when an unsupported operation is attempted,
    such as calling a method that is not supported by the model.
    """

    def __init__(self, message: str):
        """
        Create an instance of the UnsupportedOperationError class.

        Args:
            message (str): The error message.
        """
        super().__init__(message)


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
