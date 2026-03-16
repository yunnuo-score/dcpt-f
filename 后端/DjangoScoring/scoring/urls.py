from django.urls import path
from . import views

urlpatterns = [
    #path('api/enterprise/<int:enterprise_id>/score/', views.calculate_score, name='calculate_score'),
    #path('api/enterprise/<int:enterprise_id>/score/logs/', views.get_score_logs, name='score_logs'),
    path('industry-tree/', views.get_industry_tree, name='industry-tree'),
]