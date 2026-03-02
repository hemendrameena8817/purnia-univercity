# mba_sem/utils/tr/pdf_converter.py

import subprocess
import os


def convert_excel_to_pdf(temp_excel_path):

    soffice = os.path.join(os.environ.get("ProgramFiles",""), "LibreOffice","program","soffice.exe") if os.name=="nt" else "soffice"
    subprocess.run([
        soffice,
        "--headless",
        "--convert-to", "pdf:calc_pdf_Export",
        "--outdir", os.environ.get("TEMP", "/tmp"),
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