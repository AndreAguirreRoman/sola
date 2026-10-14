"""The three prompting strategies from Chang & Fosler-Lussier (2023),
"How to Prompt LLMs for Text-to-SQL" (arXiv:2305.11853).

- zero-shot:      schema + question only
- single-domain:  a few question->SQL examples written for THIS database, then the question
- cross-domain:   a few question->SQL examples from a DIFFERENT database, then our schema + question
"""

STRATEGIES = ("zero-shot", "single-domain", "cross-domain")

INSTRUCTION = "-- Using valid SQLite, answer the following question for the tables provided above."

# In-domain examples. Deliberately NOT the same as the questions in evaluate.py.
SINGLE_DOMAIN_EXAMPLES = [
    ("How many students are majoring in Computer Science?",
     "SELECT COUNT(*)\nFROM students s\nJOIN majors m ON m.major_id = s.major_id\nWHERE m.name = 'Computer Science'"),
    ("What courses is Sarah Hansen teaching in Fall 2026?",
     "SELECT c.dept_code, c.course_number, c.title\nFROM sections sec\n"
     "JOIN professors p ON p.professor_id = sec.professor_id\n"
     "JOIN courses c ON c.course_id = sec.course_id\n"
     "WHERE p.first_name = 'Sarah' AND p.last_name = 'Hansen' AND sec.semester = 'Fall 2026'"),
    ("What is Hailey Taylor's GPA?",
     "SELECT ROUND(SUM(g.grade_points * c.credits) / SUM(c.credits), 2) AS gpa\n"
     "FROM students s\nJOIN enrollments e ON e.student_id = s.student_id\n"
     "JOIN grade_scale g ON g.letter_grade = e.letter_grade\n"
     "JOIN sections sec ON sec.section_id = e.section_id\n"
     "JOIN courses c ON c.course_id = sec.course_id\n"
     "WHERE s.first_name = 'Hailey' AND s.last_name = 'Taylor'"),
    ("How much CougarCash was spent in each store category?",
     "SELECT st.category, ROUND(SUM(t.amount), 2) AS spent\nFROM cougarcash_transactions t\n"
     "JOIN stores st ON st.store_id = t.store_id\nWHERE t.transaction_type = 'Purchase'\n"
     "GROUP BY st.category\nORDER BY spent DESC"),
]

# A different database (campus piano tracking) with its own examples.
CROSS_DOMAIN_SCHEMA = """CREATE TABLE buildings (
    building_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL
);
CREATE TABLE pianos (
    piano_id       INTEGER PRIMARY KEY,
    building_id    INTEGER NOT NULL REFERENCES buildings(building_id),
    room           TEXT NOT NULL,
    brand          TEXT NOT NULL,
    year_purchased INTEGER NOT NULL
);
CREATE TABLE technicians (
    technician_id INTEGER PRIMARY KEY,
    name          TEXT NOT NULL
);
CREATE TABLE tunings (
    tuning_id     INTEGER PRIMARY KEY,
    piano_id      INTEGER NOT NULL REFERENCES pianos(piano_id),
    technician_id INTEGER NOT NULL REFERENCES technicians(technician_id),
    tuning_date   TEXT NOT NULL,  -- YYYY-MM-DD
    cost          REAL NOT NULL
);"""

CROSS_DOMAIN_EXAMPLES = [
    ("How many pianos are in each building?",
     "SELECT b.name, COUNT(*) AS pianos\nFROM pianos p\nJOIN buildings b ON b.building_id = p.building_id\nGROUP BY b.building_id"),
    ("Which pianos have never been tuned?",
     "SELECT p.piano_id, p.room, p.brand\nFROM pianos p\n"
     "WHERE NOT EXISTS (SELECT 1 FROM tunings t WHERE t.piano_id = p.piano_id)"),
    ("Which technician earned the most from tunings in 2026?",
     "SELECT te.name, SUM(t.cost) AS earned\nFROM tunings t\n"
     "JOIN technicians te ON te.technician_id = t.technician_id\n"
     "WHERE t.tuning_date LIKE '2026-%'\nGROUP BY te.technician_id\nORDER BY earned DESC\nLIMIT 1"),
    ("What is the average tuning cost for Steinway pianos?",
     "SELECT ROUND(AVG(t.cost), 2)\nFROM tunings t\nJOIN pianos p ON p.piano_id = t.piano_id\nWHERE p.brand = 'Steinway'"),
]


def _examples(pairs) -> str:
    return "\n\n".join(f"-- Question: {q}\n{sql};" for q, sql in pairs)


def build_sql_prompt(schema: str, question: str, strategy: str = "zero-shot") -> str:
    if strategy == "zero-shot":
        return f"{schema}\n{INSTRUCTION}\n-- Question: {question}\n"
    if strategy == "single-domain":
        return (f"{schema}\n{INSTRUCTION}\n\n-- Examples:\n{_examples(SINGLE_DOMAIN_EXAMPLES)}\n\n"
                f"-- Question: {question}\n")
    if strategy == "cross-domain":
        return (f"{CROSS_DOMAIN_SCHEMA}\n{INSTRUCTION}\n\n{_examples(CROSS_DOMAIN_EXAMPLES)}\n\n"
                f"-- Now a different database:\n\n{schema}\n{INSTRUCTION}\n-- Question: {question}\n")
    raise ValueError(f"Unknown strategy {strategy!r}; choose from {STRATEGIES}")
