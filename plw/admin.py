from django.contrib import admin
from .models import (
    PLWCourse, PLWSession, PLWBatch, PLWStudentProfile, 
    PLWSubject, PLWExam, PLWResult, PLWResultDetail
)

@admin.register(PLWCourse)
class PLWCourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_years')
    search_fields = ('name',)

@admin.register(PLWSession)
class PLWSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_year', 'end_year', 'is_active')
    list_filter = ('is_active',)

@admin.register(PLWBatch)
class PLWBatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'session', 'admission_year', 'is_active')
    list_filter = ('session', 'is_active')

@admin.register(PLWStudentProfile)
class PLWStudentProfileAdmin(admin.ModelAdmin):
    list_display = ('roll_no', 'registration_no', 'user', 'college', 'course', 'batch')
    search_fields = ('roll_no', 'registration_no', 'user__first_name', 'user__last_name')
    list_filter = ('college', 'course', 'batch')

@admin.register(PLWSubject)
class PLWSubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'paper_code', 'full_marks', 'pass_marks')
    search_fields = ('name', 'paper_code')

@admin.register(PLWExam)
class PLWExamAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'session', 'exam_month_year', 'publication_date')
    search_fields = ('name', 'session')

class PLWResultDetailInline(admin.TabularInline):
    model = PLWResultDetail
    extra = 1

@admin.register(PLWResult)
class PLWResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'total_marks', 'result_status', 'exam_center')
    list_filter = ('exam', 'result_status')
    search_fields = ('student__roll_no', 'student__user__first_name', 'student__user__last_name')
    inlines = [PLWResultDetailInline]

@admin.register(PLWResultDetail)
class PLWResultDetailAdmin(admin.ModelAdmin):
    list_display = ('result', 'subject', 'marks_obtained')
    list_filter = ('subject',)
