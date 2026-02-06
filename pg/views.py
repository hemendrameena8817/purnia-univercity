from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import PGStudentCourseAssessment
from .serializers import PGStudentCourseAssessmentSerializer

class PGCIAMarksEntryView(APIView):
    """
    API View for Bulk CIA Marks Entry.
    Accepts a list of assessment updates.
    
    Request Body:
    [
        {"id": 123, "ind_marks_obtained": 25, "ind_is_absent": false},
        {"id": 124, "ind_marks_obtained": 0, "ind_is_absent": true}
    ]
    """
    permission_classes = [] # Allow unauthenticated access for testing/internal use
    
    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "Expected a list of updates."}, status=status.HTTP_400_BAD_REQUEST)
        
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            for item in data:
                assess_id = item.get('id')
                if not assess_id:
                    errors.append({"error": "Missing 'id' field", "item": item})
                    continue
                
                try:
                    assessment = PGStudentCourseAssessment.objects.select_for_update().get(id=assess_id)
                except PGStudentCourseAssessment.DoesNotExist:
                    errors.append({"error": f"Assessment with id {assess_id} not found."})
                    continue
                
                serializer = PGStudentCourseAssessmentSerializer(assessment, data=item, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    updated_count += 1
                else:
                    errors.append({"id": assess_id, "errors": serializer.errors})
        
        response_data = {
            "message": f"Successfully updated {updated_count} records.",
            "errors": errors
        }
        
        if errors:
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
            
        return Response(response_data, status=status.HTTP_200_OK)
