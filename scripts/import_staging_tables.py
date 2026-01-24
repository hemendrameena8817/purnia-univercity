"""
Import scripts for staging tables.
Run each import function from Django shell.
"""
import csv
import os

def clean_value(value):
    if value in ('\\N', '', 'NULL', 'null', None):
        return None
    return str(value).strip() if value else None


def import_subject_master():
    from staging.models import SubjectMaster
    CSV_PATH = 'old_data/subject_master.csv'
    
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found")
        return
    
    existing = SubjectMaster.objects.count()
    print(f"Existing records: {existing}")
    
    imported = 0
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            SubjectMaster.objects.create(
                csv_id=clean_value(row.get('id')),
                subject_code=clean_value(row.get('subject_code')),
                subject_name=clean_value(row.get('subject_name')),
                syllabus_code=clean_value(row.get('syllabus_code')),
                semester_code=clean_value(row.get('semester_code')),
                mdc_subject_name=clean_value(row.get('mdc_subject_name')),
                institute_code=clean_value(row.get('institute_code')),
                created_by=clean_value(row.get('created_by')),
                created_on=clean_value(row.get('created_on')),
                updated_by=clean_value(row.get('updated_by')),
                updated_on=clean_value(row.get('updated_on')),
                record_status=clean_value(row.get('record_status')),
                last_updated=clean_value(row.get('last_updated')),
            )
            imported += 1
            if imported % 500 == 0:
                print(f"Imported {imported} records...")
    
    print(f"✅ SubjectMaster: Imported {imported} records. Total: {SubjectMaster.objects.count()}")


def import_paper_subject_mapping():
    from staging.models import PaperSubjectMapping
    CSV_PATH = 'old_data/paper_subject_mapping.csv'
    
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found")
        return
    
    existing = PaperSubjectMapping.objects.count()
    print(f"Existing records: {existing}")
    
    imported = 0
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            PaperSubjectMapping.objects.create(
                csv_id=clean_value(row.get('id')),
                scdsp_code=clean_value(row.get('scdsp_code')),
                paper_code=clean_value(row.get('paper_code')),
                subject_code=clean_value(row.get('subject_code')),
                discipline_code=clean_value(row.get('discipline_code')),
                institute_code=clean_value(row.get('institute_code')),
                status=clean_value(row.get('status')),
                created_by=clean_value(row.get('created_by')),
                created_on=clean_value(row.get('created_on')),
                updated_by=clean_value(row.get('updated_by')),
                updated_on=clean_value(row.get('updated_on')),
                record_status=clean_value(row.get('record_status')),
                last_updated=clean_value(row.get('last_updated')),
            )
            imported += 1
            if imported % 1000 == 0:
                print(f"Imported {imported} records...")
    
    print(f"✅ PaperSubjectMapping: Imported {imported} records. Total: {PaperSubjectMapping.objects.count()}")


def import_discipline_master():
    from staging.models import DisciplineMaster
    CSV_PATH = 'old_data/discipline_master.csv'
    
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found")
        return
    
    existing = DisciplineMaster.objects.count()
    print(f"Existing records: {existing}")
    
    imported = 0
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            DisciplineMaster.objects.create(
                csv_id=clean_value(row.get('id')),
                discipline_code=clean_value(row.get('discipline_code')),
                discipline=clean_value(row.get('discipline')),
                discipline_name=clean_value(row.get('discipline_name')),
                discipline_name_new=clean_value(row.get('discipline_name_new')),
                subject_name=clean_value(row.get('subject_name')),
                institute_code=clean_value(row.get('institute_code')),
                created_by=clean_value(row.get('created_by')),
                created_on=clean_value(row.get('created_on')),
                updated_by=clean_value(row.get('updated_by')),
                updated_on=clean_value(row.get('updated_on')),
                record_status=clean_value(row.get('record_status')),
                last_updated=clean_value(row.get('last_updated')),
                discipline_name_hindi=clean_value(row.get('discipline_name_hindi')),
            )
            imported += 1
    
    print(f"✅ DisciplineMaster: Imported {imported} records. Total: {DisciplineMaster.objects.count()}")


