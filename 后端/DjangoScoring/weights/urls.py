# weights/urls.py
from django.urls import path
# 将 UpdateWeightView 改为 WeightUpdateView
from .views import WeightAllView, WeightUpdateView,run_scoring_task,get_scoring_status

urlpatterns = [
    path('all/', WeightAllView.as_view()),
    path('update/', WeightUpdateView.as_view()), # 确保这里也对应上
    path('run/', run_scoring_task),
    path('status/', get_scoring_status),
]