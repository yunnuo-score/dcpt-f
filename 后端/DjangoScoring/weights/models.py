# weights/models.py
from django.db import models

class ScoreModelBasicWeight(models.Model):
    model_id = models.BigAutoField(primary_key=True)
    model_name = models.CharField(max_length=100)
    established_year = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    registered_capital = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    actual_paid_capital = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    company_type = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    enterprise_size_type = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    social_security_count = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    website = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    business_scope = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_rating = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_type = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    funding_round = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    patent_type = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    software_copyright = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    technology_enterprise = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'score_model_basic_weight'
        managed = False

class ScoreModelProfessionalWeight(models.Model):
    model_id = models.BigAutoField(primary_key=True)
    model_name = models.CharField(max_length=100)
    industry_market_size = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    industry_heat = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    industry_profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    qualification = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    certificates = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    innovation = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    partnership_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ranking = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'score_model_professional_weight'
        managed = False

class ScoreModelTechWeight(models.Model):
    model_id = models.BigAutoField(primary_key=True)
    model_name = models.CharField(max_length=100)
    tech_patent_type = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    patent_tech_attribute = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tech_software_copyright = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    software_copyright_tech_attribute = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tech_technology_enterprise = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    industry_university_research = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    national_provincial_award = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'score_model_tech_weight'
        managed = False

class ScoreModelTotalWeight(models.Model):
    model_id = models.BigAutoField(primary_key=True)
    model_name = models.CharField(max_length=100)
    model_weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'score_model_total_weight'
        managed = False