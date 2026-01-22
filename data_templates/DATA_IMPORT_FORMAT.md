# Data Import Templates - PUP UMIS

This document describes the Excel format required for importing legacy data into the PUP UMIS system.

---

## 📋 Complete Sheet List

| # | Sheet Name | Category | Description |
|---|------------|----------|-------------|
| 1 | Colleges | Master Data | College/Institute details |
| 2 | Faculties | Master Data | Academic faculties |
| 3 | Departments | Master Data | Departments under faculties |
| 4 | Degrees | Master Data | Degree types (BCA, MBA, etc.) |
| 5 | Programs | Master Data | Programs linked to degrees |
| 6 | Batches | Master Data | Student batches (2024-2028) |
| 7 | Sessions | Master Data | Academic sessions (2024-2025) |
| 8 | ExamCentres | Master Data | Examination centres |
| 9 | Courses | Course Data | Course/Subject with slot, credits, marks info |
| 10 | Students | Student Data | Student master data |
| 11 | CIAMarks | Marks Data | Continuous Internal Assessment marks |
| 12 | FinalMarks | Marks Data | End semester/Final exam marks |
| 13 | SemesterResults | Results | Semester-wise aggregated results |
| 14 | OverallResults | Results | Final CGPA and division |
| 15 | TabulationRegister | TR Data | Tabulation register format |
| 16 | ProvisionalCertificate | Certificates | Provisional certificate data |
| 17 | DegreeCertificate | Certificates | Final degree certificate data |
| 18 | MigrationCertificate | Certificates | Migration certificate data |

---

## 🏛️ MASTER DATA SHEETS

### Sheet 1: Colleges / Institutes

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| name | ✅ Yes | Text (255) | ABC College | Full college name |
| short_name | ✅ Yes | Text (100) | ABCC | Short name |
| college_code | ✅ Yes | Text (50) | COL001 | Unique college code |
| address | ✅ Yes | Text | Main Road, Purnea | Full address |
| principal | ✅ Yes | Text (255) | Dr. Shyam Das | Principal name |
| contact_no | No | Text (15) | 9876543211 | Contact number |
| email | No | Email | abc@college.edu | College email |
| founded | No | Date | 1990-07-01 | Format: YYYY-MM-DD |
| website | No | URL | https://abccollege.edu | Website |

---

### Sheet 2: Faculties

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| name | ✅ Yes | Text (255) | Faculty of Science | Full faculty name |
| short_name | No | Text (100) | FoS | Short name |
| description | No | Text | Science and Technology | Description |

---

### Sheet 3: Departments

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| name | ✅ Yes | Text (255) | Department of Computer Science | Full department name |
| code | ✅ Yes | Text (50) | CS | Unique department code |
| faculty_name | ✅ Yes | Text | Faculty of Science | Reference to faculty |

---

### Sheet 4: Degrees

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| name | ✅ Yes | Text (255) | Bachelor of Computer Applications | Full degree name |
| degree_level | ✅ Yes | Text | UG | Options: UG (Undergraduate), PG (Postgraduate) |
| total_semesters | ✅ Yes | Integer | 6 | Total number of semesters |
| total_years | ✅ Yes | Integer | 3 | Duration in years |

---

### Sheet 5: Programs

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| name | ✅ Yes | Text (255) | BCA (Honours) | Full program name |
| short_name | ✅ Yes | Text (50) | BCA | Short name |
| degree_name | ✅ Yes | Text | Bachelor of Computer Applications | Reference to degree |
| department_code | No | Text | CS | Reference to department |

---

### Sheet 6: Batches

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| name | ✅ Yes | Text (50) | 2024-2028 | Batch name (admission-graduation) |
| start_year | ✅ Yes | Integer | 2024 | Admission year |
| end_year | ✅ Yes | Integer | 2028 | Expected graduation year |
| is_active | ✅ Yes | Boolean | TRUE | Is batch currently active? |

---

### Sheet 7: Sessions

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| name | ✅ Yes | Text (50) | 2024-2025 | Academic session |
| start_date | ✅ Yes | Date | 2024-07-01 | Session start date |
| end_date | ✅ Yes | Date | 2025-06-30 | Session end date |
| is_current | ✅ Yes | Boolean | TRUE | Is current session? |

---

