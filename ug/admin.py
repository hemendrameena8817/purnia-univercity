from django.contrib import admin
from .models import CourseStructure, StudentCourseAssessment, SemesterRegistration, ExamRegistration


@admin.register(CourseStructure)
class CourseStructureAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'course_type', 'code', 'semester', 'max_marks', 'max_credit')
    list_filter = ('department', 'course_type', 'semester')
    search_fields = ('name', 'code', 'department__name')
    ordering = ('department', 'semester', 'code')


@admin.register(StudentCourseAssessment)
class StudentCourseAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'code', 'semester', 'label', 'marks_obtained', 'grade', 'exam_result')
    list_filter = ('semester', 'exam_type', 'exam_result', 'is_absent')
    search_fields = ('student__registration_no', 'student__first_name', 'code')
    ordering = ('student', 'semester', 'code')


@admin.register(SemesterRegistration)
class SemesterRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'status', 'exam_eligible', 'is_open')
    list_filter = ('sem', 'status', 'exam_eligible', 'is_open')
    search_fields = ('student__registration_no', 'student__first_name')
    ordering = ('student', 'sem')


@admin.register(ExamRegistration)
class ExamRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sem', 'status', 'fees', 'is_open')
    list_filter = ('sem', 'status', 'is_open')
    search_fields = ('student__registration_no', 'student__first_name')
    ordering = ('student', 'sem')
