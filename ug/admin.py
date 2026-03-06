from django.contrib import admin
from django.http import HttpResponse
import openpyxl
from django.db.models import Exists, OuterRef
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field
from ug.services.semester_registration_service import SemesterRegistrationService
from .models import (
    UGFaculty, UGDepartment, UGDegree, UGProgram, UGBatch, UGStudentProfile,
    CourseStructure, StudentCourseAssessment, SemesterRegistration, ExamRegistration,
    CommonCourseStructure, UGExamResult
)


@admin.register(UGFaculty)
class UGFacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'university', 'is_publish', 'created_at')
    list_editable = ('is_publish',)
    list_filter = ('university', 'is_publish')
    search_fields = ('name', 'short_name')
    ordering = ('name',)


@admin.register(UGDepartment)
class UGDepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head_of_department', 'is_publish', 'created_at')
    list_editable = ('is_publish',)
    list_filter = ('is_publish',)
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(UGDegree)
class UGDegreeAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'total_semesters', 'total_years', 'created_at')
    search_fields = ('name', 'short_name')
    ordering = ('name',)


@admin.register(UGProgram)
class UGProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'degree', 'department', 'created_at')
    list_filter = ('degree',)
    search_fields = ('name', 'short_name', 'degree__name', 'department__name')
    ordering = ('name',)


@admin.register(UGBatch)
class UGBatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'program', 'created_at')
    list_filter = ('program',)
    search_fields = ('name', 'program__name')
    ordering = ('name',)


