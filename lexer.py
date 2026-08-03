"""
Lexer (Tokenizer) for JSON
==========================
Converts raw JSON text into a stream of Tokens that the recursive-descent
parser consumes. Separating lexing from parsing keeps the parser clean:
it reasons about token *types*, never raw characters.
"""


class TokenType:
    LBRACE = "LBRACE"       # {
    RBRACE = "RBRACE"       # }
    LBRACKET = "LBRACKET"   # [
    RBRACKET = "RBRACKET"   # ]
    COLON = "COLON"         # :
    COMMA = "COMMA"         # ,
    STRING = "STRING"
    NUMBER = "NUMBER"
    TRUE = "TRUE"
    FALSE = "FALSE"
    NULL = "NULL"
    EOF = "EOF"


class Token:
    __slots__ = ("type", "value", "line", "col")

    def __init__(self, type_, value, line, col):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line}, col={self.col})"


class LexError(Exception):
    def __init__(self, message, line, col):
        super().__init__(f"Lex error at line {line}, column {col}: {message}")
        self.line = line
        self.col = col


class Lexer:
    _WHITESPACE = " \t\n\r"
    _ESCAPES = {
        '"': '"', "\\": "\\", "/": "/", "b": "\b",
        "f": "\f", "n": "\n", "r": "\r", "t": "\t",
    }

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(text)

    def _peek(self, offset=0):
        idx = self.pos + offset
        return self.text[idx] if idx < self.length else ""

    def _advance(self):
        ch = self.text[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_whitespace(self):
        while self._peek() != "" and self._peek() in self._WHITESPACE:
            self._advance()

    def tokenize(self):
        tokens = []
        self._skip_whitespace()
        while self.pos < self.length:
            ch = self._peek()
            start_line, start_col = self.line, self.col

            if ch == "{":
                self._advance()
                tokens.append(Token(TokenType.LBRACE, "{", start_line, start_col))
            elif ch == "}":
                self._advance()
                tokens.append(Token(TokenType.RBRACE, "}", start_line, start_col))
            elif ch == "[":
                self._advance()
                tokens.append(Token(TokenType.LBRACKET, "[", start_line, start_col))
            elif ch == "]":
                self._advance()
                tokens.append(Token(TokenType.RBRACKET, "]", start_line, start_col))
            elif ch == ":":
                self._advance()
                tokens.append(Token(TokenType.COLON, ":", start_line, start_col))
            elif ch == ",":
                self._advance()
                tokens.append(Token(TokenType.COMMA, ",", start_line, start_col))
            elif ch == '"':
                tokens.append(self._read_string(start_line, start_col))
            elif ch == "-" or ch.isdigit():
                tokens.append(self._read_number(start_line, start_col))
            elif ch.isalpha():
                tokens.append(self._read_keyword(start_line, start_col))
            else:
                raise LexError(f"Unexpected character {ch!r}", start_line, start_col)

            self._skip_whitespace()

        tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return tokens

    def _read_string(self, start_line, start_col):
        self._advance()  # consume opening quote
        chars = []
        while True:
            if self.pos >= self.length:
                raise LexError("Unterminated string", start_line, start_col)
            ch = self._peek()
            if ch == '"':
                self._advance()
                break
            elif ch == "\\":
                self._advance()
                esc = self._peek()
                if esc == "u":
                    self._advance()
                    hex_digits = ""
                    for _ in range(4):
                        d = self._peek()
                        if d == "" or d not in "0123456789abcdefABCDEF":
                            raise LexError("Invalid \\u escape", self.line, self.col)
                        hex_digits += self._advance()
                    chars.append(chr(int(hex_digits, 16)))
                elif esc in self._ESCAPES:
                    self._advance()
                    chars.append(self._ESCAPES[esc])
                else:
                    raise LexError(f"Invalid escape sequence '\\{esc}'", self.line, self.col)
            elif ord(ch) < 0x20:
                raise LexError("Unescaped control character in string", self.line, self.col)
            else:
                chars.append(self._advance())
        return Token(TokenType.STRING, "".join(chars), start_line, start_col)

    def _read_number(self, start_line, start_col):
        start = self.pos
        if self._peek() == "-":
            self._advance()

        if self._peek() == "0":
            self._advance()
        elif self._peek().isdigit():
            while self._peek().isdigit():
                self._advance()
        else:
            raise LexError("Invalid number: expected digit", self.line, self.col)

        if self._peek() == ".":
            self._advance()
            if not self._peek().isdigit():
                raise LexError("Invalid number: expected digit after '.'", self.line, self.col)
            while self._peek().isdigit():
                self._advance()

        if self._peek() in ("e", "E"):
            self._advance()
            if self._peek() in ("+", "-"):
                self._advance()
            if not self._peek().isdigit():
                raise LexError("Invalid number: expected digit in exponent", self.line, self.col)
            while self._peek().isdigit():
                self._advance()

        raw = self.text[start:self.pos]
        value = float(raw) if any(c in raw for c in ".eE") else int(raw)
        return Token(TokenType.NUMBER, value, start_line, start_col)

    def _read_keyword(self, start_line, start_col):
        start = self.pos
        while self._peek().isalpha():
            self._advance()
        word = self.text[start:self.pos]
        if word == "true":
            return Token(TokenType.TRUE, True, start_line, start_col)
        elif word == "false":
            return Token(TokenType.FALSE, False, start_line, start_col)
        elif word == "null":
            return Token(TokenType.NULL, None, start_line, start_col)
        else:
            raise LexError(f"Unexpected identifier {word!r}", start_line, start_col)
