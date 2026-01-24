# Master Data Import Scripts

This directory contains scripts to import course master data for Undergraduate (UG) and Postgraduate (PG) programs from Excel files.

## Prerequisites

1.  Ensure you have the latest code and the virtual environment is active (or use `poetry run`).
2.  Apply migrations first:
    ```bash
    poetry run python manage.py migrate
    ```
3.  Ensure the data files are present in `courses_data/` directory (or know the path where they are located).

## 1. Import UG Master Data

This script imports Faculties, Departments, Degrees, Batches, and Course Structures from the 8-semester UG Excel files.

**Command:**
```bash
poetry run python manage.py shell -c "exec(open('scripts/ug/import_ug_master_data.py').read()); import_ug_master_data(clear_existing=True)"
```

**Interaction:**
- The script will prompt you for the folder path containing the XLSX files.
- Press **Enter** to use the default path: `courses_data/ug/all_sem_courses`
- Or paste your custom path.

**What it does:**
- Creates `UGFaculty`, `UGDepartment`, `UGDegree`, `UGBatch`
- Creates `CourseStructure` entries reading exact codes from file headers.
- **Note:** `label` field (e.g., 'CIA Theory') is left blank intentionally to be populated by a separate script.

---

## 2. Import PG Master Data

This script imports Faculties, Departments, Degrees, Batches, and Course Structures from the multi-sheet PG Excel file.

**Command:**
```bash
poetry run python manage.py shell -c "exec(open('scripts/pg/import_pg_master_data.py').read()); import_pg_master_data(clear_existing=True)"
```

**Interaction:**
- The script will prompt you for the folder path.
- Press **Enter** to use the default path: `courses_data/pg`
- Or paste your custom path.

**What it does:**
- Creates `PGFaculty`, `PGDepartment`, `PGDegree`, `PGBatch`
- Creates `PGCourseStructure` entries reading exact codes.
- **Note:** `label` field is left blank intentionally.

---

## Troubleshooting

- **"File not found"**: Ensure the path you entered is correct and absolute (or relative to project root).
- **"Degree already exists"**: The script uses `get_or_create`, so running it multiple times is safe. Use `clear_existing=True` to wipe data before import if you want a fresh start.
