import os
import uuid
import shutil
from django.conf import settings
from openpyxl import load_workbook

from .selectors import fetch_assessments
from .excel_builder import MBAResultExcelBuilder
from .pdf_converter import convert_excel_to_pdf


class MBAResultGenerator:

    TEMPLATE_PATH = os.path.join(
        settings.BASE_DIR,
        "courses_data/mba/MBA_Result_final.xlsx"
    )

    def __init__(self, students, college, semester, batch_uid=None):
        print("RESULT GENETOR.PY")
        self.students = list(students)
        self.college = college
        self.semester = str(semester)
        self.batch_uid = batch_uid

    def generate(self):

        if not self.students:
            return None

        temp_excel = os.path.join(
            "/tmp", f"mba_result_{uuid.uuid4().hex}.xlsx"
        )

        shutil.copy(self.TEMPLATE_PATH, temp_excel)

        wb = load_workbook(temp_excel)
        master_sheet = wb.active
        master_sheet.title = "MASTER_TEMPLATE"

        all_assessments, subject_master, student_map, subject_codes = fetch_assessments(
            self.students,
            self.college,
            self.semester,
            self.batch_uid
        )

        builder = MBAResultExcelBuilder(
            wb=wb,
            master_sheet=master_sheet,
            students=self.students,
            college=self.college,
            all_assessments=all_assessments,
            subject_master=subject_master,
            student_map=student_map,
            subject_codes=subject_codes,
            semester=self.semester
        )

        builder.build()

        wb.save(temp_excel)

        return convert_excel_to_pdf(temp_excel)