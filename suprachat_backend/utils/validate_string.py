FORBIDDEN_CHARS = " ,*?.!:<>'\";#~&@%+-"


def validate_string(string: str) -> bool:
    """Validates the length of 'string' and checks for forbidden characters."""
    contains_forbidden_chars = False
    for char in FORBIDDEN_CHARS:
        if char in string:
            contains_forbidden_chars = True
            break

    return not contains_forbidden_chars and (len(string) > 0) and (len(string) < 300)