### Sheet 8: Exam Centres

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| centre_code | ✅ Yes | Text (50) | EC001 | Unique exam centre code |
| centre_name | ✅ Yes | Text (255) | ABC College Exam Centre | Exam centre name |
| address | ✅ Yes | Text | Main Road, Purnea | Full address |
| city | ✅ Yes | Text (100) | Purnea | City |
| district | ✅ Yes | Text (100) | Purnea | District |
| state | ✅ Yes | Text (100) | Bihar | State |
| pincode | No | Text (10) | 854301 | PIN code |
| college_code | No | Text | COL001 | Reference to college (if centre is at a college) |
| contact_person | No | Text (255) | Dr. A.K. Singh | Centre in-charge name |
| contact_phone | No | Text (15) | 9876543210 | Contact phone |
| contact_email | No | Email | ecabc@college.edu | Contact email |
| seating_capacity | No | Integer | 500 | Total seating capacity |
| is_active | ✅ Yes | Boolean | TRUE | Is centre active? |

---

## 📚 COURSE DATA

### Sheet 9: Courses / Subjects

This sheet contains all course information including slot mapping, credits, and marks distribution.

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| name | ✅ Yes | Text (255) | Introduction to Programming | Course/Subject name |
| code | ✅ Yes | Text (50) | BCA101 | Unique course code |
| course_slot | ✅ Yes | Text (20) | MJC-1 | Course slot (MJC-1, MNC-2, SEC-1, etc.) |
| semester | ✅ Yes | Integer | 1 | Semester number |
| credits | ✅ Yes | Integer | 4 | Course credits |
| cia_marks | ✅ Yes | Integer | 25 | CIA/Internal marks |
| final_marks | ✅ Yes | Integer | 75 | Final exam marks |
| total_marks | ✅ Yes | Integer | 100 | Total marks |
| description | No | Text | Basics of programming | Description |
| department_code | No | Text | CS | Reference to department |
| program_short_name | ✅ Yes | Text | BCA | Reference to program |
| is_elective | No | Boolean | FALSE | Is this an elective? |
| is_active | No | Boolean | TRUE | Is course active? |

**Standard Course Slots:**
- MJC-1, MJC-2, MJC-3... - Major Courses (4 credits, 25+75=100 marks)
- MNC-1, MNC-2... - Minor Courses (4 credits, 25+75=100 marks)
- SEC-1, SEC-2... - Skill Enhancement Courses (2 credits, 15+35=50 marks)
- VAC-1, VAC-2... - Value Added Courses (2 credits, 15+35=50 marks)
- AEC-1, AEC-2... - Ability Enhancement Courses (2 credits, 15+35=50 marks)
- GE-1, GE-2... - Generic Electives (4 credits, 25+75=100 marks)

---

## 👨‍🎓 STUDENT DATA

### Sheet 10: Students

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| first_name | ✅ Yes | Text (255) | Rahul | Student's first name |
| last_name | ✅ Yes | Text (255) | Kumar | Student's last name |
| email | ✅ Yes | Email | rahul.kumar@email.com | Student email (for login) |
| phone | No | Text (15) | 9876543212 | Phone number |
| registration_no | ✅ Yes | Text (50) | PUP2024001 | Unique registration number |
| roll_no | ✅ Yes | Text (50) | 2024BCA001 | Unique roll number |
| date_of_birth | ✅ Yes | Date | 2002-05-15 | Format: YYYY-MM-DD |
| gender | ✅ Yes | Text | Male | Options: Male, Female, Other |
| address | ✅ Yes | Text | Village XYZ, District Purnea | Full address |
| father_name | ✅ Yes | Text (255) | Shri Ram Kumar | Father's name |
| mother_name | ✅ Yes | Text (255) | Smt. Sita Devi | Mother's name |
| admission_date | ✅ Yes | Date | 2024-08-01 | Date of admission |
| enrollment_date | ✅ Yes | Date | 2024-08-15 | Date of enrollment |
| batch | ✅ Yes | Text (50) | 2024-2028 | Batch name |
| session | ✅ Yes | Text (50) | 2024-2025 | Current session |
| current_semester | ✅ Yes | Integer | 1 | Current semester |
| status | ✅ Yes | Text | Active | Options: Active, Suspended, Alumni |
| college_code | ✅ Yes | Text | COL001 | Reference to college |
| department_code | No | Text | CS | Reference to department |
| program_short_name | ✅ Yes | Text | BCA | Reference to program |

---

## 📝 MARKS DATA