@admin.register(UGStudentProfile)
class UGStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'first_name', 'last_name', 'roll_no', 'college', 
                   'major_course','minor_course','mdc_course','department', 'program', 'current_semester', 'status', 'is_active', 'batch')
    list_filter = ('status', 'gender', 'college', 'department', 'program', 'degree', 
                  'current_semester', 'batch')
    search_fields = ('registration_no', 'roll_no', 'first_name', 'last_name', 
                    'mobile_no', 'aadhar_no')
    readonly_fields = ('uid', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    # Performance optimizations for large datasets
    list_select_related = ('college', 'department', 'program', 'degree', 'batch')
    show_full_result_count = False
    list_per_page = 50
    raw_id_fields = ('user', 'college', 'department', 'program', 'degree', 'batch','major_course', 'minor_course', "mdc_course")
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('uid', 'user', 'first_name', 'last_name', 'hindi_name',
                      'date_of_birth', 'gender', 'caste', 'mobile_no', 'aadhar_no', 'address')
        }),
        ('Academic Information', {
            'fields': ('registration_no', 'roll_no', 'college', 'department', 
                      'program', 'degree', 'current_semester', 'session', 'batch', 'status', 'is_active')
        }),
        ('Admission Details', {
            'fields': ('admission_date', 'enrollment_date', 'migration_submitted', 'last_university')
        }),
        ('Course Selections (CBCS)', {
            'fields': ('major_course', 'minor_course', 'mdc_course')
        }),
        ('Family Information', {
            'fields': ('father_name', 'mother_name')
        }),
        ('Documents', {
            'fields': ('profile_image', 'signature'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('json_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(CourseStructure)
class CourseStructureAdmin(admin.ModelAdmin):
    list_display = ('id','course_name','label', 'department', 'course_type', 'course_code', 'paper_code', 'semester', 'max_marks','min_marks', 'max_credit')
    list_editable = ('course_name','label', 'department', 'course_type', 'course_code', 'paper_code', 'semester', 'max_marks','min_marks', 'max_credit')
    list_filter = ('course_type', 'semester', 'course_code', 'department', )
    search_fields = ('course_name', 'course_short_name', 'course_code', 'department__name')
    ordering = ('department', 'semester', 'course_code')
    raw_id_fields = ('department',)



class StudentCourseAssessmentResource(resources.ModelResource):
    student_registration_no = resources.Field(attribute='student__registration_no', column_name='Registration No')
    student_roll_no = resources.Field(attribute='student__roll_no', column_name='Roll No')
    student_name = resources.Field(attribute='student__first_name', column_name='Student Name')
    student_batch = resources.Field(attribute='student__batch', column_name='Batch')
    paper_department = resources.Field(attribute='department__name', column_name='Paper Department')
    semester_result = resources.Field(column_name='Semester Result')
    
    class Meta:
        model = StudentCourseAssessment
        fields = ('student_registration_no', 'student_roll_no', 'student_name', 'student_batch', 'semester', 'session', 'semester_result',
                 'course_name', 'course_code', 'paper_department', 'course_type', 'label', 
                 'ind_pass_marks', 'ind_marks_obtained', 'ind_max_marks', 'ind_is_pass', 'ind_is_absent')
        export_order = ('student_registration_no', 'student_roll_no', 'student_name', 'student_batch', 'semester', 'session', 'semester_result',
                       'course_name', 'course_code', 'paper_department', 'course_type', 'label', 
                       'ind_marks_obtained', 'ind_pass_marks', 'ind_is_pass')

    def dehydrate_semester_result(self, assessment):
        from .models import UGExamResult
        # Attempt direct match
        res = UGExamResult.objects.filter(
            student_id=assessment.student_id,
            semester=assessment.semester,
            session=assessment.session
        ).first()
        
        # If not found, try robust semester check (e.g. '3' vs '3RD')
        if not res and assessment.semester.isdigit():
             pass # Logic matching service mapping if needed, simplified for speed
             
        return res.semester_result if res else ''


class ExamResultFilter(admin.SimpleListFilter):
    title = 'Semester Result (from ExamResult)'
    parameter_name = 'sem_result'

    def lookups(self, request, model_admin):
        return [
            ('PROMOTED', 'Promoted'),
            ('PASSED', 'Passed'),
            ('FAILED', 'Failed')
        ]

    def queryset(self, request, queryset):
        if self.value():
            results = UGExamResult.objects.filter(
                student=OuterRef('student'),
                semester=OuterRef('semester'),
                semester_result=self.value()
            )
            return queryset.filter(Exists(results))
        return queryset


@admin.register(StudentCourseAssessment)
class StudentCourseAssessmentAdmin(ImportExportModelAdmin):
    resource_class = StudentCourseAssessmentResource
    # Display all marks and calculation fields directly from database
    # Display all marks and calculation fields directly from database
    list_display = (
        'id', 'student', 'semester', 'paper_code', 'label',
        # Individual
        'ind_max_marks', 'ind_pass_marks', 'ind_is_absent', 'ind_marks_obtained', 
        'ind_grace_obtained', 'ind_final_marks_obtained', 'ind_is_pass',
        # Combined
        'comb_max_marks', 'comb_max_credits', 'comb_pass_marks', 'comb_marks_obtained',
        'comb_grace_obtained', 'comb_final_marks_obtained', 'comb_credit_obtained',
        'comb_numeric_grade', 'comb_letter_grade', 'comb_grade_point',
        # Course
        'course_max_marks', 'course_max_credits', 'course_pass_marks', 'course_marks_obtained',
        'course_grace_obtained', 'course_final_marks_obtained', 'course_credit_obtained', 'course_grade_point',
        # Semester
        'sem_max_credit', 'sem_credit_obtained', 'sgpa', 'sem_result', 'next_sem_status', 'sem_grace_obtained'
    )
    
    # Filters for easy navigation
    list_filter = ('session','semester', 'label','batch', 'course_type', 'ind_is_absent', 'ind_is_pass', ExamResultFilter)
    
    # Search by student registration number AND name
    search_fields = ('student__registration_no', 'student__first_name', 'student__last_name', 
                     'paper_code', 'course_code')
    
    # Order by ID for performance (indexed)
    ordering = ('-id',)
    
    # Performance optimizations for 2M+ records
    list_select_related = ('student',)  # Reduce DB queries
    show_full_result_count = False  # Skip COUNT query
    list_per_page = 50
    
    # Fast FK lookups in forms
    raw_id_fields = ('student', 'department', 'batch')
    
    # Disable bulk actions for speed
    actions = None
    
    def has_add_permission(self, request):
        # Disable add in admin (use migration scripts instead)
        return False
    
    def get_queryset(self, request):
        """Optimize queryset - limit to recent records by default"""
        qs = super().get_queryset(request)
        
        # If no filters applied, only show records from last 100k IDs
        # This approach works with .distinct() unlike slicing
        if not request.GET or request.GET.get('all'):
            from django.db.models import Max
            max_id = StudentCourseAssessment.objects.aggregate(Max('id'))['id__max']
            if max_id:
                # Only show last 100k records by ID range
                min_id = max(1, max_id - 100000)
                qs = qs.filter(id__gte=min_id)
        
        return qs
    
    # Organized fieldsets for detail view
    fieldsets = (
        ('Basic Information', {
            'fields': ('student', 'semester', 'paper_code', 'course_code', 'course_type', 'label')
        }),
        ('Individual Assessment (CIA/ESE)', {
            'fields': (
                'ind_max_marks',
                'ind_pass_marks', 
                'ind_marks_obtained',
                'ind_grace_obtained',
                'ind_final_marks_obtained',
                'ind_is_absent',
                'ind_is_pass'
            ),
            'description': 'Individual component marks (CIA or ESE separately)'
        }),
        ('Combined Assessment (Theory + Practical)', {
            'fields': (
                'comb_max_marks',
                'comb_pass_marks',
                'comb_marks_obtained',
                'comb_grace_obtained',
                'comb_final_marks_obtained',
                'comb_max_credits',
                'comb_credit_obtained',
                'comb_numeric_grade',
                'comb_grade_point'
            ),
            'description': 'Combined CIA + ESE marks and calculated credits/grades'
        }),
        ('Course Level Summary', {
            'fields': (
                'course_max_credits',
                'course_credit_obtained',
                'course_grade_point'
            ),
            'classes': ('collapse',),
            'description': 'Overall course-level aggregated values'
        }),
        ('Semester Level Summary', {
            'fields': (
                'sem_max_credit',
                'sem_credit_obtained',
                'sem_result'
            ),
            'classes': ('collapse',),
            'description': 'Semester-level aggregated values'
        }),
        ('Additional Information', {
            'fields': ('college_code', 'exam_type', 'department', 'batch'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SemesterRegistration)
class SemesterRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'batch', 'sem', 'status', 'exam_eligible', 'is_open', 'start_date', 'end_date', 'session')
    list_filter = ('batch', 'sem', 'status', 'exam_eligible', 'is_open')
    search_fields = ('student__registration_no', 'student__first_name', 'batch__name')
    ordering = ('-sem', 'student')
    list_per_page = 50
    raw_id_fields = ('student', 'batch')
    list_select_related = ('student', 'batch')
    show_full_result_count = False
    list_editable = ('status', 'exam_eligible')


@admin.register(ExamRegistration)
class ExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'status', 'fees', 'is_open')
    list_filter = ('sem', 'status', 'is_open')
    search_fields = ('student__registration_no', 'student__first_name')
    ordering = ('student', 'sem')

@admin.register(CommonCourseStructure)
class CommonCourseStructureAdmin(admin.ModelAdmin):
    list_display = ('id','semester', 'course_type','code', 'course_name', 'ltp', 'credit', 'marks')

    list_filter = ('semester', 'course_type')
    search_fields = ('semester', 'course_name', 'course_type')
    ordering = ('semester', 'course_type')
    list_editable = ('semester', 'course_type','code', 'course_name', 'ltp', 'credit', 'marks')



class UGExamResultResource(resources.ModelResource):
    registration_no = resources.Field(attribute='student__registration_no', column_name='Registration No')
    student_name = resources.Field(attribute='student__first_name', column_name='Student Name')
    student_batch = resources.Field(attribute='student__batch', column_name='Batch')
    failed_ese_papers = resources.Field(column_name='Failed ESE Papers')
    
    class Meta:
        model = UGExamResult
        fields = ('id', 'registration_no', 'student_name', 'student_batch', 'semester', 'session', 
                 'sgpa', 'semester_result', 'semester_credit_earned', 'semester_max_credit', 
                 'cia_pass', 'ese_pass', 'next_sem_status', 'is_legacy', 'failed_ese_papers')
        export_order = ('id', 'registration_no', 'student_name', 'student_batch', 'semester', 'session', 'semester_result', 'sgpa', 'failed_ese_papers')

    def dehydrate_failed_ese_papers(self, exam_result):
        # Fetch ESE failures for this specific semester result
        failures = StudentCourseAssessment.objects.filter(
            student=exam_result.student,
            # Match semester by text (e.g. '3RD') from exam_result
            semester=exam_result.semester,
            session=exam_result.session,
            label__icontains='ESE',
            ind_is_pass=False
        )
        return ", ".join([a.paper_code for a in failures])


@admin.register(UGExamResult)
class UGExamResultAdmin(ImportExportModelAdmin):
    resource_class = UGExamResultResource
    list_display = ('get_student_name', 'get_registration_no', 'semester', 'session', 
                    'sgpa', 'semester_result', 'semester_credit_earned', 'semester_max_credit', 'cia_pass', 'ese_pass')
    list_filter = ('semester', 'student__batch', 'semester_result','cia_pass', 'ese_pass', 'next_sem_status', 'session', 'is_legacy', 'created_at')
    search_fields = ('student__registration_no', 'student__first_name', 'student__last_name', 'semester')
    ordering = ('-created_at', 'student__registration_no')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('student',)
    # Performance optimizations
    list_select_related = ('student',)
    show_full_result_count = False
    list_per_page = 50
    
    actions = ['export_failed_subjects_xls']

    @admin.action(description='Export Failed ESE Details (XLSX)')
    def export_failed_subjects_xls(self, request, queryset):
        """
        Export failed ESE subjects for selected students in XLSX format.
        Useful for identifying backlog subjects for PROMOTED students.
        """
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename=failed_ese_details.xlsx'
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Failed ESE Details"
        
        # Define headers
        headers = [
            'Registration No', 'Student Name', 'Department', 'Batch', 'Semester', 'Session', 
            'Result Status', 'Course Code', 'Paper Code', 'Course Name', 
            'Course Type', 'Label', 'Pass Marks', 'Marks Obtained', 'Is Absent'
        ]
        ws.append(headers)
        
        # Filter for PROMOTED records only
        queryset = queryset.filter(semester_result='PROMOTED')
        
        if not queryset.exists():
            wb.save(response)
            return response

        # Get relevant filters
        student_ids = queryset.values_list('student_id', flat=True)
        semesters = set(queryset.values_list('semester', flat=True))
        
        # Expand semesters to handle "3" vs "3RD" mismatch
        expanded_semesters = set()
        for sem in semesters:
            expanded_semesters.add(sem)
            expanded_semesters.add(str(SemesterRegistrationService.SEMESTER_MAP.get(sem, sem)))

        # Query Assessments directly (Paper-wise optimization)
        failures = StudentCourseAssessment.objects.filter(
            student_id__in=student_ids,
            semester__in=expanded_semesters,
            label__icontains='ESE',
            ind_is_pass=False
        ).select_related('student', 'department').order_by('paper_code', 'student__registration_no')
        
        # Fallback if label filter is too strict
        if not failures.exists():
             failures = StudentCourseAssessment.objects.filter(
                student_id__in=student_ids,
                semester__in=expanded_semesters,
                ind_is_pass=False
            ).exclude(label__icontains='CIA').select_related('student', 'department').order_by('paper_code', 'student__registration_no')

        for fail in failures:
            # Need to find the corresponding result for this student/semester to get semester_result (always PROMOTED here)
            # Since we know we filtered for PROMOTED, we can hardcode or just assume.
            # But wait, result status is in UGExamResult.
            # We can skip fetching UGExamResult for every row since we know they are promoted.
            # Or we can just put "PROMOTED" since we filtered for it.
            
            row = [
                str(fail.student.registration_no),
                f"{fail.student.first_name} {fail.student.last_name}",
                fail.department.name if fail.department else '',
                str(fail.student.batch) if fail.student.batch else '',
                fail.semester,
                fail.session,
                "PROMOTED", # We filtered for this
                fail.course_code,
                fail.paper_code,
                fail.course_name,
                fail.course_type,
                fail.label,
                fail.ind_pass_marks,
                fail.ind_marks_obtained,
                "Yes" if fail.ind_is_absent else "No"
            ]
            ws.append(row)
                
        wb.save(response)
        return response
    
    # Custom display methods
    @admin.display(description='Student Name', ordering='student__first_name')
    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"
    
    @admin.display(description='Registration No', ordering='student__registration_no')
    def get_registration_no(self, obj):
        return obj.student.registration_no
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student', 'semester', 'session')
        }),
        ('Assessment Status', {
            'fields': ('cia_pass', 'ese_pass')
        }),
        ('Credits', {
            'fields': ('semester_max_credit', 'semester_credit_earned')
        }),
        ('Results', {
            'fields': ('sgpa', 'semester_result')
        }),
        ('Promotion', {
            'fields': ('next_semester', 'next_sem_status'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_legacy', 'published_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('student')


