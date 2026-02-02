from django.contrib import admin
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCASubject, MCAExam, MCAExamSchedule, MCAStudentAssessment, 
    MCASemesterResult, MCASemesterRegistration, MCAExamRegistration
)

@admin.register(MCACourse)
class MCACourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_years')
    search_fields = ('name',)

@admin.register(MCASession)
class MCASessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_year', 'end_year', 'is_active')
    list_filter = ('is_active',)

@admin.register(MCABatch)
class MCABatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'session', 'admission_year', 'is_active')
    list_filter = ('session', 'is_active')

@admin.register(MCAStudentProfile)
class MCAStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('roll_no', 'registration_no', 'user', 'college', 'course', 'batch')
    search_fields = ('roll_no', 'registration_no', 'user__username', 'user__first_name', 'user__last_name')
    list_filter = ('college', 'course', 'batch')

@admin.register(MCASubject)
class MCASubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject_code', 'paper_code', 'semester', 'full_marks', 'pass_marks', 'credit')
    search_fields = ('name', 'subject_code', 'paper_code')
    list_filter = ('semester',)

@admin.register(MCAExam)
class MCAExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'session', 'exam_month_year', 'publication_date')
    search_fields = ('name', 'session')

@admin.register(MCAExamSchedule)
class MCAExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('exam', 'subject', 'exam_date', 'exam_time', 'sitting')
    list_filter = ('exam', 'exam_date', 'sitting')
    search_fields = ('subject__name', 'subject__paper_code')

@admin.register(MCAStudentAssessment)
class MCAStudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'semester', 'label', 'ind_marks_obtained', 'ind_is_pass')
    list_filter = ('semester', 'label', 'exam_type', 'batch')
    search_fields = ('student__roll_no', 'subject__name', 'subject__paper_code')

@admin.register(MCASemesterResult)
class MCASemesterResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'session', 'semester_result', 'sgpa')
    list_filter = ('semester', 'session', 'semester_result')
    search_fields = ('student__roll_no',)

@admin.register(MCASemesterRegistration)
class MCASemesterRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'session', 'status', 'exam_eligible')
    list_filter = ('sem', 'session', 'status', 'exam_eligible')

@admin.register(MCAExamRegistration)
class MCAExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'session', 'status', 'is_open')
    list_filter = ('sem', 'session', 'status', 'is_open')
