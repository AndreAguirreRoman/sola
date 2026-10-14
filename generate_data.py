"""Generate deterministic fictional data for the BYU student DB -> data.sql"""
import random, sys
from datetime import datetime, timedelta

random.seed(482)
out = []
def q(v):
    if v is None: return "NULL"
    if isinstance(v, str): return "'" + v.replace("'", "''") + "'"
    return repr(v)
def insert(table, rows):
    out.append(f"INSERT INTO {table} VALUES\n" + ",\n".join(
        "    (" + ", ".join(q(v) for v in r) + ")" for r in rows) + ";\n")

majors = [
    (1, "Computer Science", "Physical and Mathematical Sciences"),
    (2, "Statistics", "Physical and Mathematical Sciences"),
    (3, "Mathematics", "Physical and Mathematical Sciences"),
    (4, "Mechanical Engineering", "Ira A. Fulton College of Engineering"),
    (5, "Electrical Engineering", "Ira A. Fulton College of Engineering"),
    (6, "Accounting", "Marriott School of Business"),
    (7, "Information Systems", "Marriott School of Business"),
    (8, "Exercise Science", "Life Sciences"),
    (9, "Psychology", "Family, Home, and Social Sciences"),
    (10, "English", "Humanities"),
    (11, "Nursing", "Nursing"),
    (12, "Music", "Fine Arts and Communications"),
]
insert("majors", majors)

housing = [
    (1, "Heritage Halls", 1, 520.0), (2, "Helaman Halls", 1, 610.0),
    (3, "Wymount Terrace", 1, 845.0), (4, "Foley Apartments", 1, 735.0),
    (5, "The Village", 0, 615.0), (6, "Glenwood", 0, 435.0),
    (7, "Liberty on 9th", 0, 560.0), (8, "Belmont", 0, 395.0),
    (9, "King Henry", 0, 425.0),
]
insert("housing", housing)

grade_scale = [("A",4.0),("A-",3.7),("B+",3.4),("B",3.0),("B-",2.7),("C+",2.4),
               ("C",2.0),("C-",1.7),("D+",1.4),("D",1.0),("D-",0.7),("E",0.0)]
insert("grade_scale", grade_scale)

profs = [
    (1, "Daniel", "Whitmore", "Computer Science", "TMCB 3368"),
    (2, "Sarah", "Hansen", "Computer Science", "TMCB 3330"),
    (3, "Kevin", "Ashby", "Computer Science", "TMCB 3326"),
    (4, "Rachel", "Moore", "Statistics", "TMCB 2152"),
    (5, "Michael", "Tanner", "Statistics", "TMCB 2130"),
    (6, "Emily", "Larsen", "Mathematics", "TMCB 275"),
    (7, "Jared", "Whitaker", "Mathematics", "TMCB 289"),
    (8, "Lisa", "Nakamura", "Physics", "ESC N241"),
    (9, "Brent", "Olsen", "Mechanical Engineering", "EB 435"),
    (10, "Maria", "Gonzalez", "Ancient Scripture", "JSB 270"),
    (11, "Thomas", "Reid", "Church History and Doctrine", "JSB 310"),
    (12, "Hannah", "Pratt", "English", "JFSB 4120"),
    (13, "Samuel", "Kimball", "Accounting", "TNRB 540"),
    (14, "Grace", "Ellsworth", "Psychology", "KMBL 1022"),
]
insert("professors", profs)

# course_id, dept, num, title, credits, (prof ids), building
courses = [
    (1, "C S", "110", "How to Program", 3.0, [2, 3], "TMCB"),
    (2, "C S", "111", "Introduction to Computer Science", 4.0, [2, 3], "JSB"),
    (3, "C S", "235", "Data Structures and Algorithms", 3.0, [1], "TMCB"),
    (4, "C S", "240", "Advanced Software Construction", 4.0, [3], "TMCB"),
    (5, "C S", "452", "Database Modeling Concepts", 3.0, [2], "TMCB"),
    (6, "C S", "482", "Data Science", 3.0, [1], "TMCB"),
    (7, "STAT", "121", "Principles of Statistics", 3.0, [4, 5], "JSB"),
    (8, "STAT", "240", "Probability and Statistics", 3.0, [5], "TMCB"),
    (9, "MATH", "112", "Calculus 1", 4.0, [6, 7], "TMCB"),
    (10, "MATH", "113", "Calculus 2", 4.0, [6, 7], "TMCB"),
    (11, "MATH", "213", "Elementary Linear Algebra", 2.0, [7], "TMCB"),
    (12, "PHSCS", "121", "Introduction to Newtonian Mechanics", 3.0, [8], "ESC"),
    (13, "ME EN", "250", "Statics", 3.0, [9], "EB"),
    (14, "REL A", "275", "Teachings and Doctrine of the Book of Mormon", 2.0, [10, 11], "JSB"),
    (15, "REL C", "200", "The Eternal Family", 2.0, [11], "JSB"),
    (16, "REL A", "250", "Jesus Christ and the Everlasting Gospel", 2.0, [10], "JSB"),
    (17, "WRTG", "150", "Writing and Rhetoric", 3.0, [12], "JFSB"),
    (18, "ACC", "200", "Principles of Accounting", 3.0, [13], "TNRB"),
    (19, "PSYCH", "111", "General Psychology", 3.0, [14], "KMBL"),
    (20, "AMER HER", "100", "American Heritage", 3.0, [12], "JSB"),
]
insert("courses", [c[:5] for c in courses])

