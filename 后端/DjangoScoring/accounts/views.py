import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.db.utils import IntegrityError
from .serializers import RegisterSerializer, LoginSerializer
from .models import UserProfile, OperationLog
from django.contrib.auth.hashers import make_password
from .models import UserProfile, OperationLog , Role, UserRole
from rest_framework.permissions import AllowAny
import random
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.response import Response
from django.db import connection,transaction
import jwt
from rest_framework_simplejwt.tokens import UntypedToken
from django.core.exceptions import ObjectDoesNotExist
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache  # 使用 Django 缓存框架连接 Redis
from .models import UserProfile, Domain
# 导入阿里云 SDK 示例
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from rest_framework import status


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                return Response({
                    "success": True,
                    "message": "注册成功",
                    "data": {"username": user.user_name, "email": user.email}
                }, status=status.HTTP_201_CREATED)
            except IntegrityError:
                # 触发了数据库的 unique_key 约束 (如邮箱或手机号重复)
                return Response({"success": False, "message": "邮箱或手机号已被注册"},
                                status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 提取第一个验证错误信息返回给前端
        errors = serializer.errors
        msg = "验证失败"
        for field, msgs in errors.items():
            if isinstance(msgs, list):
                msg = msgs[0]
                break
        return Response({"success": False, "message": msg}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        domain_name = request.data.get('domain')  # 获取前端传来的领域名称

        if not all([username, password, domain_name]):
            return Response({"success": False, "message": "请填写所有必填项"}, status=400)

        try:
            # 1. 联合查询：用户名 + 领域
            user = UserProfile.objects.get(
                user_name=username,
                domain__name=domain_name
            )

            # --- 新增逻辑：判断账号是否已注销 ---
            # 判断 user 对象是否有 is_active 属性（防止字段未创建报错）
            if hasattr(user, 'is_active') and user.is_active == 0:
                return Response({
                    "success": False,
                    "message": "该账号已注销，无法登录。如需找回请联系管理员。"
                }, status=403) # 403 Forbidden 表示服务器拒绝执行
            # --------------------------------

            # 2. 校验密码哈希
            if check_password(password, user.password_hash):
                # 更新登录时间
                user.last_login_at = timezone.now()
                user.save()

                # 3. 记录操作日志
                # 即使你把数据库 user_id 改为了 NULL，这里传入 user 对象依然能记录下 ID
                OperationLog.objects.create(
                    user=user,
                    action='登录'
                )

                # 4. 签发 Token
                refresh = RefreshToken()
                refresh['user_id'] = user.user_id

                # 获取角色名
                role_assignment = user.role_assignments.first()
                role_name = role_assignment.role.name if role_assignment else "ordinary_user"

                return Response({
                    "success": True,
                    "message": "登录成功",
                    "data": {
                        "token": str(refresh.access_token),
                        "user": {
                            "username": user.user_name,
                            "role": role_name,
                            "domain": domain_name
                        }
                    }
                })
            else:
                return Response({"success": False, "message": "用户名或密码错误"}, status=401)

        except UserProfile.DoesNotExist:
            return Response({"success": False, "message": "该领域下未找到此用户"}, status=401)
        except Exception as e:
            # 捕获其他潜在错误
            print(f"登录异常: {str(e)}")
            return Response({"success": False, "message": "系统错误，请联系管理员"}, status=500)


class SendCodeView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')

        try:
            user = UserProfile.objects.get(user_name=username, email=email)

            # 1. 生成 6 位随机验证码
            code = "".join([str(random.randint(0, 9)) for _ in range(6)])

            # 2. 【生产建议】这里应该把 code 存入 Redis 并设置 5 分钟过期
            # 暂时为了演示，我们可以把它打印在终端，或者存入 session
            request.session[f'reset_code_{username}'] = code

            # 3. 真正调用发送函数
            subject = '【区域产业链洞察平台】身份验证'
            message = f'您正在申请重置密码，验证码为：{code}，请于5分钟内完成验证。'

            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            return Response({"success": True, "message": "验证码已发送至您的邮箱"})

        except UserProfile.DoesNotExist:
            return Response({"success": False, "message": "信息校验失败"}, status=404)
        except Exception as e:
            return Response({"success": False, "message": f"邮件发送失败: {str(e)}"}, status=500)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        code = request.data.get('code')
        new_password = request.data.get('newPassword')

        # 调试打印：看看后端收到了什么，以及 Session 里存了什么
        print(f"DEBUG: 尝试重置用户 -> {username}")
        print(f"DEBUG: 前端传来的验证码 -> {code}")

        # 从 Session 获取之前存的验证码
        saved_code = request.session.get(f'reset_code_{username}')
        print(f"DEBUG: Session 中记录的验证码 -> {saved_code}")

        # 校验逻辑
        if not saved_code:
            return Response({"success": False, "message": "验证码已过期或Session已失效"}, status=400)

        if str(code).strip() != str(saved_code).strip():
            return Response({"success": False, "message": "验证码不正确"}, status=400)

        try:
            user = UserProfile.objects.get(user_name=username)
            user.password_hash = make_password(new_password)
            user.save()

            #记录操作日志
            OperationLog.objects.create(
                user=user,  # 关联当前用户
                action='重置密码'  # 对应你的 SQL 字段 action
            )

            # 成功后清除验证码
            del request.session[f'reset_code_{username}']

            return Response({"success": True, "message": "密码重置成功"})
        except UserProfile.DoesNotExist:
            return Response({"success": False, "message": "用户不存在"}, status=404)

class CheckUsernameView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        username = request.query_params.get('username')
        exists = UserProfile.objects.filter(user_name=username).exists()
        return Response({"exists": exists})

def get_user_from_token(request):
    """从请求头解析 Token 并返回 UserProfile 实例，失败返回 None"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None

    # 确保分割后的长度正确
    parts = auth_header.split(' ')
    if len(parts) != 2:
        return None
    raw_token = parts[1]

    try:
        decoded_token = UntypedToken(raw_token)
        user_id = decoded_token.get('user_id')
        return UserProfile.objects.get(user_id=user_id)
    except Exception as e:
        print(f"DEBUG: Token validation failed: {e}")
        return None

def is_admin(user):
    """判断用户是否为管理员"""
    if not user:
        return False
    role_assignment = user.role_assignments.first()
    return role_assignment and role_assignment.role.name == 'ADMIN'


class UserListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        operator = get_user_from_token(request)
        if not operator or not is_admin(operator):
            return Response({"success": False, "message": "越权操作"}, status=403)

        users = UserProfile.objects.prefetch_related('role_assignments__role').all()
        data = []
        for u in users:
            role_assignment = u.role_assignments.first()
            role_id = role_assignment.role.role_id if role_assignment else None
            role_name = role_assignment.role.name if role_assignment else "未分配"

            data.append({
                "user_id": u.user_id,
                "user_name": u.user_name,
                "role_id": role_id,
                "role_name": role_name,
                "is_active": getattr(u, 'is_active', 1) # 新增：返回当前状态给前端
            })

        return Response({"success": True, "data": data})


class UpdateUserRoleView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        # 1. 验证登录状态与管理员权限
        operator = get_user_from_token(request)
        if not operator:
            return Response({"success": False, "message": "未登录或 Token 已过期"}, status=status.HTTP_401_UNAUTHORIZED)

        if not is_admin(operator):
            return Response({"success": False, "message": "越权操作：只有管理员可以修改角色"},
                            status=status.HTTP_403_FORBIDDEN)

        # 2. 获取参数
        target_user_id = request.data.get('user_id')
        new_role_id = request.data.get('role_id')

        if not target_user_id or not new_role_id:
            return Response({"success": False, "message": "参数不全"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                target_user = UserProfile.objects.get(user_id=target_user_id)
                new_role = Role.objects.get(role_id=new_role_id)

                # 3. 使用 ORM 更新或创建权限映射
                # 注意你的 user_and_roles 表有 unique_together = ('user', 'role')
                # 这里假设每个用户只有一个角色，直接修改或覆盖
                from .models import UserRole
                # 先删除旧角色映射，再创建新的（或者用 update_or_create）
                UserRole.objects.filter(user=target_user).delete()
                UserRole.objects.create(user=target_user, role=new_role)

                # 4. 记录操作日志
                OperationLog.objects.create(
                    user=operator,
                    action=f"管理员(ID:{operator.user_id})修改了用户(ID:{target_user_id})的角色为:{new_role.name}"
                )

            return Response({"success": True, "message": "角色更新成功"})

        except UserProfile.DoesNotExist:
            return Response({"success": False, "message": "目标用户不存在"}, status=status.HTTP_404_NOT_FOUND)
        except Role.DoesNotExist:
            return Response({"success": False, "message": "所选角色不存在"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "message": f"操作失败: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

import string
from .models import InviteCode
from .serializers import AdminCreateUserSerializer

class InviteCodeListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        operator = get_user_from_token(request)
        if not is_admin(operator):
            return Response({"success": False, "message": "越权操作"}, status=status.HTTP_403_FORBIDDEN)

        # 获取所有未使用的邀请码
        codes = InviteCode.objects.filter(is_used=False).order_by('-created_at')
        data = [{
            "code": c.code,
            "created_at": c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else None
        } for c in codes]

        return Response({"success": True, "data": data})


class GenerateInviteCodeView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        operator = get_user_from_token(request)
        if not is_admin(operator):
            return Response({"success": False, "message": "越权操作"}, status=status.HTTP_403_FORBIDDEN)

        # 获取生成的数量，默认为 1
        count = int(request.data.get('count', 1))
        if count < 1 or count > 50:
            return Response({"success": False, "message": "一次最多生成50个"}, status=400)

        new_codes = []
        import string
        import random

        for _ in range(count):
            code_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            InviteCode.objects.create(code=code_str, is_used=False)
            new_codes.append(code_str)

        OperationLog.objects.create(
            user=operator,
            action=f"管理员批量生成了 {count} 个新邀请码"
        )

        return Response({
            "success": True,
            "message": f"成功生成 {count} 个邀请码",
            "data": {"codes": new_codes}
        })

class AdminCreateUserView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        operator = get_user_from_token(request)
        if not is_admin(operator):
            return Response({"success": False, "message": "越权操作"}, status=status.HTTP_403_FORBIDDEN)

        serializer = AdminCreateUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                OperationLog.objects.create(
                    user=operator,
                    action=f"管理员直接创建了新用户: {user.user_name}"
                )
                return Response({"success": True, "message": "用户创建成功"}, status=status.HTTP_201_CREATED)
            except IntegrityError:
                return Response({"success": False, "message": "邮箱或手机号已被注册"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        errors = serializer.errors
        msg = "验证失败"
        for field, msgs in errors.items():
            if isinstance(msgs, list):
                msg = msgs[0]
                break
        return Response({"success": False, "message": msg}, status=status.HTTP_400_BAD_REQUEST)


class DeleteUserView(APIView):
    """管理员管理用户状态 (禁用/恢复)"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        operator = get_user_from_token(request)
        if not operator or not is_admin(operator):
            return Response({"success": False, "message": "权限不足"}, status=403)

        target_user_id = request.data.get('user_id')
        target_status = request.data.get('target_status', 0)  # 前端如果传1就是恢复，传0就是禁用

        if not target_user_id:
            return Response({"success": False, "message": "未提供用户ID"}, status=400)

        if int(target_user_id) == operator.user_id:
            return Response({"success": False, "message": "不能操作当前登录的管理员账号"}, status=400)

        try:
            with transaction.atomic():
                target_user = UserProfile.objects.get(user_id=target_user_id)

                # 切换状态
                if hasattr(target_user, 'is_active'):
                    target_user.is_active = target_status
                    target_user.save()
                else:
                    return Response({"success": False, "message": "系统未配置软删除字段"}, status=500)

                action_str = "恢复" if target_status == 1 else "禁用"

                OperationLog.objects.create(
                    user=operator,
                    action=f"管理员{action_str}了用户: {target_user.user_name} (ID: {target_user_id})"
                )

            return Response({"success": True, "message": f"用户 {target_user.user_name} 已成功{action_str}"})

        except UserProfile.DoesNotExist:
            return Response({"success": False, "message": "目标用户不存在"}, status=404)
        except Exception as e:
            return Response({"success": False, "message": f"操作失败: {str(e)}"}, status=500)


class UserProfileView(APIView):
    """获取个人资料 - 核心修复版"""
    permission_classes = [AllowAny]  # 1. 允许进入，由下方逻辑手动校验
    authentication_classes = []

    def get(self, request):
        # 2. 使用你自定义的解析函数
        user = get_user_from_token(request)
        if not user:
            return Response({"success": False, "message": "身份验证失败"}, status=401)

        # 3. 获取角色名称
        role_assignment = user.role_assignments.first()
        role_name = role_assignment.role.name if role_assignment else "普通用户"

        # 4. 构建返回数据 (修复了字段读取报错)
        data = {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "email": user.email,
            "phone": user.phone,
            "organization": user.organization,
            "position": user.position,
            # 这里的 domain 是外键，读取它的 name 属性
            "domain_name": user.domain.name if user.domain else "未分配",
            "role_name": role_name,
            "registered_at": user.registered_at,
        }
        return Response({"success": True, "data": data})


class UpdateUserProfileView(APIView):
    """修改个人资料 (包含用户名、邮箱、手机等)"""
    permission_classes = [AllowAny]
    authentication_classes = []  # 之前解决 401 的关键

    def post(self, request):
        user = get_user_from_token(request)
        if not user:
            return Response({"success": False, "message": "身份验证失败"}, status=401)

        # 获取前端传来的所有字段
        user_name = request.data.get('user_name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        organization = request.data.get('organization')
        position = request.data.get('position')

        # 校验用户名是否与其他用户重复 (排除自己)
        if user_name and UserProfile.objects.exclude(user_id=user.user_id).filter(user_name=user_name).exists():
            return Response({"success": False, "message": "该用户名已被占用"}, status=400)

        # 更新字段
        if user_name: user.user_name = user_name
        if email: user.email = email
        if phone: user.phone = phone
        user.organization = organization
        user.position = position

        user.save()

        OperationLog.objects.create(user=user, action=f"用户更新了资料: {user_name}")
        return Response({"success": True, "message": "资料更新成功"})


class SecuritySettingsView(APIView):
    """安全设置 (密码与绑定)"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        user = get_user_from_token(request)
        if not user:
            return Response({"success": False, "message": "身份验证失败"}, status=401)

        action = request.data.get('action')

        if action == "change_password":
            old_password = request.data.get('old_password')
            new_password = request.data.get('new_password')

            # 校验原密码：注意你的字段名是 password_hash
            if not check_password(old_password, user.password_hash):
                return Response({"success": False, "message": "原密码错误"}, status=400)

            # 更新密码并加密
            user.password_hash = make_password(new_password)
            user.save()

            OperationLog.objects.create(user=user, action="修改登录密码")
            return Response({"success": True, "message": "密码修改成功"})

        elif action == "update_binding":
            user.email = request.data.get('email', user.email)
            user.phone = request.data.get('phone', user.phone)
            user.save()
            return Response({"success": True, "message": "绑定信息更新成功"})

        return Response({"success": False, "message": "无效操作"}, status=400)


class DeleteAccountView(APIView):
    """用户自主注销账号 (软删除方案)"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def delete(self, request):
        user = get_user_from_token(request)
        if not user:
            return Response({"success": False, "message": "身份验证失败"}, status=401)

        try:
            # 1. 记录注销日志
            # 此时 user_id 会保留在日志表里，因为用户记录没被删
            OperationLog.objects.create(
                user=user,
                action=f"用户 {user.user_name} 办理了注销，账号已禁用"
            )

            # 2. 执行逻辑删除（软删除）
            # 修改状态位，不再物理删除 user 对象
            user.is_active = 0
            # 如果你希望注销后释放手机号/邮箱占用，可以在这里清空，或者保留以防重复注册
            user.save()

            return Response({"success": True, "message": "账号注销成功，感谢您的使用"})

        except Exception as e:
            print(f"注销操作报错: {str(e)}")
            return Response({"success": False, "message": "服务器内部错误"}, status=500)