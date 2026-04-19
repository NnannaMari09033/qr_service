from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema
from .serializers import UserSerializer, RegisterSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="Register a new user", request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Get your profile", responses={200: UserSerializer})
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(summary="Update your profile", request=UserSerializer, responses={200: UserSerializer})
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Delete your account", responses={204: None})
    def delete(self, request):
        request.user.delete()
        return Response(
            {'message': 'Account deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )