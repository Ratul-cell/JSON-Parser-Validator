"""
Recursive Descent Parser for JSON
==================================
This is the heart of the project. JSON's grammar (RFC 8259) is:

    value    ::= object | array | string | number | "true" | "false" | "null"
    object   ::= "{" ( pair ( "," pair )* )? "}"
    pair     ::= string ":" value
    array    ::= "[" ( value ( "," value )* )? "]"
    string   ::= '"' characters '"'
    number   ::= '-'? int frac? exp?

A recursive descent parser turns each grammar rule into a function of the
same name, and each function calls the functions for the rules on the
right-hand side. The parser looks at the *current* token (one token of
lookahead) to decide which production applies -- that's why parse_value
can look at '{' and know to call parse_object, or see a string/number and
consume it directly.

Because JSON is recursive (objects contain values, values can be objects),
the call graph mirrors that recursion:

    parse_value -> parse_object -> parse_pair -> parse_value -> ...
    parse_value -> parse_array  -> parse_value -> ...

Each nested '{' or '[' in the input adds a frame to the call stack, so the
maximum nesting depth of a JSON document is bounded by Python's recursion
limit (this mirrors real-world parsers, which usually impose an explicit
depth limit for the same reason -- see MAX_DEPTH below).
"""

from lexer import Lexer, TokenType

MAX_DEPTH = 500  # guards against pathological/malicious deeply-nested input


class ParseError(Exception):
    def __init__(self, message, line, col):
        super().__init__(f"Parse error at line {line}, column {col}: {message}")
        self.line = line
        self.col = col


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.depth = 0

    @property
    def _current(self):
        return self.tokens[self.pos]

    def _advance(self):
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def _expect(self, type_):
        tok = self._current
        if tok.type != type_:
            raise ParseError(
                f"Expected {type_} but found {tok.type} ({tok.value!r})",
                tok.line, tok.col,
            )
        return self._advance()

    # --- entry point -----------------------------------------------------
    def parse(self):
        if self._current.type == TokenType.EOF:
            raise ParseError("Empty input: no JSON value found", 1, 1)
        value = self.parse_value()
        if self._current.type != TokenType.EOF:
            tok = self._current
            raise ParseError(
                f"Unexpected trailing data starting with {tok.type}",
                tok.line, tok.col,
            )
        return value

    # --- value ::= object | array | string | number | true | false | null
    def parse_value(self):
        self.depth += 1
        if self.depth > MAX_DEPTH:
            tok = self._current
            raise ParseError(
                f"Maximum nesting depth ({MAX_DEPTH}) exceeded", tok.line, tok.col,
            )
        try:
            tok = self._current
            if tok.type == TokenType.LBRACE:
                return self.parse_object()
            elif tok.type == TokenType.LBRACKET:
                return self.parse_array()
            elif tok.type == TokenType.STRING:
                self._advance()
                return tok.value
            elif tok.type == TokenType.NUMBER:
                self._advance()
                return tok.value
            elif tok.type == TokenType.TRUE:
                self._advance()
                return True
            elif tok.type == TokenType.FALSE:
                self._advance()
                return False
            elif tok.type == TokenType.NULL:
                self._advance()
                return None
            else:
                raise ParseError(
                    f"Unexpected token {tok.type} ({tok.value!r}); expected a value",
                    tok.line, tok.col,
                )
        finally:
            self.depth -= 1

    # --- object ::= "{" ( pair ( "," pair )* )? "}"
    def parse_object(self):
        self._expect(TokenType.LBRACE)
        obj = {}
        if self._current.type == TokenType.RBRACE:
            self._advance()
            return obj

        key, value = self.parse_pair()
        obj[key] = value
        while self._current.type == TokenType.COMMA:
            self._advance()
            if self._current.type == TokenType.RBRACE:
                tok = self._current
                raise ParseError("Trailing comma before '}'", tok.line, tok.col)
            key, value = self.parse_pair()
            obj[key] = value

        self._expect(TokenType.RBRACE)
        return obj

    # --- pair ::= string ":" value
    def parse_pair(self):
        tok = self._current
        if tok.type != TokenType.STRING:
            raise ParseError(
                f"Expected string key but found {tok.type}", tok.line, tok.col,
            )
        key = self._advance().value
        self._expect(TokenType.COLON)
        value = self.parse_value()
        return key, value

    # --- array ::= "[" ( value ( "," value )* )? "]"
    def parse_array(self):
        self._expect(TokenType.LBRACKET)
        arr = []
        if self._current.type == TokenType.RBRACKET:
            self._advance()
            return arr

        arr.append(self.parse_value())
        while self._current.type == TokenType.COMMA:
            self._advance()
            if self._current.type == TokenType.RBRACKET:
                tok = self._current
                raise ParseError("Trailing comma before ']'", tok.line, tok.col)
            arr.append(self.parse_value())

        self._expect(TokenType.RBRACKET)
        return arr


def parse_json(text):
    """Tokenize and parse `text`, returning the resulting Python object."""
    tokens = Lexer(text).tokenize()
    return Parser(tokens).parse()