### Sheet 11: CIA Marks (Continuous Internal Assessment)

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| registration_no | ✅ Yes | Text | PUP2024001 | Student registration number |
| email | ✅ Yes | Email | rahul@email.com | Student email |
| session | ✅ Yes | Text | 2024-2025 | Academic session |
| semester | ✅ Yes | Integer | 1 | Semester number |
| course_code | ✅ Yes | Text | BCA101 | Course code |
| course_slot | ✅ Yes | Text | MJC-1 | Course slot |
| theory_marks | No | Integer | 12 | Theory CIA marks obtained |
| theory_max | No | Integer | 15 | Theory CIA max marks |
| practical_marks | No | Integer | 8 | Practical CIA marks obtained |
| practical_max | No | Integer | 10 | Practical CIA max marks |
| total_marks_obtained | ✅ Yes | Integer | 20 | Total CIA marks obtained |
| max_marks | ✅ Yes | Integer | 25 | Maximum CIA marks |
| grade_points | No | Decimal | 8.0 | Grade points (0-10) |
| grade_letter | No | Text | A | Grade letter (O/A+/A/B+/B/C/D/F) |
| grade_description | No | Text | Excellent | Grade description |
| status | ✅ Yes | Text | Completed | Completed/Pending/Absent |

---

### Sheet 12: Final Marks (End Semester Exam)

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| registration_no | ✅ Yes | Text | PUP2024001 | Student registration number |
| email | ✅ Yes | Email | rahul@email.com | Student email |
| session | ✅ Yes | Text | 2024-2025 | Academic session |
| semester | ✅ Yes | Integer | 1 | Semester number |
| exam_type | ✅ Yes | Text | Regular | Options: Regular, BACK |
| course_code | ✅ Yes | Text | BCA101 | Course code |
| course_slot | ✅ Yes | Text | MJC-1 | Course slot |
| theory_marks | No | Integer | 45 | Theory marks obtained |
| theory_max | No | Integer | 50 | Theory max marks |
| practical_marks | No | Integer | 20 | Practical marks obtained |
| practical_max | No | Integer | 25 | Practical max marks |
| total_final_obtained | ✅ Yes | Integer | 65 | Total final marks obtained |
| total_final_max | ✅ Yes | Integer | 75 | Maximum final marks |
| grade_points | No | Decimal | 8.0 | Grade points (0-10) |
| grade_letter | No | Text | A | Grade letter (O/A+/A/B+/B/C/D/F) |
| grade_description | No | Text | Excellent | Grade description |
| exam_date | No | Date | 2024-12-15 | Exam date |
| status | ✅ Yes | Text | Pass | Pass/Fail/Absent |

---

## 📊 RESULTS DATA

### Sheet 13: Semester Results (Aggregated)

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| registration_no | ✅ Yes | Text | PUP2024001 | Student registration number |
| email | ✅ Yes | Email | rahul@email.com | Student email |
| session | ✅ Yes | Text | 2024-2025 | Academic session |
| semester | ✅ Yes | Integer | 1 | Semester number |
| exam_type | ✅ Yes | Text | Regular | Options: Regular, BACK |
| total_credits | ✅ Yes | Integer | 22 | Total credits in semester |
| credits_earned | ✅ Yes | Integer | 22 | Credits earned |
| total_cia_obtained | ✅ Yes | Integer | 120 | Total CIA marks |
| total_cia_max | ✅ Yes | Integer | 150 | Max CIA marks |
| total_final_obtained | ✅ Yes | Integer | 330 | Total final marks |
| total_final_max | ✅ Yes | Integer | 400 | Max final marks |
| total_marks_obtained | ✅ Yes | Integer | 450 | Grand total marks |
| total_max_marks | ✅ Yes | Integer | 550 | Grand total max |
| percentage | ✅ Yes | Decimal | 81.82 | Percentage |
| sgpa | ✅ Yes | Decimal | 8.15 | Semester GPA |
| grade_letter | No | Text | A | Overall grade letter |
| grade_description | No | Text | Excellent | Overall grade description |
| result_status | ✅ Yes | Text | Pass | Pass/Fail/Promoted |
| result_date | No | Date | 2025-02-15 | Result declaration date |
| remarks | No | Text | | Any remarks |

---

### Sheet 14: Overall Results (CGPA/Final)

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| registration_no | ✅ Yes | Text | PUP2024001 | Student registration number |
| email | ✅ Yes | Email | rahul@email.com | Student email |
| program_short_name | ✅ Yes | Text | BCA | Program |
| batch | ✅ Yes | Text | 2024-2028 | Batch |
| total_semesters_completed | ✅ Yes | Integer | 6 | Semesters completed |
| total_credits | ✅ Yes | Integer | 132 | Total credits |
| credits_earned | ✅ Yes | Integer | 132 | Credits earned |
| total_marks_obtained | ✅ Yes | Integer | 2850 | Total marks |
| total_max_marks | ✅ Yes | Integer | 3300 | Maximum marks |
| overall_percentage | ✅ Yes | Decimal | 86.36 | Overall percentage |
| cgpa | ✅ Yes | Decimal | 8.50 | Cumulative GPA |
| grade_letter | ✅ Yes | Text | A+ | Final grade letter |
| grade_description | ✅ Yes | Text | Outstanding | Final grade description |
| division | ✅ Yes | Text | First Division with Distinction | Division |
| final_result | ✅ Yes | Text | Pass | Pass/Fail |
| completion_date | No | Date | 2027-06-30 | Course completion date |

