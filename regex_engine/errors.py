class RegexSyntaxError(ValueError):
    """Raised for an invalid pattern. `position` is the 0-based index in the pattern."""

    def __init__(self, message: str, position: int):
        super().__init__(f"{message} (at position {position})")
        self.message = message
        self.position = position
