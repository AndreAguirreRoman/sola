"""Ask the BYU Student Records database questions in plain English.

Flow: question -> Claude writes SQL -> run it on SQLite -> send rows back to
Claude -> plain-English answer.
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import time
from pathlib import Path

from prompts import STRATEGIES, build_sql_prompt

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "byu.db"
SCHEMA_PATH = ROOT / "schema.sql"
DATA_PATH = ROOT / "data.sql"
DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_ROWS_TO_MODEL = 50  # keep the answer prompt small (and cheap)
# USD per million tokens (input, output), from platform.claude.com/docs/en/about-claude/pricing
PRICES = {"claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}


def fmt(value) -> str:
    """Show SQL NULL as NULL (not Python's None) so the model isn't misled."""
    return "NULL" if value is None else str(value)


# ---------------------------------------------------------------- database

def initialize_database() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    for suffix in ("", "-journal", "-wal", "-shm"):  # remove old DB and any leftover journals
        Path(f"{DB_PATH}{suffix}").unlink(missing_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(SCHEMA_PATH.read_text())
        connection.executescript(DATA_PATH.read_text())
    print(f"Created {DB_PATH}")


def open_read_only() -> sqlite3.Connection:
    """Open the DB read-only so even a bad query can't change data."""
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def database_prompt(connection: sqlite3.Connection, sample_rows: int = 3) -> str:
    """Describe the DB the way the Chang & Fosler-Lussier paper found works best:
    each table's CREATE TABLE statement followed by a few example rows."""
    parts: list[str] = []
    tables = connection.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY rowid"
    ).fetchall()
    for name, create_sql in tables:
        parts.append(create_sql + ";")
        if sample_rows:
            cursor = connection.execute(f"SELECT * FROM {name} LIMIT {sample_rows}")
            header = "\t".join(col[0] for col in cursor.description)
            rows = "\n".join("\t".join(fmt(v) for v in row) for row in cursor.fetchall())
            parts.append(
                f"/*\n{sample_rows} example rows:\nSELECT * FROM {name} LIMIT {sample_rows};\n"
                f"{header}\n{rows}\n*/"
            )
        parts.append("")
    return "\n".join(parts)


def clean_sql(text: str) -> str:
    """Extract one read-only SQL statement from the model output."""
    text = text.strip()
    fenced = re.search(r"```(?:sql|sqlite)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    sql = fenced.group(1).strip() if fenced else text
    sql = sql.rstrip(";").strip()
    if ";" in sql:
        raise ValueError("Only one SQL statement is allowed.")
    if not re.match(r"^(SELECT|WITH)\b", sql, flags=re.IGNORECASE):
        raise ValueError("Only read-only SELECT/WITH queries are allowed.")
    if re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA)\b", sql, re.IGNORECASE):
        raise ValueError("The generated query contains a write or schema-changing operation.")
    return sql


# ---------------------------------------------------------------- Claude

class Claude:
    def __init__(self, model: str):
        from anthropic import Anthropic

        self.client = Anthropic()
        self.model = model
        self.input_tokens = 0
        self.output_tokens = 0

    def ask(self, system: str, user: str, max_tokens: int = 4096) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        if response.stop_reason == "max_tokens":
            raise RuntimeError(f"Claude's reply was cut off at the {max_tokens}-token limit "
                               "(the query was too long). Try a simpler question.")
        return "\n".join(b.text for b in response.content if b.type == "text").strip()

    def cost(self) -> float | None:
        if self.model not in PRICES:
            return None
        price_in, price_out = PRICES[self.model]
        return (self.input_tokens * price_in + self.output_tokens * price_out) / 1_000_000

    def usage_line(self) -> str:
        cost = self.cost()
        dollars = f" | ${cost:.4f}" if cost is not None else ""
        return f"{self.input_tokens} in / {self.output_tokens} out{dollars}"


SQL_SYSTEM = (
    "You translate natural-language questions about a BYU student records database "
    "into a single valid SQLite query. Return only the SQL, with no Markdown or explanation. "
    "Use only the tables and columns in the schema. Generate read-only queries."
)

ANSWER_SYSTEM = (
    "You answer questions about a BYU student records database. You are given the user's "
    "question, the SQL that was run, and the rows it returned. Answer the question in plain, "
    "friendly English using only those rows. Be concise. If the result is empty, say that no "
    "matching records were found. Do not mention SQL unless asked."
)


