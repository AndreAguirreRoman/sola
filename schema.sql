-- BYU Student Records database (fictional data only)
PRAGMA foreign_keys = ON;

CREATE TABLE majors (
    major_id    INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    college     TEXT NOT NULL            -- e.g. 'Physical and Mathematical Sciences'
);

CREATE TABLE housing (
    housing_id   INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,   -- e.g. 'Heritage Halls', 'The Village'
    on_campus    INTEGER NOT NULL CHECK (on_campus IN (0, 1)),
    monthly_rent REAL NOT NULL
);

CREATE TABLE students (
    student_id        INTEGER PRIMARY KEY,   -- 9-digit BYU ID
    net_id            TEXT NOT NULL UNIQUE,
    first_name        TEXT NOT NULL,
    last_name         TEXT NOT NULL,
    email             TEXT NOT NULL UNIQUE,
    major_id          INTEGER REFERENCES majors(major_id),   -- NULL = undeclared
    class_standing    TEXT NOT NULL CHECK (class_standing IN ('Freshman','Sophomore','Junior','Senior','Graduate')),
    enrollment_status TEXT NOT NULL CHECK (enrollment_status IN ('Full-time','Part-time','Withdrawn','Graduated')),
    citizenship       TEXT NOT NULL CHECK (citizenship IN ('US Citizen','Permanent Resident','International')),
    home_country      TEXT NOT NULL,
    home_state        TEXT,                  -- US state; NULL for international students
    church_member     INTEGER NOT NULL CHECK (church_member IN (0, 1)),
    returned_missionary INTEGER NOT NULL CHECK (returned_missionary IN (0, 1)),
    scholarship_pct   INTEGER NOT NULL DEFAULT 0 CHECK (scholarship_pct BETWEEN 0 AND 100),
    housing_id        INTEGER REFERENCES housing(housing_id),
    admit_date        TEXT NOT NULL          -- YYYY-MM-DD
);

CREATE TABLE professors (
    professor_id INTEGER PRIMARY KEY,
    first_name   TEXT NOT NULL,
    last_name    TEXT NOT NULL,
    department   TEXT NOT NULL,              -- e.g. 'Computer Science'
    office       TEXT NOT NULL               -- building + room, e.g. 'TMCB 3330'
);

CREATE TABLE courses (
    course_id     INTEGER PRIMARY KEY,
    dept_code     TEXT NOT NULL,             -- e.g. 'C S', 'MATH', 'REL A'
    course_number TEXT NOT NULL,             -- e.g. '142', '112'
    title         TEXT NOT NULL,
    credits       REAL NOT NULL,
    UNIQUE (dept_code, course_number)
);

CREATE TABLE sections (
    section_id     INTEGER PRIMARY KEY,
    course_id      INTEGER NOT NULL REFERENCES courses(course_id),
    professor_id   INTEGER NOT NULL REFERENCES professors(professor_id),
    semester       TEXT NOT NULL,            -- 'Fall 2025', 'Winter 2026', 'Fall 2026'
    section_number TEXT NOT NULL,            -- '001', '002'
    days           TEXT NOT NULL,            -- 'MWF', 'TTh'
    start_time     TEXT NOT NULL,            -- 24h 'HH:MM'
    building       TEXT NOT NULL,            -- e.g. 'JSB', 'TMCB', 'MARB'
    capacity       INTEGER NOT NULL
);

CREATE TABLE grade_scale (
    letter_grade TEXT PRIMARY KEY,           -- 'A', 'A-', ..., 'E' (BYU uses E for failing)
    grade_points REAL NOT NULL
);

CREATE TABLE enrollments (
    student_id   INTEGER NOT NULL REFERENCES students(student_id),
    section_id   INTEGER NOT NULL REFERENCES sections(section_id),
    letter_grade TEXT REFERENCES grade_scale(letter_grade),   -- NULL = in progress (current semester)
    PRIMARY KEY (student_id, section_id)
);

CREATE TABLE stores (
    store_id   INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,         -- e.g. 'BYU Creamery on Ninth', 'Vending Machine - TMCB'
    category   TEXT NOT NULL CHECK (category IN ('Dining','Grocery','Retail','Vending','Services')),
    building   TEXT NOT NULL,                -- e.g. 'WILK', 'HBLL', 'TMCB'
    open_time  TEXT NOT NULL,                -- 24h 'HH:MM'
    close_time TEXT NOT NULL                 -- 24h 'HH:MM'; '00:00' = midnight
);

CREATE TABLE cougarcash_transactions (
    transaction_id   INTEGER PRIMARY KEY,
    student_id       INTEGER NOT NULL REFERENCES students(student_id),
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Deposit','Purchase')),
    store_id         INTEGER REFERENCES stores(store_id),   -- where it was spent; NULL for deposits
    amount           REAL NOT NULL CHECK (amount > 0),   -- always positive; type gives direction
    transaction_date TEXT NOT NULL           -- YYYY-MM-DD HH:MM
);