---

## 📋 TABULATION REGISTER DATA

### Sheet 15: TR Data (Tabulation Register)

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| registration_no | ✅ Yes | Text | PUP2024001 | Student registration number |
| email | ✅ Yes | Email | rahul@email.com | Student email |
| roll_no | ✅ Yes | Text | 2024BCA001 | Roll number |
| student_name | ✅ Yes | Text | Rahul Kumar | Full name |
| father_name | ✅ Yes | Text | Shri Ram Kumar | Father's name |
| program_short_name | ✅ Yes | Text | BCA | Program |
| session | ✅ Yes | Text | 2024-2025 | Session |
| semester | ✅ Yes | Integer | 3 | Current semester |
| exam_type | ✅ Yes | Text | Regular | Options: Regular, BACK |
| college_code | ✅ Yes | Text | COL001 | College code |

**Per Course Marks (for each course 1-5):**

| Column Pattern | Required | Data Type | Example | Description |
|----------------|----------|-----------|---------|-------------|
| course{N}_code | No | Text | BCA301 | Course code |
| course{N}_cia | No | Integer | 20 | CIA marks |
| course{N}_theory | No | Integer | 45 | Theory marks |
| course{N}_practical | No | Integer | 15 | Practical marks |
| course{N}_total | No | Integer | 80 | Total marks |

**Current Semester Totals:**

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| current_sem_total_marks | ✅ Yes | Integer | 315 | Current sem total marks |
| current_sem_credits | ✅ Yes | Integer | 22 | Current sem credits |
| current_sem_sgpa | ✅ Yes | Decimal | 8.15 | Current sem SGPA |

**Previous Semester Credits (Cumulative):**

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| sem1_credits_earned | No | Integer | 22 | Credits earned in Sem 1 |
| sem2_credits_earned | No | Integer | 22 | Credits earned in Sem 2 |
| sem3_credits_earned | No | Integer | 22 | Credits earned in Sem 3 |
| sem4_credits_earned | No | Integer | 22 | Credits earned in Sem 4 |
| sem5_credits_earned | No | Integer | 22 | Credits earned in Sem 5 |
| sem6_credits_earned | No | Integer | 0 | Credits earned in Sem 6 |

**Cumulative & Result:**

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| total_credits_earned | ✅ Yes | Integer | 66 | Total cumulative credits |
| cgpa | ✅ Yes | Decimal | 7.85 | Cumulative GPA |
| result | ✅ Yes | Text | Pass | Pass/Fail/Promoted |
| remarks | No | Text | | Any remarks |

---

## 📜 CERTIFICATE DATA

### Sheet 16: Provisional Certificate Data

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| registration_no | ✅ Yes | Text | PUP2021001 | Student registration number |
| roll_no | ✅ Yes | Text | 2021BCA001 | Roll number |
| student_name | ✅ Yes | Text | Rahul Kumar | Full name |
| father_name | ✅ Yes | Text | Shri Ram Kumar | Father's name |
| mother_name | ✅ Yes | Text | Smt. Sita Devi | Mother's name |
| date_of_birth | ✅ Yes | Date | 2002-05-15 | Date of birth |
| program_name | ✅ Yes | Text | Bachelor of Computer Applications | Program full name |
| program_short_name | ✅ Yes | Text | BCA | Program short name |
| college_name | ✅ Yes | Text | ABC College | College name |
| batch | ✅ Yes | Text | 2021-2024 | Batch |
| passing_session | ✅ Yes | Text | 2023-2024 | Passing session |
| passing_year | ✅ Yes | Integer | 2024 | Passing year |
| cgpa | ✅ Yes | Decimal | 8.50 | CGPA |
| percentage | ✅ Yes | Decimal | 86.36 | Percentage |
| division | ✅ Yes | Text | First Division with Distinction | Division |
| result | ✅ Yes | Text | Pass | Pass/Fail |
| certificate_no | No | Text | PUP/PROV/2024/001 | Certificate number |
| issue_date | No | Date | 2024-07-15 | Issue date |
| status | ✅ Yes | Text | Pending | Pending/Verified/Approved/Issued |

