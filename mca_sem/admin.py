from django.contrib import admin
from .models import (
    MCACourse, MCASession, MCABatch, MCAStudentProfile, 
    MCASubject, MCAExam, MCAResult, MCAResultDetail
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
    list_display = ('name', 'paper_code', 'full_marks', 'pass_marks')
    search_fields = ('name', 'paper_code')

@admin.register(MCAExam)
class MCAExamAdmin(admin.ModelAdmin):
    list_display = ('uid', 'name', 'session', 'exam_month_year', 'publication_date')
    search_fields = ('name', 'session')

class MCAResultDetailInline(admin.TabularInline):
    model = MCAResultDetail
    extra = 1

@admin.register(MCAResult)
class MCAResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'total_marks', 'result_status', 'exam_center')
    list_filter = ('exam', 'result_status')
    search_fields = ('student__roll_no', 'student__user__first_name', 'student__user__last_name')
    inlines = [MCAResultDetailInline]

@admin.register(MCAResultDetail)
class MCAResultDetailAdmin(admin.ModelAdmin):
    list_display = ('result', 'subject', 'marks_obtained')
    list_filter = ('subject',)
