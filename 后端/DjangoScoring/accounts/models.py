from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.hashers import check_password, make_password

# ---------------------------------------------------------
# 3. 领域表 (对应 SQL: user_domains)
# ---------------------------------------------------------
class Domain(models.Model):
    # 显式定义主键，对应 domain_id
    domain_id = models.AutoField(primary_key=True, db_column='domain_id')

    # 关键：代码中用 .name 访问，但数据库存的是 domain_name
    name = models.CharField(max_length=50, unique=True, db_column='domain_name')

    description = models.TextField(blank=True, null=True, db_column='domain_description')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at', null=True)

    class Meta:
        db_table = 'user_domains'
        managed = False  # 告诉 Django 这张表已存在，不要尝试重新创建它

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# 2. 权限角色表 (对应 SQL: user_roles)
# ---------------------------------------------------------
class Role(models.Model):
    role_id = models.AutoField(primary_key=True, db_column='role_id')
    name = models.CharField(max_length=30, unique=True, db_column='role_name')
    description = models.TextField(blank=True, null=True, db_column='role_description')

    class Meta:
        db_table = 'user_roles'
        managed = False

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# 5. 邀请码表 (对应 SQL: user_dinvite_codes)
# 注意：你的 SQL 中 invite_code 是主键 (VARCHAR)，不是自增 ID
# ---------------------------------------------------------
class InviteCode(models.Model):
    # 这里的 primary_key 是字符型，对应 SQL 的 PRIMARY KEY (`invite_code`)
    code = models.CharField(max_length=50, primary_key=True, db_column='invite_code')

    is_used = models.BooleanField(default=False, db_column='is_used')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at', null=True)

    # 你的 SQL 中没有 used_by 外键列，所以这里不定义 ForeignKey，避免迁移报错
    # 如果需要记录谁用了，需要在业务逻辑层处理或手动加列

    class Meta:
        db_table = 'user_dinvite_codes'
        managed = False

    def __str__(self):
        return self.code


# ---------------------------------------------------------
# 1. 用户表 (对应 SQL: users)
# 注意：这是一张独立的业务用户表，包含密码哈希等，不完全等同于 Django Auth User
# ---------------------------------------------------------
class UserProfile(models.Model):
    user_id = models.AutoField(primary_key=True, db_column='user_id')

    user_name = models.CharField(max_length=100, unique=False, db_column='user_name')
    # 注意：SQL 中 user_name 没有唯一约束，但 email 和 phone 有

    password_hash = models.CharField(max_length=60, db_column='password_hash')
    email = models.CharField(max_length=100, unique=True, db_column='email', blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True, db_column='phone', blank=True, null=True)

    organization = models.CharField(max_length=100, blank=True, null=True, db_column='organization')
    position = models.CharField(max_length=100, blank=True, null=True, db_column='position')
    is_active = models.IntegerField(default=1, db_column='is_active')

    # 外键关联 Domain，指向 domain_id
    domain = models.ForeignKey(
        Domain,
        on_delete=models.PROTECT,
        db_column='domain_id',
        related_name='users',
        null=True,
        blank=True
    )

    registered_at = models.DateTimeField(db_column='registered_at', auto_now_add=True, null=True)
    last_login_at = models.DateTimeField(db_column='last_login_at', null=True, blank=True)
    updated_at = models.DateTimeField(db_column='updated_at', auto_now=True, null=True)

    class Meta:
        db_table = 'users'
        managed = False

    def __str__(self):
        return self.user_name


# ---------------------------------------------------------
# 4. 用户角色关联表 (对应 SQL: user_and_roles)
# ---------------------------------------------------------
class UserRole(models.Model):
    association_id = models.AutoField(primary_key=True, db_column='association_id')

    # 关联到上面的 UserProfile (因为你的 user_id 是在 users 表里)
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='role_assignments'
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        db_column='role_id',
        related_name='user_assignments'
    )

    assigned_at = models.DateTimeField(db_column='assigned_at', auto_now_add=True, null=True)

    class Meta:
        db_table = 'user_and_roles'
        managed = False
        unique_together = ('user', 'role')  # 对应 SQL 中的 UNIQUE KEY `uk_user_role`

    def __str__(self):
        return f"{self.user.user_name} - {self.role.name}"


# ---------------------------------------------------------
# 6. 操作日志表 (对应 SQL: user_operation_logs)
# ---------------------------------------------------------
class OperationLog(models.Model):
    log_id = models.AutoField(primary_key=True, db_column='log_id')

    user = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        db_column='user_id',
        related_name='operation_logs'
    )

    operation_time = models.DateTimeField(db_column='operation_time', auto_now_add=True, null=True)
    action = models.CharField(max_length=50, db_column='action')

    # 你的 SQL 中没有 details 字段，这里就不加了，保持严格一致

    class Meta:
        db_table = 'user_operation_logs'
        managed = False

    def __str__(self):
        return f"{self.action} ({self.operation_time})"