semesters = ["Winter 2026", "Fall 2026"]
slots = [("MWF", "08:00"), ("MWF", "09:00"), ("MWF", "10:00"), ("MWF", "11:00"),
         ("MWF", "13:00"), ("TTh", "08:00"), ("TTh", "09:30"), ("TTh", "11:00"),
         ("TTh", "12:30"), ("TTh", "14:00"), ("TTh", "15:30")]
sections = []
sid = 1
for sem in semesters:
    for c in courses:
        n = 1
        if sem == "Winter 2026" and c[0] in (13, 15): continue
        for k in range(n):
            days, t = random.choice(slots)
            cap = random.choice([30, 40, 60, 80, 120]) if c[0] in (2, 7, 9, 14, 19, 20) else random.choice([25, 30, 40, 50])
            sections.append((sid, c[0], c[5][k % len(c[5])], sem, f"{k+1:03d}", days, t, c[6], cap))
            sid += 1
insert("sections", sections)

first = ["Ethan","Emma","Tanner","Abigail","Caleb","Brooklyn","Jacob","McKenzie","Spencer","Hailey",
         "Bridger","Kaitlyn","Logan","Madison","Tyler","Sophia","Andrew","Rebecca","Isaac","Lauren",
         "Wei","Mei","Diego","Valentina","Joao","Camila","Kwame","Ama","Hiroshi","Yuki","Sione","Mele",
         "Luis","Gabriela","Min-jun","Ji-woo","Lucas","Ana","Daniel","Olivia","Nathan","Chloe","Peter",
         "Grace","Samuel","Ruth","Aaron","Leah","Joseph","Hannah"]
last = ["Smith","Johnson","Christensen","Jensen","Peterson","Nielsen","Anderson","Young","Allen","Taylor",
        "Larsen","Hansen","Williams","Clark","Walker","Brown","Robinson","Hall","Wright","Thompson",
        "Zhang","Li","Hernandez","Garcia","Silva","Rodriguez","Mensah","Owusu","Tanaka","Sato","Fifita",
        "Tonga","Martinez","Lopez","Kim","Park","Oliveira","Santos","Nguyen","Tran","Baker","Adams",
        "Moore","Cook","Kofford","Rowley","Barlow","Hatch","Call","Morrell"]
us_states = ["Utah"]*10 + ["Idaho"]*3 + ["Arizona"]*3 + ["California"]*3 + ["Washington","Texas","Nevada","Colorado","Oregon","Virginia"]
intl = {"Wei":"China","Mei":"China","Diego":"Mexico","Valentina":"Mexico","Joao":"Brazil","Camila":"Brazil",
        "Kwame":"Ghana","Ama":"Ghana","Hiroshi":"Japan","Yuki":"Japan","Sione":"Tonga","Mele":"Tonga",
        "Luis":"Peru","Gabriela":"Peru","Min-jun":"South Korea","Ji-woo":"South Korea","Lucas":"Brazil","Ana":"Mexico",
        "Daniel":"Canada","Olivia":"Canada"}

standings = ["Freshman","Sophomore","Junior","Senior","Graduate"]
students = []
pick = list(range(12)) + [20, 22, 24, 26, 28, 30, 34, 38]   # 12 domestic-leaning + 8 international-leaning names
for i, idx in enumerate(pick):
    fn, ln = first[idx], last[idx]
    sid_ = 100000000 + random.randint(10000000, 89999999)
    net = (fn[0] + ln).lower().replace("-", "")[:8] + str(random.randint(1, 99))
    cs = random.choices(standings, weights=[22, 22, 22, 26, 8])[0]
    status = random.choices(["Full-time","Part-time","Withdrawn","Graduated"], weights=[78, 12, 5, 5])[0]
    if status == "Graduated": cs = "Senior"
    if fn in intl and random.random() < 0.85:
        cit, country, state = "International", intl[fn], None
    else:
        cit = random.choices(["US Citizen","Permanent Resident"], weights=[92, 8])[0]
        country, state = "United States", random.choice(us_states)
    member = 1 if random.random() < 0.97 else 0
    rm = 1 if member and cs != "Freshman" and random.random() < 0.55 else 0
    schol = random.choices([0, 25, 50, 75, 100], weights=[50, 15, 18, 7, 10])[0]
    if cs == "Freshman":
        h = random.choice([1, 1, 2, 2, 5, 6])
    elif cs == "Graduate":
        h = random.choice([3, 3, 4, None])
    else:
        h = random.choice([4, 5, 6, 7, 8, 9, None])
    years_in = {"Freshman": 0, "Sophomore": 1, "Junior": 2, "Senior": 3, "Graduate": 4}[cs] + (2 if rm else 0)
    admit = f"{2026 - years_in if cs!='Freshman' else 2026}-{random.choice(['04','09','09','09','01'])}-0{random.randint(1,9)}"
    if admit > "2026-09-30": admit = "2026-09-01"
    major = None if (cs in ("Freshman","Sophomore") and random.random() < 0.3) else random.randint(1, 12)
    students.append([sid_, net, fn, ln, f"{net}@byu.edu", major, cs, status, cit, country, state,
                     member, rm, schol, h, admit])
