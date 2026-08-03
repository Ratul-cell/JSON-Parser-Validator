"""
Command-line interface for the JSON Parser & Validator.

Usage:
    python cli.py file.json         validate a file
    python cli.py --stdin           validate JSON piped in on stdin

Examples:
    python cli.py examples/valid.json
    echo '{"a": 1}' | python cli.py --stdin
"""

import sys
import json as _stdlib_json  # only used to pretty-print the resulting Python object
from validator import validate


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--stdin":
        text = sys.stdin.read()
        source = "<stdin>"
    else:
        path = sys.argv[1]
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        source = path

    result = validate(text)

    if result.is_valid:
        print(f"VALID: {source}")
        print(_stdlib_json.dumps(result.value, indent=2))
        sys.exit(0)
    else:
        print(f"INVALID: {source}")
        print(result.error)
        sys.exit(1)


if __name__ == "__main__":
    main()
