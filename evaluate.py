"""Compare the three prompting strategies on a fixed test set.

Each test question has a hand-written "gold" SQL query. For every strategy we let
Claude write SQL, run both queries, and mark the strategy correct when its rows
contain the gold answer (same number of rows; every gold value appears in the
matching row; numbers within 0.01). Results go to strategy_results.md.

    python evaluate.py                       # all strategies, model from .env
    python evaluate.py --strategies zero-shot single-domain
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

from app import DB_PATH, DEFAULT_MODEL, Claude, ask_database, initialize_database, open_read_only
from prompts import STRATEGIES

ROOT = Path(__file__).parent

TESTS = [
    ("Who spent the most CougarCash at the Creamery?",
     """SELECT s.first_name, s.last_name, ROUND(SUM(t.amount), 2)
        FROM cougarcash_transactions t JOIN stores st USING (store_id) JOIN students s USING (student_id)
        WHERE t.transaction_type = 'Purchase' AND st.name LIKE '%Creamery%'
        GROUP BY s.student_id ORDER BY 3 DESC LIMIT 1"""),
    ("Who are the top 5 international students by GPA who have no scholarship, are returned missionaries, and have deposited CougarCash?",
     """SELECT s.first_name, s.last_name, ROUND(SUM(g.grade_points * c.credits) / SUM(c.credits), 2) AS gpa
        FROM students s JOIN enrollments e USING (student_id) JOIN grade_scale g USING (letter_grade)
        JOIN sections sec USING (section_id) JOIN courses c USING (course_id)
        WHERE s.citizenship = 'International' AND s.scholarship_pct = 0 AND s.returned_missionary = 1
          AND s.student_id IN (SELECT student_id FROM cougarcash_transactions WHERE transaction_type = 'Deposit')
        GROUP BY s.student_id ORDER BY gpa DESC LIMIT 5"""),
    ("Which student has the least CougarCash left?",
     """SELECT s.first_name, s.last_name,
               ROUND(SUM(CASE WHEN t.transaction_type = 'Deposit' THEN t.amount ELSE -t.amount END), 2) AS bal
        FROM cougarcash_transactions t JOIN students s USING (student_id)
        GROUP BY s.student_id ORDER BY bal LIMIT 1"""),
    ("Which students are taking classes in Fall 2026 but haven't bought anything with CougarCash?",
     """SELECT DISTINCT s.first_name, s.last_name
        FROM students s JOIN enrollments e USING (student_id) JOIN sections sec USING (section_id)
        WHERE sec.semester = 'Fall 2026'
          AND s.student_id NOT IN (SELECT student_id FROM cougarcash_transactions WHERE transaction_type = 'Purchase')"""),
    ("Do on-campus students pay more rent than off-campus students?",
     """SELECT ROUND(AVG(h.monthly_rent), 2) FROM students s JOIN housing h USING (housing_id) GROUP BY h.on_campus"""),
    ("What classes is Wei Zhang taking right now?",
     """SELECT c.dept_code, c.course_number
        FROM students s JOIN enrollments e USING (student_id) JOIN sections sec USING (section_id) JOIN courses c USING (course_id)
        WHERE s.first_name = 'Wei' AND s.last_name = 'Zhang' AND sec.semester = 'Fall 2026'"""),
    ("Is Wei Zhang retaking any classes?",
     """SELECT c.dept_code, c.course_number
        FROM students s JOIN enrollments e USING (student_id) JOIN sections sec USING (section_id) JOIN courses c USING (course_id)
        WHERE s.first_name = 'Wei' AND s.last_name = 'Zhang'
        GROUP BY c.course_id HAVING COUNT(*) > 1"""),
    ("How many students have not declared a major?",
     """SELECT COUNT(*) FROM students WHERE major_id IS NULL"""),
    ("Which building's vending machine made the most money?",
     """SELECT st.building, ROUND(SUM(t.amount), 2)
        FROM cougarcash_transactions t JOIN stores st USING (store_id)
        WHERE st.category = 'Vending' AND t.transaction_type = 'Purchase'
        GROUP BY st.building ORDER BY 2 DESC LIMIT 1"""),
    ("What classes did Emily Larsen teach in Winter 2026?",
     """SELECT c.dept_code, c.course_number
        FROM sections sec JOIN professors p USING (professor_id) JOIN courses c USING (course_id)
        WHERE p.first_name = 'Emily' AND p.last_name = 'Larsen' AND sec.semester = 'Winter 2026'"""),
]


# ---------------------------------------------------------------- grading

def _value_matches(gold, cell) -> bool:
    if gold is None:
        return cell is None
    if isinstance(gold, (int, float)) and isinstance(cell, (int, float)):
        return abs(gold - cell) < 0.01
    return str(gold).lower() in str(cell).lower()


def _row_matches(gold_row, pred_row) -> bool:
    return all(any(_value_matches(g, c) for c in pred_row) for g in gold_row)


def is_correct(gold_rows, pred_rows) -> bool:
    if len(gold_rows) != len(pred_rows):
        return False
    unused = list(pred_rows)
    for gold_row in gold_rows:
        match = next((p for p in unused if _row_matches(gold_row, p)), None)
        if match is None:
            return False
        unused.remove(match)
    return True


# ---------------------------------------------------------------- report

def write_report(model: str, strategies, results, totals, path: Path) -> None:
    lines = [f"# Prompting strategy comparison ({model})", "",
             f"{len(TESTS)} test questions, each graded automatically against a hand-written gold query.", "",
             "| Strategy | Correct | Input tokens | Output tokens | Cost | Avg seconds |",
             "|---|---|---|---|---|---|"]
    for s in strategies:
        t = totals[s]
        cost = f"${t['cost']:.4f}" if t["cost"] is not None else "n/a"
        lines.append(f"| {s} | {t['correct']}/{len(TESTS)} | {t['in']:,} | {t['out']:,} | {cost} | {t['secs'] / len(TESTS):.1f} |")
    lines += ["", "## Per question", "", "| # | Question | " + " | ".join(strategies) + " |",
              "|---|---|" + "---|" * len(strategies)]
    for i, (q, _) in enumerate(TESTS):
        marks = " | ".join("✅" if results[s][i]["correct"] else "❌" for s in strategies)
        lines.append(f"| {i + 1} | {q} | {marks} |")
    lines += ["", "## Generated SQL", ""]
    for i, (q, gold) in enumerate(TESTS):
        lines += [f"### {i + 1}. {q}", "", "Gold:", "```sql", " ".join(gold.split()), "```"]
        for s in strategies:
            r = results[s][i]
            verdict = "✅ correct" if r["correct"] else "❌ wrong"
            lines += [f"**{s}** ({verdict}, {len(r['rows'])} rows{', retried after error' if r['retried'] else ''}):",
                      "```sql", r["sql"], "```"]
        lines.append("")
    path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES))
    parser.add_argument("--out", default="strategy_results.md")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is missing. Copy .env.example to .env and add your key.")
    if not DB_PATH.exists():
        initialize_database()
    model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)

    with open_read_only() as conn:
        gold_rows = [conn.execute(sql).fetchall() for _, sql in TESTS]

    results, totals = {}, {}
    for strategy in args.strategies:
        claude = Claude(model)  # fresh token counter per strategy
        results[strategy], secs = [], 0.0
        print(f"\n=== {strategy}")
        for i, (question, _) in enumerate(TESTS):
            try:
                r = ask_database(claude, question, strategy, with_answer=False)
                r["correct"] = is_correct(gold_rows[i], r["rows"])
            except Exception as exc:  # unsafe/invalid SQL counts as wrong
                r = {"sql": f"-- ERROR: {exc}", "rows": [], "retried": False, "correct": False, "seconds": 0.0}
            secs += r["seconds"]
            results[strategy].append(r)
            print(f"  {'✅' if r['correct'] else '❌'} {question}")
        totals[strategy] = {"correct": sum(r["correct"] for r in results[strategy]),
                            "in": claude.input_tokens, "out": claude.output_tokens,
                            "cost": claude.cost(), "secs": secs}
        print(f"  -> {totals[strategy]['correct']}/{len(TESTS)} correct | {claude.usage_line()}")

    out = ROOT / args.out
    write_report(model, args.strategies, results, totals, out)
    (ROOT / "strategy_results.json").write_text(json.dumps(
        {s: [{k: v for k, v in r.items() if k != "rows"} | {"rows": [list(x) for x in r["rows"]]}
             for r in results[s]] for s in results} | {"_totals": totals}, indent=2, default=str))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