---

### Sheet 17: Final/Degree Certificate Data

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| registration_no | ✅ Yes | Text | PUP2021001 | Student registration number |
| roll_no | ✅ Yes | Text | 2021BCA001 | Roll number |
| student_name | ✅ Yes | Text | Rahul Kumar | Full name |
| father_name | ✅ Yes | Text | Shri Ram Kumar | Father's name |
| mother_name | ✅ Yes | Text | Smt. Sita Devi | Mother's name |
| date_of_birth | ✅ Yes | Date | 2002-05-15 | Date of birth |
| degree_name | ✅ Yes | Text | Bachelor of Computer Applications | Degree name |
| program_name | ✅ Yes | Text | BCA (Honours) | Program name |
| specialization | No | Text | Computer Science | Specialization if any |
| college_name | ✅ Yes | Text | ABC College | College name |
| batch | ✅ Yes | Text | 2021-2024 | Batch |
| passing_session | ✅ Yes | Text | 2023-2024 | Passing session |
| passing_year | ✅ Yes | Integer | 2024 | Passing year |
| cgpa | ✅ Yes | Decimal | 8.50 | Final CGPA |
| percentage | ✅ Yes | Decimal | 86.36 | Final percentage |
| division | ✅ Yes | Text | First Division with Distinction | Division |
| total_credits | ✅ Yes | Integer | 132 | Total credits earned |
| convocation_date | No | Date | 2024-12-15 | Convocation date |
| certificate_no | No | Text | PUP/DEG/2024/001 | Certificate number |
| issue_date | No | Date | 2024-12-20 | Issue date |
| status | ✅ Yes | Text | Pending | Pending/Verified/Approved/Issued |

---

### Sheet 18: Migration Certificate Data

| Column Name | Required | Data Type | Example | Description |
|-------------|----------|-----------|---------|-------------|
| registration_no | ✅ Yes | Text | PUP2021001 | Student registration number |
| roll_no | ✅ Yes | Text | 2021BCA001 | Roll number |
| student_name | ✅ Yes | Text | Rahul Kumar | Full name |
| father_name | ✅ Yes | Text | Shri Ram Kumar | Father's name |
| date_of_birth | ✅ Yes | Date | 2002-05-15 | Date of birth |
| program_name | ✅ Yes | Text | BCA (Honours) | Program name |
| college_name | ✅ Yes | Text | ABC College | College name |
| passing_year | ✅ Yes | Integer | 2024 | Passing year |
| migrating_to | No | Text | XYZ University | Migrating to university |
| purpose | No | Text | Higher Studies | Purpose of migration |
| certificate_no | No | Text | PUP/MIG/2024/001 | Certificate number |
| issue_date | No | Date | 2024-08-01 | Issue date |
| status | ✅ Yes | Text | Pending | Pending/Verified/Approved/Issued |

---

## ⚠️ Important Notes

### Date Formats
- All dates should be in **YYYY-MM-DD** format (e.g., 2024-01-15)
- Excel may auto-format dates; ensure they are text or properly formatted

### Boolean Values
- Use **TRUE** or **FALSE** (or 1/0)

### Foreign Key References
- Use the reference columns (e.g., `college_code`, `program_short_name`) to link data
- These values must exist in the respective sheets before dependent data can be imported

### Import Order
Data should be imported in this order:
1. Colleges
2. Faculties
3. Departments
4. Degrees
5. Programs
6. Batches
7. Sessions
8. Exam Centres
9. Courses
10. Students
11. CIA Marks
12. Final Marks
13. Semester Results
14. Overall Results
15. TR Data
16. Provisional Certificates
17. Degree Certificates
18. Migration Certificates

### Validation Rules
- All required fields must have values
- Email addresses must be valid format
- Phone numbers: max 15 characters
- Unique fields (registration_no, roll_no, email, course_code) must not have duplicates
- Marks cannot exceed maximum marks

### Grading System
| Grade | Grade Points | Percentage Range | Description |
|-------|-------------|------------------|-------------|
| O | 10 | 90-100 | Outstanding |
| A+ | 9 | 80-89 | Outstanding |
| A | 8 | 70-79 | Excellent |
| B+ | 7 | 60-69 | Very Good |
| B | 6 | 50-59 | Good |
| C | 5 | 45-49 | Average |
| D | 4 | 40-44 | Below Average |
| F | 0 | Below 40 | Fail |

---

## 📞 Contact for Support

If you have questions about the data format, please contact the development team.