def import_course_discipline_sem_paper_mapping():
    from staging.models import CourseDisciplineSemPaperMapping
    CSV_PATH = 'old_data/course_discipline_sem_paper_mapping.csv'
    
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found")
        return
    
    existing = CourseDisciplineSemPaperMapping.objects.count()
    print(f"Existing records: {existing}")
    
    imported = 0
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            CourseDisciplineSemPaperMapping.objects.create(
                csv_id=clean_value(row.get('id')),
                scdsp_code=clean_value(row.get('scdsp_code')),
                syllabus_code=clean_value(row.get('syllabus_code')),
                course_code=clean_value(row.get('course_code')),
                discipline_code=clean_value(row.get('discipline_code')),
                semester_code=clean_value(row.get('semester_code')),
                paper_code=clean_value(row.get('paper_code')),
                paper_type=clean_value(row.get('paper_type')),
                subject_type=clean_value(row.get('subject_type')),
                paper_ge=clean_value(row.get('paper_ge')),
                paper_credit=clean_value(row.get('paper_credit')),
                institute_code=clean_value(row.get('institute_code')),
                created_by=clean_value(row.get('created_by')),
                created_on=clean_value(row.get('created_on')),
                updated_by=clean_value(row.get('updated_by')),
                update_on=clean_value(row.get('update_on')),
                record_status=clean_value(row.get('record_status')),
                last_updated=clean_value(row.get('last_updated')),
            )
            imported += 1
            if imported % 500 == 0:
                print(f"Imported {imported} records...")
    
    print(f"✅ CourseDisciplineSemPaperMapping: Imported {imported} records. Total: {CourseDisciplineSemPaperMapping.objects.count()}")


def import_registered_applicant_master():
    from staging.models import RegisteredApplicantMaster
    CSV_PATH = 'old_data/registered_applicant_master.csv'
    
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found")
        return
    
    existing = RegisteredApplicantMaster.objects.count()
    print(f"Existing records: {existing}")
    
    imported = 0
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            RegisteredApplicantMaster.objects.create(
                csv_id=clean_value(row.get('id')),
                reg_no=clean_value(row.get('reg_no')),
                sams_id=clean_value(row.get('sams_id')),
                college_roll_no=clean_value(row.get('college_roll_no')),
                college_reg_no=clean_value(row.get('college_reg_no')),
                center=clean_value(row.get('center')),
                center2017_old=clean_value(row.get('3rdcenter2017_old')),
                center2017=clean_value(row.get('3rdcenter2017')),
                roll_no=clean_value(row.get('roll_no')),
                result=clean_value(row.get('result')),
                exam_type_code=clean_value(row.get('exam_type_code')),
                student_name=clean_value(row.get('student_name')),
                fathers_name=clean_value(row.get('fathers_name')),
                mothers_name=clean_value(row.get('mothers_name')),
                appl_no=clean_value(row.get('appl_no')),
                course_code=clean_value(row.get('course_code')),
                discipline_code=clean_value(row.get('discipline_code')),
                semester_code=clean_value(row.get('semester_code')),
                batch_code=clean_value(row.get('batch_code')),
                syllabus_year=clean_value(row.get('syllabus_year')),
                institute_code=clean_value(row.get('institute_code')),
                session_code=clean_value(row.get('session_code')),
                phone=clean_value(row.get('phone')),
                dob=clean_value(row.get('dob')),
                gender=clean_value(row.get('gender')),
                category=clean_value(row.get('category')),
                approve=clean_value(row.get('Approve')),
                full_address=clean_value(row.get('full_address')),
                institute_pub_status=clean_value(row.get('institute_pub_status')),
                student_pub_status=clean_value(row.get('student_pub_status')),
                last_board=clean_value(row.get('last_board')),
                aadhar_card_no=clean_value(row.get('aadhar_card_no')),
                created_by=clean_value(row.get('created_by')),
                created_on=clean_value(row.get('created_on')),
                updated_by=clean_value(row.get('updated_by')),
                updated_on=clean_value(row.get('updated_on')),
                record_status=clean_value(row.get('record_status')),
                last_updated=clean_value(row.get('last_updated')),
                payment_status=clean_value(row.get('payment_status')),
                is_sem=clean_value(row.get('is_sem')),
                abc_id=clean_value(row.get('ABC_Id')),
                addmision_date=clean_value(row.get('Addmision_date')),
                api_status=clean_value(row.get('api_status')),
            )
            imported += 1
            if imported % 5000 == 0:
                print(f"Imported {imported} records...")
    
    print(f"✅ RegisteredApplicantMaster: Imported {imported} records. Total: {RegisteredApplicantMaster.objects.count()}")


def import_all():
    """Import all 4 tables"""
    print("=" * 60)
    print("Importing SubjectMaster...")
    import_subject_master()
    
    print("\n" + "=" * 60)
    print("Importing PaperSubjectMapping...")
    import_paper_subject_mapping()
    
    print("\n" + "=" * 60)
    print("Importing DisciplineMaster...")
    import_discipline_master()
    
    print("\n" + "=" * 60)
    print("Importing CourseDisciplineSemPaperMapping...")
    import_course_discipline_sem_paper_mapping()
    
    print("\n" + "=" * 60)
    print("✅ All imports completed!")

