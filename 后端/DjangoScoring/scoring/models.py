from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Enterprise(models.Model):
    """企业基本信息模型"""
    id = models.IntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = '企业基本信息'



class Patent(models.Model):
    """专利信息模型"""
    id = models.IntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = '专利信息'


class SoftwareCopyright(models.Model):
    """软件著作权信息模型"""
    id = models.IntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = '软件著作权'



class Certificate(models.Model):
    """证书信息模型"""
    id = models.IntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = '资质认证'


class Client(models.Model):
    """客户信息表"""
    id = models.IntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = '客户信息'


class Supplier(models.Model):
    """供应商信息表"""
    id = models.IntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = '供应商'

class AwardRanking(models.Model):
    """上榜榜单表"""
    id = models.IntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = "上榜榜单"

class Industry(models.Model):
    """行业分类"""
    id = models.IntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table = "行业分类"

class Risk(models.Model):
    """风险信息"""
    id = models.IntegerField(primary_key=True)

    class Meta:
        managed = False
        db_table =  "风险信息"



class ScoreResult(models.Model):
    """评分结果模型"""
    enterprise_id = models.IntegerField(primary_key=True)
    enterprise_name = models.CharField(max_length=255, blank=True, null=True)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="总评分", default=0.00)
    basic_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="基础评分", default=0.00)
    tech_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="科技属性评分", default=0.00)
    professional_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="专业能力评分", default=0.00)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "评分结果"
        verbose_name_plural = "评分结果"
        unique_together = (('enterprise_id', 'enterprise_name'),)

    def __str__(self):
        return f"{self.enterprise_name} - {self.total_score}"


class ScoreLog(models.Model):
    """评分日志模型"""
    enterprise_id = models.IntegerField(verbose_name="企业ID", null=True, blank=True)
    enterprise_name = models.CharField(verbose_name="企业名称",max_length=255, blank=True, null=True)
    score_type = models.CharField(max_length=20, verbose_name="评分类型", choices=[
        ('basic', '基础评分'),
        ('tech', '科技属性评分'),
        ('professional', '专业能力评分')
    ])
    score_value = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="评分值", default=0.00)
    description = models.TextField(verbose_name="描述", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "评分日志"
        verbose_name_plural = "评分日志"