insert("students", [tuple(s) for s in students])

# enrollments
grade_letters = [g[0] for g in grade_scale]
gw = [30, 14, 11, 10, 7, 6, 6, 4, 3, 3, 2, 4]
sec_by_sem = {s: [x for x in sections if x[3] == s] for s in semesters}
enroll = []
major_courses = {1: [1,2,3,4,5,6,9,10,11], 2: [7,8,9,10,11,6], 3: [9,10,11,8], 4: [9,10,12,13],
                 5: [9,10,12,11], 6: [18,7], 7: [18,1,2,5], 8: [19,7], 9: [19,7], 10: [17], 11: [19,7], 12: [17]}
for s in students:
    status, cs, admit = s[7], s[6], s[15]
    for sem in semesters:
        start = {"Fall 2025": "2025-09-01", "Winter 2026": "2026-01-05", "Fall 2026": "2026-09-01"}[sem]
        if admit > start: continue
        if status in ("Withdrawn","Graduated") and sem == "Fall 2026": continue
        n = 2 if status == "Full-time" else 1
        pool = sec_by_sem[sem]
        prefer = set(major_courses.get(s[5], [])) | {14, 15, 16, 17, 20}
        chosen, used = [], set()
        cands = sorted(pool, key=lambda x: (0 if x[1] in prefer else 1, random.random()))
        for sec in cands:
            if len(chosen) >= n: break
            if sec[1] in used: continue
            used.add(sec[1]); chosen.append(sec)
        for sec in chosen:
            g = None if sem == "Fall 2026" else random.choices(grade_letters, weights=gw)[0]
            enroll.append((s[0], sec[0], g))
insert("enrollments", enroll)

# CougarCash
# store_id, name, category, building, open, close, (min $, max $), weight
stores = [
    (1, "Cougareat", "Dining", "WILK", "07:00", "21:00", (6, 14), 14),
    (2, "BYU Creamery on Ninth", "Grocery", "Creamery on Ninth", "07:00", "23:00", (3, 25), 10),
    (3, "BYU Store", "Retail", "BYU Store", "08:00", "19:00", (5, 80), 6),
    (4, "Cannon Commons", "Dining", "Cannon Center", "07:00", "20:00", (9, 15), 10),
    (5, "Legends Grille", "Dining", "WILK", "10:30", "15:00", (7, 13), 6),
    (6, "Jamba Juice", "Dining", "WILK", "08:00", "18:00", (5, 9), 6),
    (7, "Harold B. Lee Library Print Center", "Services", "HBLL", "07:00", "00:00", (0.5, 6), 6),
    (8, "Vending Machine - HBLL", "Vending", "HBLL", "00:00", "23:59", (1.5, 3.5), 5),
    (9, "Vending Machine - TMCB", "Vending", "TMCB", "00:00", "23:59", (1.5, 3.5), 5),
    (10, "Vending Machine - JSB", "Vending", "JSB", "00:00", "23:59", (1.5, 3.5), 3),
    (11, "Wilk Information Desk", "Services", "WILK", "08:00", "22:00", (2, 10), 2),
]
insert("stores", [s[:6] for s in stores])

txns = []
tid = 1
base = datetime(2026, 8, 25)
for s in students:
    if s[7] in ("Withdrawn", "Graduated"): continue
    on = s[14] in (1, 2)
    n_deposit = 1
    n_buy = random.randint(2, 4) if on else random.randint(0, 3)
    for _ in range(n_deposit):
        d = base + timedelta(days=random.randint(0, 45), hours=random.randint(8, 21), minutes=random.randint(0, 59))
        txns.append([s[0], "Deposit", None, float(random.choice([50, 100, 200, 300, 500])), d])
    for _ in range(n_buy):
        st = random.choices(stores, weights=[x[7] for x in stores])[0]
        if on and random.random() < 0.4: st = stores[3]  # dorm residents eat at Cannon
        lo, hi = st[6]
        d = base + timedelta(days=random.randint(0, 48), hours=random.randint(7, 22), minutes=random.randint(0, 59))
        txns.append([s[0], "Purchase", st[0], round(random.uniform(lo, hi), 2), d])
txns.sort(key=lambda t: t[4])
insert("cougarcash_transactions", [(i + 1, t[0], t[1], t[2], t[3], t[4].strftime("%Y-%m-%d %H:%M")) for i, t in enumerate(txns)])

sys.stdout.write("-- Fictional seed data for the BYU Student Records database. Any resemblance to real students is coincidental.\n\n" + "\n".join(out))
