import os
import uuid
import shutil
from django.conf import settings
from openpyxl import load_workbook

from .selectors import fetch_assessments
from .excel_builder import MBAResultExcelBuilder
from .pdf_converter import convert_excel_to_pdf
from .mba_4th_sem import MBA4thSemResultGenerator


class MBAResultGenerator:

    TEMPLATE_PATH = os.path.join(
        settings.BASE_DIR,
        "mba_sem/static/tr/MBA_Result_2nd.xlsx"
    )

    def __init__(self, students, college, semester, batch_uid=None, exam_name=None, course_type=None, exam_month_year=None):
        print(f"RESULT GENETOR.PY | semester={semester} | course_type={course_type}")
        self.students = list(students)
        self.college = college
        self.semester = str(semester)
        self.batch_uid = batch_uid
        self.exam_name = exam_name
        self.course_type = course_type
        self.exam_month_year = exam_month_year

    def generate(self):

        if not self.students:
            return None

        # Route 4th semester to the dedicated static-subject builder
        if self.semester == "4":
            print("[MBAResultGenerator] Routing to MBA4thSemResultGenerator")
            gen = MBA4thSemResultGenerator(
                students=self.students,
                college=self.college,
                batch_uid=self.batch_uid,
                exam_name=self.exam_name,
                course_type=self.course_type,
                exam_month_year=self.exam_month_year,
            )
            return gen.generate()

        # All other semesters → dynamic subject builder
        temp_excel = os.path.join(
            os.environ.get("TEMP", "/tmp"), f"mba_result_{uuid.uuid4().hex}.xlsx"
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
            semester=self.semester,
            exam_name=self.exam_name
        )

        builder.build()

        wb.save(temp_excel)

        return convert_excel_to_pdf(temp_excel)