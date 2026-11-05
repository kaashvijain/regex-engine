"""Entry point.

    python main.py                 start the web app on http://127.0.0.1:8000
    python main.py PATTERN TEXT    print whether TEXT fully matches PATTERN
"""

import os
import sys


def cli(pattern, text):
    import regex_engine

    try:
        rx = regex_engine.compile(pattern)
    except regex_engine.RegexSyntaxError as e:
        print(f"error: {e.message}")
        print(f"  {pattern}")
        print("  " + " " * e.position + "^")
        return 2
    print(rx.fullmatch(text))
    spans = list(rx.finditer(text))
    if spans:
        print("matches:", ", ".join(f"{text[a:b]!r}@{a}" for a, b in spans))
    return 0


def serve():
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.server:app", host=os.environ.get("HOST", "127.0.0.1"), port=port)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(cli(sys.argv[1], sys.argv[2]))
    elif len(sys.argv) == 1:
        serve()
    else:
        print(__doc__)
        sys.exit(1)
