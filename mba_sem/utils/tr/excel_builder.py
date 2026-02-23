import os
import io
from django.conf import settings
from openpyxl.drawing.image import Image as XLImage
from mba_sem.models import MBACourseStructure
from mba_sem.utils.tr.grading import (
    calculate_numeric_grade,
    calculate_grade_point,
    get_letter_and_description,
)
from openpyxl.styles import Font

class MBAResultExcelBuilder:

    COL_START = 14
    DATA_START_ROW = 17
    STUDENTS_PER_PAGE = 5

    def __init__(
        self,
        wb,
        master_sheet,
        students,
        college,
        all_assessments,
        subject_master,
        student_map,
        subject_codes,
        semester,
        exam_name=None
    ):
        self.wb = wb
        self.master_sheet = master_sheet
        self.students = list(students)
        self.college = college
        self.all_assessments = all_assessments
        self.subject_master = subject_master or {}
        self.student_map = student_map or {}
        self.subject_codes = subject_codes or []
        self.semester = str(semester)
        self.exam_name = exam_name
        self.subject_structure = {}

    # ======================================================
    # LOGO
    # ======================================================

    def _add_logo(self, ws):

        logo_path = os.path.join(
            "static/images/",
            "purnea-logo.png"
        )

        if not os.path.exists(logo_path):
            print("Logo not found:", logo_path)
            return

        img = XLImage(logo_path)
        img.width = 110
        img.height = 110
        img.anchor = "W1"

        ws.add_image(img)

    # ======================================================
    # BUILD
    # ========================f==============================

    def build(self):

        pages = [
            self.students[i:i + self.STUDENTS_PER_PAGE]
            for i in range(0, len(self.students), self.STUDENTS_PER_PAGE)
        ]

        for index, student_chunk in enumerate(pages):

            ws = self.wb.copy_worksheet(self.master_sheet)
            ws.title = f"Page_{index+1}"

            self._add_logo(ws)
            self._build_header(ws, student_chunk)
            self._build_subject_header(ws)
            self._build_students(ws, student_chunk)
            self._build_footer(ws, student_chunk)   

        if "MASTER_TEMPLATE" in self.wb.sheetnames:
            self.wb.remove(self.wb["MASTER_TEMPLATE"])

    # ======================================================
    # HEADER
    # ======================================================

    def _build_header(self, ws, student_chunk):
        ws["A4"] = self.exam_name or ""
        ws["AP4"] = f"Dept./College : {self.college.name}"

        if student_chunk and student_chunk[0].course:
            ws["AP2"] = f"Subject : {student_chunk[0].course.name}"

    # ======================================================
    # SUBJECT HEADER
    # ======================================================

    def _build_subject_header(self, ws):

        col_pointer = self.COL_START

        for code in self.subject_codes:

            structures = MBACourseStructure.objects.filter(
                course_code=code,
                semester=self.semester
            )

            has_ese = False
            has_cia = False
            ese_max = cia_max = 0
            ese_pass = cia_pass = 0
            credit = 0

            for obj in structures:
                label = str(obj.label or "").upper()
                credit = float(obj.credit or 0)

                if label.startswith("ESE"):
                    has_ese = True
                    ese_max += float(obj.max_marks or 0)
                    ese_pass += float(obj.min_marks or 0)

                if label.startswith("CIA"):
                    has_cia = True
                    cia_max += float(obj.max_marks or 0)
                    cia_pass += float(obj.min_marks or 0)

            if not has_ese and not has_cia:
                continue

            headers = []
            if has_ese:
                headers.append("ESE")
            if has_cia:
                headers.append("CIA")

            headers += [
                "Total",
                "Credit Alloted",
                "Numeric Grade",
                "Credit Earned",
                "GP"
            ]

            self.subject_structure[code] = {
                "headers": headers,
                "credit": credit,
                "has_ese": has_ese,
                "has_cia": has_cia,
                "ese_pass": ese_pass,
                "cia_pass": cia_pass,
            }

            width = len(headers)

            ws.merge_cells(start_row=5, start_column=col_pointer,
                           end_row=5, end_column=col_pointer + width - 1)
            ws.cell(row=5, column=col_pointer).value = \
                self.subject_master.get(code, code)

            ws.merge_cells(start_row=6, start_column=col_pointer,
                           end_row=6, end_column=col_pointer + width - 1)
            ws.cell(row=6, column=col_pointer).value = code

            for i, header in enumerate(headers):
                ws.cell(row=7, column=col_pointer + i).value = header

            col_offset = col_pointer

            if has_ese:
                ws.cell(row=14, column=col_offset).value = ese_max
                ws.cell(row=15, column=col_offset).value = ese_pass
                col_offset += 1

            if has_cia:
                ws.cell(row=14, column=col_offset).value = cia_max
                ws.cell(row=15, column=col_offset).value = cia_pass
                col_offset += 1

            ws.cell(row=14, column=col_offset).value = ese_max + cia_max
            ws.cell(row=15, column=col_offset).value = ese_pass + cia_pass
            ws.cell(row=14, column=col_offset + 1).value = credit

            col_pointer += width

        self.gpa_start_col = col_pointer

    # ======================================================
    # STUDENTS
    # ======================================================

    def _build_students(self, ws, student_chunk):

        row_pointer = self.DATA_START_ROW

        # SEM blocks start column (E = 5)
        sem1_col = 5
        sem2_col = 8
        sem3_col = 11

        for student in student_chunk:

            ws.cell(row=row_pointer, column=1).value = student.roll_no
            ws.cell(row=row_pointer, column=2).value = student.get_full_name()
            ws.cell(row=row_pointer, column=3).value = student.registration_no

            # ===== SEM 1 =====
            ws.cell(row=row_pointer, column=sem1_col).value = student.roll_no
            ws.cell(row=row_pointer, column=sem1_col + 1).value = student.sem_1_gpa
            ws.cell(row=row_pointer, column=sem1_col + 2).value = student.sem_1_credit_earned

            # ===== SEM 2 =====
            ws.cell(row=row_pointer, column=sem2_col).value = student.roll_no
            ws.cell(row=row_pointer, column=sem2_col + 1).value = student.sem_2_gpa
            ws.cell(row=row_pointer, column=sem2_col + 2).value = student.sem_2_credit_earned

            # ===== SEM 3 =====
            ws.cell(row=row_pointer, column=sem3_col).value = student.roll_no
            ws.cell(row=row_pointer, column=sem3_col + 1).value = student.sem_3_gpa
            ws.cell(row=row_pointer, column=sem3_col + 2).value = student.sem_3_credit_earned


            col_pointer = self.COL_START

            total_credit_allotted = 0
            total_credit_earned = 0
            total_grade_points = 0
            failed = False
            student_appeared = False

            for code, meta in self.subject_structure.items():

                headers = meta["headers"]
                credit_alloted = float(meta.get("credit", 0))
                has_ese = meta.get("has_ese", False)
                has_cia = meta.get("has_cia", False)
                ese_pass_req = float(meta.get("ese_pass", 0))
                cia_pass_req = float(meta.get("cia_pass", 0))

                ese_marks = 0
                cia_marks = 0
                ese_passed = True
                cia_passed = True
                ese_absent = False
                cia_absent = False

                ese_found = False
                cia_found = False

                for rec in self.student_map.get(student.id, []):
                    if rec.paper_code == code:
                        label = str(rec.label or "").upper()
                        is_absent = bool(rec.ind_is_absent)
                        marks = float(
                            rec.ind_final_marks_obtained
                            if rec.ind_final_marks_obtained is not None
                            else (rec.ind_marks_obtained or 0)
                        )
                        if label.startswith("ESE"):
                            ese_marks = marks
                            ese_found = True
                            ese_absent = is_absent
                        elif label.startswith("CIA"):
                            cia_marks = marks
                            cia_found = True
                            cia_absent = is_absent

                # Determine if passed both parts
                if has_ese:
                    ese_passed = (ese_marks >= ese_pass_req) if (ese_found and not ese_absent) else (ese_pass_req <= 0)
                if has_cia:
                    cia_passed = (cia_marks >= cia_pass_req) if (cia_found and not cia_absent) else (cia_pass_req <= 0)

                total = ese_marks + cia_marks
                numeric = calculate_numeric_grade(total) if not (ese_absent and cia_absent) else 0

                # Track if student appeared for AT LEAST ONE component
                if ese_found and not ese_absent: student_appeared = True
                if cia_found and not cia_absent: student_appeared = True

                # CREDIT LOGIC
                if ese_passed and cia_passed and numeric >= 5 and not (ese_absent or cia_absent):
                    credit_earned = credit_alloted
                else:
                    credit_earned = 0
                    failed = True

                gp = calculate_grade_point(numeric, credit_earned)

                total_credit_allotted += credit_alloted
                total_credit_earned += credit_earned
                total_grade_points += gp

                values = {
                    "ESE": "AB" if ese_absent else ese_marks,
                    "CIA": "AB" if cia_absent else cia_marks,
                    "Total": "AB" if (ese_absent and cia_absent) else total,
                    "Credit Alloted": credit_alloted,
                    "Numeric Grade": numeric if not (ese_absent and cia_absent) else 0,
                    "Credit Earned": credit_earned,
                    "GP": gp
                }

                for i, header in enumerate(headers):
                    ws.cell(
                        row=row_pointer,
                        column=col_pointer + i
                    ).value = values.get(header, "")

                col_pointer += len(headers)

            # ===== GPA & OVERALL RESULT =====
            if not student_appeared:
                # Student did not appear for ANY component
                gpa = 0.00
                letter, desc = "AB", "Absent"
                result_status = "Absent"
            elif failed:
                # If any subject is failed (credit_earned=0), the overall result is Fail
                gpa = 0.00
                letter, desc = "F", "Fail"
                result_status = "Fail"
            else:
                # If all subjects passed, calculate weighted GPA
                gpa = round(
                    total_grade_points / total_credit_earned, 2
                ) if total_credit_earned > 0 else 0
                letter, desc = get_letter_and_description(gpa)
                result_status = "Pass"

            summary_col = 55

            ws.cell(row=row_pointer, column=summary_col).value = total_credit_allotted
            ws.cell(row=row_pointer, column=summary_col + 1).value = total_credit_earned
            ws.cell(row=row_pointer, column=summary_col + 2).value = gpa
            ws.cell(row=row_pointer, column=summary_col + 3).value = letter
            ws.cell(row=row_pointer, column=summary_col + 4).value = desc
            ws.cell(row=row_pointer, column=summary_col + 5).value = result_status

            row_pointer += 1

    def _build_footer(self, ws, student_chunk):
        MAX_STUDENTS_PER_PAGE = 5

        footer_row = self.DATA_START_ROW + MAX_STUDENTS_PER_PAGE - 1 + 4

        page_total = len(student_chunk)
        page_pass = 0
        page_fail = 0
        page_absent = 0
        page_pending = 0
        page_expelled = 0
        page_promoted = 0

        summary_col = 55
        result_status_col = summary_col + 5

        for i in range(len(student_chunk)):
            row = self.DATA_START_ROW + i
            status = ws.cell(row=row, column=result_status_col).value

            if status == "Pass":
                page_pass += 1
            elif status == "Fail":
                page_fail += 1
            elif status == "Absent":
                page_absent += 1

        # ===== LEFT BLOCK =====
        ws.cell(row=footer_row, column=2).value = f"No of Students : {page_total}"
        ws.cell(row=footer_row + 1, column=2).value = f"Pass : {page_pass}"
        ws.cell(row=footer_row + 2, column=2).value = f"Promoted : {page_promoted}"

        # ===== CENTER BLOCK =====
        ws.cell(row=footer_row, column=8).value = f"Expelled : {page_expelled}"
        ws.cell(row=footer_row + 1, column=8).value = f"Fail : {page_fail}"
        ws.cell(row=footer_row + 2, column=8).value = f"Qualified : 0"

        # ===== RIGHT BLOCK =====
        ws.cell(row=footer_row + 1 , column=14).value = f"Absent : {page_absent}"
        ws.cell(row=footer_row + 2, column=14).value = f"Result Pending : {page_pending}"

        # ===== SIGN AREA =====
        sign_row = footer_row + 2
        normal_font = Font(name="Calibri", size=11, color="000000")

        ws.cell(row=sign_row, column=22).value = "Compared By Address"
        ws.cell(row=sign_row, column=38).value = "Full Signature of Tabulator-cum-scrutinizer with date"
        ws.cell(row=sign_row, column=58).value = "Controller of Examination"
        