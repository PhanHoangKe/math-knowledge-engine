"""Structured exceptions for the Safe Mathematical Parser and Normalizer."""


class ParserError(Exception):
    """Base exception for all parsing and validation failures."""

    def __init__(self, message: str, position: int | None = None):
        super().__init__(message)
        self.message = message
        self.position = position

    def to_dict(self) -> dict:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "position": self.position,
        }


class InputLengthExceededError(ParserError):
    """Raised when the raw input length exceeds configured limit."""
    pass


class TokenCountExceededError(ParserError):
    """Raised when the number of tokens exceeds configured limit."""
    pass


class ASTDepthExceededError(ParserError):
    """Raised when the AST depth exceeds recursion or nesting limit."""
    pass


class NodeCountExceededError(ParserError):
    """Raised when the total AST node count exceeds limit."""
    pass


class CoefficientMagnitudeError(ParserError):
    """Raised when numeric constants exceed maximum allowed magnitude."""
    pass


class InvalidExponentError(ParserError):
    """Raised when exponent is negative, non-integer, or exceeds max degree."""
    pass


class OutOfScopeSyntaxError(ParserError):
    """Raised when input contains symbols or functions outside DEV-01 scope."""
    pass


class InvalidSyntaxError(ParserError):
    """Raised when syntax does not conform to the finite grammar."""
    pass
