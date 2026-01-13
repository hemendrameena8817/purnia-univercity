from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import UserAccount

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = UserAccount
        fields = ['email', 'username', 'password', 'first_name', 'last_name']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = UserAccount.objects.create_user(**validated_data, password=password)
        return user


from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()   # can be email or username
    password = serializers.CharField()

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')

        user = None

        # Check if identifier is email
        if '@' in identifier:
            user = User.objects.filter(email=identifier).first()
        else:
            user = User.objects.filter(username=identifier).first()

        if user is None:
            raise serializers.ValidationError("Invalid username/email")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid password")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")

        data['user'] = user
        return data
