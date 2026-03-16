from rest_framework import serializers
from django.db import transaction
from django.contrib.auth.hashers import make_password
from .models import Domain, InviteCode, Role, UserProfile, UserRole, OperationLog


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, min_length=6)
    confirm = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    # 前端传 company 和 job，我们在这接收
    company = serializers.CharField(max_length=100)
    job = serializers.CharField(max_length=100, required=False, allow_blank=True)
    domain = serializers.CharField()
    inviteCode = serializers.CharField()
    role = serializers.CharField(required=False, default='ordinary_user')

    def validate_confirm(self, value):
        if value != self.initial_data.get('password'):
            raise serializers.ValidationError("两次输入的密码不一致")
        return value

    def validate_username(self, value):
        if UserProfile.objects.filter(user_name=value).exists():
            raise serializers.ValidationError("该用户名已被注册，请尝试其他名称")
        return value

    def validate_inviteCode(self, value):
        try:
            invite = InviteCode.objects.get(code=value)
            if invite.is_used:
                raise serializers.ValidationError("该邀请码已被使用")
            self.invite_obj = invite
        except InviteCode.DoesNotExist:
            raise serializers.ValidationError("无效的邀请码")
        return value

    def validate_domain(self, value):
        try:
            domain_obj = Domain.objects.get(name=value)
            self.domain_obj = domain_obj
        except Domain.DoesNotExist:
            raise serializers.ValidationError("无效的所属领域")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            # 1. 手动生成密码哈希
            hashed_password = make_password(validated_data['password'])

            # 2. 直接写入自定义用户表 (严格映射数据库字段)
            user = UserProfile.objects.create(
                user_name=validated_data['username'],
                password_hash=hashed_password,
                email=validated_data['email'],
                phone=validated_data['phone'],
                organization=validated_data['company'],  # 映射公司到 organization
                position=validated_data.get('job', ''),  # 映射职务到 position
                domain=self.domain_obj
            )

            # 3. 分配角色
            role_name = validated_data.get('role', 'ordinary_user')
            role_obj, _ = Role.objects.get_or_create(name=role_name)
            UserRole.objects.create(user=user, role=role_obj)

            # 4. 更新邀请码状态 (只更新 is_used，不记录 used_by)
            self.invite_obj.is_used = True
            self.invite_obj.save()

            # 5. 记录操作日志 (只记录 action)
            OperationLog.objects.create(
                user=user,
                action='注册'
            )

            return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class AdminCreateUserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    company = serializers.CharField(max_length=100, required=False, allow_blank=True)
    job = serializers.CharField(max_length=100, required=False, allow_blank=True)
    domain = serializers.CharField()
    role = serializers.CharField(required=False, default='ordinary_user')

    def validate_username(self, value):
        if UserProfile.objects.filter(user_name=value).exists():
            raise serializers.ValidationError("用户名已存在，无法重复录入")
        return value

    def validate_domain(self, value):
        try:
            domain_obj = Domain.objects.get(name=value)
            self.domain_obj = domain_obj
        except Domain.DoesNotExist:
            raise serializers.ValidationError("无效的所属领域")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            hashed_password = make_password(validated_data['password'])

            user = UserProfile.objects.create(
                user_name=validated_data['username'],
                password_hash=hashed_password,
                email=validated_data.get('email') or None,
                phone=validated_data.get('phone') or None,
                organization=validated_data.get('company', ''),
                position=validated_data.get('job', ''),
                domain=self.domain_obj
            )

            # 分配角色
            role_name = validated_data.get('role', 'ordinary_user')
            role_obj, _ = Role.objects.get_or_create(name=role_name)
            UserRole.objects.create(user=user, role=role_obj)

            return user