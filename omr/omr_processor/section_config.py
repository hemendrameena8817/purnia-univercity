"""
section_config.py
=================
Defines ALL sections for Part C and Part D OMR sheets.

ROI format: (x1_rel, y1_rel, x2_rel, y2_rel)  — all values between 0.0 and 1.0
These are RELATIVE to the normalized (perspective-corrected) image size (800x1100).

Calibrated against:  SKM_C30826030713191.pdf  (Purnea University Part D scan)
"""

NORM_W = 1600  # pixels — width of normalized sheet (doubled for reliable bubble detection)
NORM_H = 2200  # pixels — height of normalized sheet

# ─────────────────────────────────────────────────────────────────────────────
# PART D  (Student info sheet)
# ─────────────────────────────────────────────────────────────────────────────
PART_D_SECTIONS = {
    "barcode": {
        "label": "Serial / Barcode",
        "type": "barcode",
        "orientation": "vertical",
        "roi": (0.18, 0.0, 0.45, 0.21),
    },
    "roll_number": {
        "label": "Roll Number",
        "type": "bubble_grid",
        "roi": (0.045, 0.310, 0.677, 0.563),
        "rows": 10,
        "cols": 11,
        "values": list("0123456789"),
        "select": "one_per_col",
    },
    "center_code": {
        "label": "Center Code",
        "type": "bubble_grid",
        "roi": (0.69, 0.310, 0.92, 0.563),
        "rows": 10,
        "cols": 4,
        "values": list("0123456789"),
        "select": "one_per_col",
    },
    "year": {
        "label": "Year",
        "type": "bubble_grid",
        "roi": (0.02, 0.631, 0.10, 0.739),
        "rows": 4,
        "cols": 1,
        "values": ["1", "2", "3", "4"],
        "select": "one_per_col",
        "skip_refine": True,
    },
    "sem": {
        "label": "Semester",
        "type": "bubble_grid",
        "roi": (0.08, 0.631, 0.165, 0.882),
        "rows": 10,
        "cols": 1,
        "values": list("0123456789"),
        "select": "one_per_col",
        "skip_refine": True,
    },
    "course_code": {
        "label": "Course Code",
        "type": "bubble_grid",
        "roi": (0.234, 0.631, 0.677, 0.882),
        "rows": 10,
        "cols": 7,
        "values": list("0123456789"),
        "prefix_col": {
            "col_index": 0,
            "options": ["U", "P"],
        },
        "select": "one_per_col",
    },
    "session": {
        "label": "Session",
        "type": "bubble_grid",
        "roi": (0.704, 0.631, 0.921, 0.882),
        "rows": 10,
        "cols": 4,
        "values": list("0123456789"),
        "select": "one_per_col",
    },
    "exam_type": {
        "label": "Exam Type",
        "type": "radio",
        "roi": (0.045, 0.922, 0.677, 0.976),
        "options": ["Regular", "Back Paper", "Ex.", "Improvement"],
        "direction": "grid",
        "grid_rows": 2,
        "grid_cols": 2,
        "select": "one",
    },
    "sitting": {
        "label": "Sitting",
        "type": "radio",
        "roi": (0.82, 0.922, 0.92, 0.976),
        "options": ["First", "Second"],
        "direction": "vertical",
        "select": "one",
    },
}



# ─────────────────────────────────────────────────────────────────────────────
# PART C  (Evaluator / Marks sheet)
# ─────────────────────────────────────────────────────────────────────────────
PART_C_SECTIONS = {
    "barcode": {
        "label": "Serial / Barcode",
        "type": "barcode",
        "orientation": "vertical",
        "roi": (0.66, 0.015, 0.985, 0.255),
    },
    "ug_old": {
        "label": "UG Old (Part)",
        "type": "radio",
        "roi": (0.20, 0.09, 0.28, 0.17),
        "options": ["Part-I", "Part-II", "Part-III"],
        "direction": "vertical",
        "select": "one",
    },
    "ug_new": {
        "label": "UG New (Semester)",
        "type": "radio",
        "roi": (0.40, 0.08, 0.50, 0.29),
        "options": [
            "Sem-I", "Sem-II", "Sem-III", "Sem-IV",
            "Sem-V", "Sem-VI", "Sem-VII", "Sem-VIII",
        ],
        "direction": "vertical",
        "select": "one",
    },
    "pg_sem": {
        "label": "PG Semester",
        "type": "radio",
        "roi": (0.62, 0.08, 0.70, 0.20),
        "options": ["Sem-I", "Sem-II", "Sem-III", "Sem-IV"],
        "direction": "vertical",
        "select": "one",
    },
    "faculty": {
        "label": "Faculty",
        "type": "radio",
        "roi": (0.19, 0.36, 0.25, 0.60),
        "options": ["Arts", "Science", "Commerce", "Education", "Vocational", "Law", "Other"],
        "direction": "vertical",
        "select": "one",
    },
    "course_code": {
        "label": "Course Code",
        "type": "bubble_grid",
        "roi": (0.30, 0.36, 0.70, 0.62),
        "rows": 10,
        "cols": 7,
        "values": list("0123456789"),
        "prefix_col": {"col_index": 0, "options": ["U", "P"]},
        "select": "one_per_col",
    },
    "center_code": {
        "label": "Center Code",
        "type": "bubble_grid",
        "roi": (0.72, 0.36, 0.93, 0.61),
        "rows": 10,
        "cols": 4,
        "values": list("0123456789"),
        "select": "one_per_col",
    },
    "marks_obtained": {
        "label": "Marks Obtained",
        "type": "bubble_grid",
        "roi": (0.02, 0.73, 0.14, 0.98),
        "rows": 10,
        "cols": 2,
        "values": list("0123456789"),
        "col_labels": ["Tens", "Units"],
        "select": "one_per_col",
    },
    "total_marks": {
        "label": "Total Marks",
        "type": "bubble_grid",
        "roi": (0.17, 0.73, 0.30, 0.98),
        "rows": 10,
        "cols": 2,
        "values": list("0123456789"),
        "col_labels": ["Tens", "Units"],
        "select": "one_per_col",
    },
}

SECTION_MAP = {
    "C": PART_C_SECTIONS,
    "D": PART_D_SECTIONS,
}