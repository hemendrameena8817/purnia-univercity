from rest_framework import serializers
from .models import UGSemResultCurrent

class UGSemResultUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer to update UGSemResultCurrent entries.
    Allows bulk updates by ID.
    """
    id = serializers.IntegerField(required=True)

    class Meta:
        model = UGSemResultCurrent
        fields = [
            'id', 
            'semester_code', 
            'college_roll_no', 
            'college_reg_no', 
            'paper_code', 
            'subject_code', 
            'subject_name',
            'mark_secured', 
            'maximum_mark',
            'pass_mark',
            'subject_total_mark',
            'grand_total_mark',
            'total_secured_mark', 
            'final_result',
            'is_migrated',
            'status',
            'exam_type'
        ]
        read_only_fields = ['uid', 'imported_at']

