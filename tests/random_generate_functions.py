def generate_random_string(length: int) -> str:
    """
    Generate a random string with specified length.

    Args:
        length (int): The desired length of the random string.

    Returns:
        str: The generated random string.
    """

    from secrets import choice
    from string import ascii_letters, digits

    return ''.join(choice(ascii_letters + digits) for _ in range(length))


def generate_random_float() -> float:
    """
    Generate a random float between 0 and 1.

    Returns:
        float: The generated random float.
    """

    from secrets import SystemRandom

    return SystemRandom().random()


def generate_random_integer() -> int:
    """
    Generate a random integer between 0 and sys.maxsize.

    Returns:
        int: The generated random integer.
    """

    from secrets import SystemRandom
    from sys import maxsize

    return SystemRandom().randint(0, maxsize)
