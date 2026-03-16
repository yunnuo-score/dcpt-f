from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import AccessToken
from .models import (
    ScoreModelBasicWeight, ScoreModelProfessionalWeight,
    ScoreModelTechWeight, ScoreModelTotalWeight
)


# 封装 Token 验证助手，处理引号干扰
def validate_token(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION', "")
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    try:
        raw_token = auth_header.split(' ')[1]
        clean_token = raw_token.strip().strip('"').strip("'")
        return AccessToken(clean_token)
    except:
        return None


class WeightAllView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if not validate_token(request):
            return Response({"success": False, "message": "认证失败"}, status=401)

        # 基础指标数据
        b = ScoreModelBasicWeight.objects.first()
        b_fields = [("established_year", "成立年限"), ("registered_capital", "注册资本"),
                    ("actual_paid_capital", "实缴资本"), ("company_type", "公司类型"),
                    ("enterprise_size_type", "企业规模"), ("social_security_count", "社保人数"), ("website", "网址"),
                    ("business_scope", "经营范围"), ("tax_rating", "纳税人等级"), ("tax_type", "纳税人类型"),
                    ("funding_round", "投融资轮次"), ("patent_type", "专利类型"), ("software_copyright", "软件著作权"),
                    ("technology_enterprise", "科技型企业")]
        b_list = [{"key": f[0], "name": f[1], "weight": float(getattr(b, f[0]) or 0)} for f in b_fields] if b else []

        # 科技指标数据
        t_obj = ScoreModelTechWeight.objects.first()
        t_fields = [("tech_patent_type", "专利类型"), ("patent_tech_attribute", "专利属性"),
                    ("tech_software_copyright", "软件著作权"), ("software_copyright_tech_attribute", "软著属性"),
                    ("tech_technology_enterprise", "科技企业"), ("industry_university_research", "产学研"),
                    ("national_provincial_award", "国省级奖励")]
        t_list = [{"key": f[0], "name": f[1], "weight": float(getattr(t_obj, f[0]) or 0)} for f in
                  t_fields] if t_obj else []

        # 专业指标数据
        p = ScoreModelProfessionalWeight.objects.first()
        p_fields = [("industry_market_size", "市场规模"), ("industry_heat", "行业热度"),
                    ("industry_profit_margin", "利润率"), ("qualification", "资质"), ("certificates", "证书"),
                    ("innovation", "创新性"), ("partnership_score", "合作评分"), ("ranking", "专业榜单")]
        p_list = [{"key": f[0], "name": f[1], "weight": float(getattr(p, f[0]) or 0)} for f in p_fields] if p else []

        # 总权重数据
        total_qs = ScoreModelTotalWeight.objects.all()
        total_list = [{"key": str(x.model_id), "name": x.model_name, "weight": float(x.model_weight or 0)} for x in
                      total_qs]

        return Response({
            "success": True,
            "data": {"total": total_list, "basic": b_list, "tech": t_list, "professional": p_list}
        })


class WeightUpdateView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not validate_token(request):
            return Response({"success": False, "message": "认证失败"}, status=401)

        level = request.data.get('level')
        data = request.data.get('data', [])

        try:
            if level == "TOTAL":
                for item in data:
                    ScoreModelTotalWeight.objects.filter(model_id=int(item['key'])).update(model_weight=item['weight'])
            elif level == "BASIC":
                ScoreModelBasicWeight.objects.filter(model_id=1).update(**{i['key']: i['weight'] for i in data})
            elif level == "TECH":
                ScoreModelTechWeight.objects.filter(model_id=1).update(**{i['key']: i['weight'] for i in data})
            elif level == "PROFESSIONAL":
                ScoreModelProfessionalWeight.objects.filter(model_id=1).update(**{i['key']: i['weight'] for i in data})

            return Response({"success": True, "message": "保存成功"})
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=500)


from django.core.management import call_command
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import threading
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.core.cache import cache # 导入缓存

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def run_scoring_task(request):
    token_obj = validate_token(request)
    if not token_obj:
        return JsonResponse({"success": False, "message": "认证失败"}, status=401)

    # 标记任务开始
    cache.set("scoring_status", "running", timeout=3600)

    def start_scoring():
        try:
            call_command('run_scoring')
            # 任务成功结束，修改状态
            cache.set("scoring_status", "completed", timeout=600)
        except Exception as e:
            # 任务失败，记录错误
            cache.set("scoring_status", f"failed: {str(e)}", timeout=600)

    threading.Thread(target=start_scoring).start()
    return JsonResponse({"success": True, "message": "评分引擎已启动"})

# 2. 新增查询状态的接口
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_scoring_status(request):
    status = cache.get("scoring_status", "idle") # 默认空闲
    return JsonResponse({"success": True, "status": status})