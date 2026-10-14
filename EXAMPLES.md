# Example questions

Real runs of `app.py` on `claude-sonnet-5-5` with the **zero-shot** strategy. Each answer was checked by hand against the database.

| # | Question | Verdict | Tokens (in / out) | Cost |
|---|---|---|---|---|
| 1 | Who spent the most CougarCash at the Creamery? | ✅ Correct | 3,857 / 354 | $0.011 |
| 2 | Top 5 international (and US) students by GPA with no scholarship, RM, who deposited CougarCash | ✅ Correct, and honest that fewer than 5 matched | 4,351 / 1,116 | $0.020 |
| 3 | Which student has the least CougarCash left? | ⚠️ Partly correct | 3,817 / 418 | $0.012 |
| 4 | Which students are taking classes in Fall 2026 but haven't bought anything with CougarCash? | ✅ Correct | 3,898 / 263 | $0.010 |
| 5 | Which professor gave the lowest average grade in Winter 2026? | ⚠️ Correct but misleading | 3,883 / 251 | $0.010 |
| 6 | Do on-campus students pay more rent than off-campus students? | ✅ Correct | 3,849 / 368 | $0.011 |
| 7 | What classes is Emily Larsen taking right now? | ❌ Wrong | 3,841 / 308 | $0.011 |
| 8 | Is Wei Zhang retaking any classes? | ⚠️ Right answer, incomplete | 3,860 / 607 | $0.014 |

Total for all 8: about **$0.10**, roughly 1¢ per question. Prices: $2 per million input tokens and $10 per million output tokens.

---

## 1. Who spent the most CougarCash at the Creamery? ✅

```sql
SELECT s.student_id, s.first_name, s.last_name, SUM(t.amount) AS total_spent
FROM cougarcash_transactions t
JOIN stores st ON t.store_id = st.store_id
JOIN students s ON t.student_id = s.student_id
WHERE t.transaction_type = 'Purchase'
  AND st.name LIKE '%Creamery%'
GROUP BY s.student_id, s.first_name, s.last_name
ORDER BY total_spent DESC
LIMIT 1
```

> Diego Hernandez spent the most CougarCash at the Creamery, with a total of $18.08 in purchases.

**Notes:** Claude joined to `stores` instead of guessing a store ID, used `LIKE '%Creamery%'` because the real name is "BYU Creamery on Ninth", and excluded deposits.

---

## 2. Top 5 international and US students by GPA (no scholarship, RM, deposited CougarCash) ✅

*Asked as: "Who are the top 5 international students by GPA who have no scholarship, are returned missionaries, and have deposited CougarCash?, find the same for the top 5 national students"*

```sql
WITH student_gpa AS (
    SELECT s.student_id, s.first_name, s.last_name, s.citizenship,
           SUM(g.grade_points * c.credits) / SUM(c.credits) AS gpa
    FROM students s
    JOIN enrollments e ON e.student_id = s.student_id
    JOIN grade_scale g ON g.letter_grade = e.letter_grade
    JOIN sections sec ON sec.section_id = e.section_id
    JOIN courses c ON c.course_id = sec.course_id
    WHERE s.scholarship_pct = 0
      AND s.returned_missionary = 1
      AND EXISTS (SELECT 1 FROM cougarcash_transactions t
                  WHERE t.student_id = s.student_id AND t.transaction_type = 'Deposit')
    GROUP BY s.student_id, s.first_name, s.last_name, s.citizenship
)
SELECT * FROM (SELECT student_id, first_name, last_name, citizenship, ROUND(gpa, 3) AS gpa
               FROM student_gpa WHERE citizenship = 'International' ORDER BY gpa DESC LIMIT 5)
UNION ALL
SELECT * FROM (SELECT student_id, first_name, last_name, citizenship, ROUND(gpa, 3) AS gpa
               FROM student_gpa WHERE citizenship = 'US Citizen' ORDER BY gpa DESC LIMIT 5)
```

> **International students (top 3 found, fewer than 5 matched):** Sione Fifita 3.02, Hiroshi Tanaka 2.40, Wei Zhang 2.35.
> **National (US citizen) students (only 1 found):** Emma Johnson 1.70.
> Only 3 international students and 1 US citizen student met all the criteria, so neither group reaches 5.

**Notes:** This was the hardest question, and Claude got it fully right:
- GPA is weighted by credits, which takes 5 tables.
- Fall 2026 classes are left out automatically, because their NULL grades don't match anything in `grade_scale`.
- It used `EXISTS` for "deposited", so the deposits don't multiply the GPA rows.
- It answered two questions in one query with `UNION ALL`.
- It said plainly that fewer than 5 students matched instead of loosening a filter.

One judgment call: it read "national" as `'US Citizen'` and left out permanent residents. That didn't change the result here, because the dataset has none.

---

## 3. Which student has the least CougarCash left? ⚠️

```sql
SELECT s.student_id, s.first_name, s.last_name,
       SUM(CASE WHEN t.transaction_type = 'Deposit' THEN t.amount ELSE -t.amount END) AS balance
FROM students s
JOIN cougarcash_transactions t ON t.student_id = s.student_id
GROUP BY s.student_id, s.first_name, s.last_name
ORDER BY balance ASC
LIMIT 1
```

