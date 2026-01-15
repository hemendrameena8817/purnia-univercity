from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .serializers import StudentCreateSerializer


class StudentCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StudentCreateSerializer(data=request.data)

        if serializer.is_valid():
            student = serializer.save()

            return Response({
                "success": True,
                "message": "Student created successfully",
                "data": {
                    "id": student.id,
                    "uid": student.uid,
                    "email": student.user.email,
                    "username": student.user.username,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "enrollment_no": student.enrollment_no,
                    "roll_no": student.roll_no,
                    "college": student.college.name,
                    "status": student.status,
                    "created_at": student.created_at
                }
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
