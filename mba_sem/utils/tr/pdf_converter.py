# mba_sem/utils/tr/pdf_converter.py

import subprocess
import os


def convert_excel_to_pdf(temp_excel_path):

    subprocess.run([
        "soffice",
        "--headless",
        "--convert-to", "pdf:calc_pdf_Export",
        "--outdir", "/tmp",
        temp_excel_path
    ])

    pdf_path = temp_excel_path.replace(".xlsx", ".pdf")

    if not os.path.exists(pdf_path):
        return None

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    os.remove(temp_excel_path)
    os.remove(pdf_path)

    return pdf_bytes