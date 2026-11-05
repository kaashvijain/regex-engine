from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import regex_engine
from regex_engine.dfa import build_dfa
from regex_engine.export import (
    annotate_trace,
    ast_to_view,
    dfa_to_json,
    nfa_to_json,
    tokens_to_json,
)

MAX_PATTERN = 200
MAX_TEXT = 2000
MAX_DFA_STATES = 300

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Regex Engine Visualizer", docs_url="/api/docs", redoc_url=None)


class AnalyzeRequest(BaseModel):
    pattern: str = Field(max_length=MAX_PATTERN)
    text: str = Field(default="", max_length=MAX_TEXT)
    mode: Literal["full", "search"] = "full"


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    try:
        rx = regex_engine.compile(req.pattern)
    except regex_engine.RegexSyntaxError as e:
        return JSONResponse(
            status_code=400, content={"error": e.message, "position": e.position}
        )

    dfa = build_dfa(rx.nfa, max_states=MAX_DFA_STATES)
    search = req.mode == "search"

    if search:
        result = {"matches": [list(span) for span in rx.finditer(req.text)]}
    else:
        result = {"matched": rx.fullmatch(req.text)}

    return {
        "pattern": req.pattern,
        "text": req.text,
        "mode": req.mode,
        "tokens": tokens_to_json(rx.tokens),
        "ast": ast_to_view(rx.ast),
        "nfa": nfa_to_json(rx.nfa),
        "dfa": dfa_to_json(dfa),
        "trace": annotate_trace(
            rx.nfa, dfa, rx.trace(req.text, search), req.text, search
        ),
        "result": result,
    }


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
