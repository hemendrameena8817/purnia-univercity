# mba_sem/utils/tr/grading.py

GRADE_STRUCTURE = [
    {"min": 91, "max": 100, "numeric": 10, "letter": "O",   "desc": "Outstanding"},
    {"min": 81, "max": 90,  "numeric": 9,  "letter": "A++", "desc": "Excellent"},
    {"min": 71, "max": 80,  "numeric": 8,  "letter": "A+",  "desc": "Very Good"},
    {"min": 61, "max": 70,  "numeric": 7,  "letter": "A",   "desc": "Good"},
    {"min": 51, "max": 60,  "numeric": 6,  "letter": "B+",  "desc": "Average"},
    {"min": 45, "max": 50,  "numeric": 5,  "letter": "B",   "desc": "Pass"},
    {"min": 0,  "max": 44,  "numeric": 0,  "letter": "F",   "desc": "Fail"},
]


def calculate_numeric_grade(total):
    try:
        total = float(total)
    except:
        return ""

    for rule in GRADE_STRUCTURE:
        if rule["min"] <= total <= rule["max"]:
            return rule["numeric"]
    return 0


def calculate_credit_obtained(ese, cia):
    def safe(obj, field):
        if obj and hasattr(obj, field):
            val = getattr(obj, field)
            return float(val) if val is not None else 0
        return 0

    ese_marks = safe(ese, "ind_marks_obtained")
    ese_pass = safe(ese, "ind_pass_marks")

    # Viva / No CIA case
    if not cia:
        return 4 if ese_marks >= ese_pass else 0

    cia_marks = safe(cia, "ind_marks_obtained")
    cia_pass = safe(cia, "ind_pass_marks")

    if ese_marks >= ese_pass and cia_marks >= cia_pass:
        return 4
    return 0


def calculate_grade_point(numeric_grade, credit_obtained):
    try:
        return float(numeric_grade) * float(credit_obtained)
    except:
        return 0


def get_letter_and_description(gpa):
    try:
        percent_value = float(gpa) * 10
    except:
        return "F", "Fail"

    for rule in GRADE_STRUCTURE:
        if rule["min"] <= percent_value <= rule["max"]:
            return rule["letter"], rule["desc"]

    return "F", "Fail"