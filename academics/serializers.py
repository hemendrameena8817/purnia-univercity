from rest_framework import serializers
from .models import Batch, Course

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['uid', 'name', 'start_year', 'end_year', 'is_active']

class CourseSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = Course
        fields = ['uid', 'name', 'code', 'description', 'department_name', 'is_elective', 'is_active']
