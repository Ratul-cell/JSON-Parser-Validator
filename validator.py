"""
Validator
=========
Thin wrapper around the lexer/parser that turns exceptions into a clean
result object: (is_valid, value_or_none, error_or_none). This is the
piece application code should use directly instead of calling the
lexer/parser internals.
"""

from lexer import Lexer, LexError
from parser import Parser, ParseError


class ValidationResult:
    def __init__(self, is_valid, value=None, error=None):
        self.is_valid = is_valid
        self.value = value
        self.error = error

    def __bool__(self):
        return self.is_valid

    def __repr__(self):
        if self.is_valid:
            return f"ValidationResult(valid, value={self.value!r})"
        return f"ValidationResult(invalid, error={self.error!r})"


def validate(text):
    """Validate a JSON string. Never raises -- always returns a ValidationResult."""
    try:
        tokens = Lexer(text).tokenize()
    except LexError as e:
        return ValidationResult(False, error=str(e))

    try:
        value = Parser(tokens).parse()
    except ParseError as e:
        return ValidationResult(False, error=str(e))
    except RecursionError:
        return ValidationResult(False, error="Input nested too deeply to parse")

    return ValidationResult(True, value=value)