> Wei Zhang (student ID 167745718) has the least CougarCash left, with a balance of $25.96.

**Notes:** No column stores a balance, and Claude correctly worked it out as deposits minus purchases. But the inner `JOIN` drops the **5 students who have no transactions at all**. Their balance is arguably $0, which is less than Wei's $25.96. The answer is reasonable but doesn't mention the ambiguity. A `LEFT JOIN` with `COALESCE(..., 0)` would include them.

---

## 4. Which students are taking classes in Fall 2026 but haven't bought anything with CougarCash? ✅

```sql
SELECT DISTINCT s.student_id, s.first_name, s.last_name
FROM students s
JOIN enrollments e ON e.student_id = s.student_id
JOIN sections sec ON sec.section_id = e.section_id
WHERE sec.semester = 'Fall 2026'
  AND NOT EXISTS (SELECT 1 FROM cougarcash_transactions t
                  WHERE t.student_id = s.student_id AND t.transaction_type = 'Purchase')
```

> Three students are enrolled in Fall 2026 classes but have no CougarCash purchases on record: Jacob Anderson, Bridger Larsen, McKenzie Young.

**Notes:** Correct use of `NOT EXISTS`. Checking only *purchases* matters: all three of these students made deposits, so a query that checked for any transaction would have missed them.

---

## 5. Which professor gave the lowest average grade in Winter 2026? ⚠️

```sql
SELECT p.professor_id, p.first_name, p.last_name, AVG(gs.grade_points) AS avg_grade_points
FROM professors p
JOIN sections s ON s.professor_id = p.professor_id
JOIN enrollments e ON e.section_id = s.section_id
JOIN grade_scale gs ON gs.letter_grade = e.letter_grade
WHERE s.semester = 'Winter 2026'
GROUP BY p.professor_id, p.first_name, p.last_name
ORDER BY avg_grade_points ASC
LIMIT 1
```

> Emily Larsen gave the lowest average grade in Winter 2026, with an average of 1.0 grade points (about a D on a 4.0 scale).

**Notes:** The SQL is right, but Emily Larsen's "average" comes from **one student**. The next lowest, Hannah Pratt (2.63), is based on 12 grades. The answer doesn't mention the sample size because the query never selected `COUNT(*)`, so Claude couldn't see it.

---

## 6. Do on-campus students pay more rent than off-campus students? ✅

```sql
SELECT CASE WHEN h.on_campus = 1 THEN 'On-campus' ELSE 'Off-campus' END AS housing_type,
       COUNT(*) AS student_count,
       ROUND(AVG(h.monthly_rent), 2) AS avg_monthly_rent
FROM students s
JOIN housing h ON s.housing_id = h.housing_id
GROUP BY h.on_campus
ORDER BY h.on_campus DESC
```

> Yes, on average. On-campus students pay about $689 per month in rent, compared with about $494.62 for off-campus students. That's roughly $194 more per month on campus. This is based on a small group: 5 on-campus students and 13 off-campus students.

**Notes:** It turned the 0/1 flag into readable labels, averaged across *students* rather than housing options, and this time included the count and a small-sample caveat. Compare that with example 5.

---

## 7. What classes is Emily Larsen taking right now? ❌

```sql
SELECT c.dept_code, c.course_number, c.title, sec.section_number, sec.semester, sec.days, sec.start_time, sec.building
FROM students s
JOIN enrollments e ON e.student_id = s.student_id
JOIN sections sec ON sec.section_id = e.section_id
JOIN courses c ON c.course_id = sec.course_id
WHERE s.first_name = 'Emily' AND s.last_name = 'Larsen'
  AND e.letter_grade IS NULL
```

> No matching records were found for Emily Larsen. The search didn't return any current classes for her. She may not be enrolled in anything right now, or there may be no student by that name in the records.

**Notes:** Emily Larsen is a **professor**, not a student. Claude only searched `students` because the question said "taking". It never checked `professors`, so it missed that she is *teaching* MATH 112 and MATH 113 this semester (Fall 2026). The answer at least didn't make anything up. One clever detail: it used `letter_grade IS NULL` to mean "current semester". That works in this data, but it would break if a past grade were ever missing.

---

## 8. Is Wei Zhang retaking any classes? ⚠️

```sql
SELECT s.student_id, c.dept_code, c.course_number, c.title, COUNT(*) AS times_taken
FROM students s
JOIN enrollments e ON e.student_id = s.student_id
JOIN sections sec ON sec.section_id = e.section_id
JOIN courses c ON c.course_id = sec.course_id
WHERE s.first_name = 'Wei' AND s.last_name = 'Zhang'
GROUP BY s.student_id, c.course_id
HAVING COUNT(*) > 1
```

> Yes, it looks like it. Wei Zhang has two enrollments in PSYCH 111 (General Psychology), so they've taken it twice. It's the only course they've taken more than once. The records don't show whether the second attempt is in progress or already finished.

**Notes:** It correctly found the course with `GROUP BY … HAVING COUNT(*) > 1`. But the last sentence is wrong: the database *does* show that the first attempt got a C- in Winter 2026 and the retake is in progress in Fall 2026. The query just didn't select the semester or grade. This is a pattern: **the answer can only be as good as the columns the SQL chose to return.**