def generate_sql(claude: Claude, schema: str, question: str, strategy: str = "zero-shot",
                 error: str | None = None, bad_sql: str | None = None) -> str:
    prompt = build_sql_prompt(schema, question, strategy)
    if error:
        prompt += (f"\n-- Your previous query failed.\n-- Query: {bad_sql}\n-- Error: {error}\n"
                   "-- Write a corrected query.\n")
    return clean_sql(claude.ask(SQL_SYSTEM, prompt))


def friendly_answer(claude: Claude, question: str, sql: str, columns: list[str], rows: list[tuple]) -> str:
    shown = rows[:MAX_ROWS_TO_MODEL]
    table = "\t".join(columns) + "\n" + "\n".join("\t".join(fmt(v) for v in r) for r in shown)
    note = f"\n(Showing {len(shown)} of {len(rows)} rows.)" if len(rows) > len(shown) else ""
    prompt = f"Question: {question}\n\nSQL:\n{sql}\n\nResult rows:\n{table}{note}"
    return claude.ask(ANSWER_SYSTEM, prompt, max_tokens=600)


def ask_database(claude: Claude, question: str, strategy: str = "zero-shot",
                 with_answer: bool = True) -> dict:
    """question -> SQL -> rows -> (optional) plain-English answer."""
    start = time.perf_counter()
    retried = False
    with open_read_only() as connection:
        schema = database_prompt(connection)
        sql = generate_sql(claude, schema, question, strategy)
        try:
            cursor = connection.execute(sql)
        except sqlite3.Error as exc:  # give Claude one chance to fix its query
            retried = str(exc)
            sql = generate_sql(claude, schema, question, strategy, error=str(exc), bad_sql=sql)
            try:
                cursor = connection.execute(sql)
            except sqlite3.Error as exc2:
                raise RuntimeError(f"SQL failed twice ({exc2}). Last query:\n{sql}") from None
        columns = [c[0] for c in cursor.description]
        rows = cursor.fetchall()
    answer = friendly_answer(claude, question, sql, columns, rows) if with_answer else None
    return {"question": question, "strategy": strategy, "sql": sql, "columns": columns,
            "rows": rows, "answer": answer, "retried": retried,
            "seconds": time.perf_counter() - start}


def run_question(claude: Claude, question: str, strategy: str = "zero-shot") -> str:
    result = ask_database(claude, question, strategy)
    if result["retried"]:
        print(f"  (first query failed: {result['retried']}; retried)")
    print(f"\nSQL:\n{result['sql']}\n")
    print(f"Rows returned: {len(result['rows'])}")
    print(f"\nAnswer: {result['answer']}")
    print(f"\n[{claude.model} | {strategy} | {result['seconds']:.1f}s | "
          f"total so far: {claude.usage_line()}]")
    return result["answer"]


# ---------------------------------------------------------------- CLI

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question", nargs="?", help="Question in plain English (omit for interactive mode)")
    parser.add_argument("--init-db", action="store_true", help="Recreate the database from schema.sql + data.sql")
    parser.add_argument("--show-prompt", action="store_true", help="Print the schema prompt sent to Claude")
    parser.add_argument("--strategy", choices=STRATEGIES, default="zero-shot",
                        help="Prompting strategy from Chang & Fosler-Lussier (default: zero-shot)")
    args = parser.parse_args()

    if args.init_db:
        initialize_database()
        return
    if not DB_PATH.exists():
        initialize_database()
    if args.show_prompt:
        with open_read_only() as connection:
            print(build_sql_prompt(database_prompt(connection), "<your question>", args.strategy))
        return

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is missing. Copy .env.example to .env and add your key.")
    claude = Claude(os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL))

    if args.question:
        try:
            run_question(claude, args.question, args.strategy)
        except Exception as exc:
            raise SystemExit(f"Error: {exc}\n[{claude.model} | total so far: {claude.usage_line()}]")
        return

    print("Ask about BYU students, classes, grades, housing, or CougarCash. Type 'quit' to exit.")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"quit", "exit", "q"}:
            break
        if question:
            try:
                run_question(claude, question, args.strategy)
            except Exception as exc:
                print(f"Error: {exc}")


if __name__ == "__main__":
    main()
