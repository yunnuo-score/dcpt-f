from django.db import transaction,connection
from django.db.models import Count
from .models import Enterprise, Patent, SoftwareCopyright, ScoreResult, ScoreLog
#from .models import Certificate, Industry
from weights.models import (
    ScoreModelBasicWeight,
    ScoreModelTechWeight,
    ScoreModelProfessionalWeight,
    ScoreModelTotalWeight
)


class DataAdapter:
    """企业信息适配器——适配分散在多个表中的企业数据"""

    def __init__(self, enterprise_id=None, enterprise_name=None):
        self.enterprise_id = enterprise_id
        self.enterprise_name = enterprise_name
        self.data = None

    def get_data(self):
        """从数据库中获取完整的企业数据"""
        if self.data is not None:
            return self.data

        # 根据企业ID或名称查询
        if self.enterprise_id:
            query = """
                    SELECT e.`企业名称`         AS name,
                           e.`成立年限`         AS established_year,
                           e.`注册资本`         AS registered_capital,
                           e.`实缴资本`         AS actual_paid_capital,
                           e.`企业类型`         AS company_type,
                           e.`企业规模`         AS enterprise_size_type,
                           e.`经营范围`         AS business_scope,
                           e.`投融资轮次`       AS funding_round,
                           q.`社保人数`         AS social_security_count,
                           q. `税务评级`        AS tax_rating,
                           q.`是否为一般纳税人`  AS tax_type,
                           z.`高新技术企业`     AS is_high_tech,
                           z.`专精特新中小企业` AS is_specialized,
                           z.`创新型中小企业`   AS is_innovative
                    FROM `企业基本信息` e
                             LEFT JOIN `知识产权` z ON e.`企业名称` = z.`企业名称`
                             LEFT JOIN `企业经营信息` q ON e.`企业名称` = q.`企业名称`
                    WHERE e.`id` = %s 
                    """
            params = (self.enterprise_id,)
        elif self.enterprise_name:
            query = """
                    SELECT e.`企业名称`         AS name,
                           e.`成立年限`         AS established_year,
                           e.`注册资本`         AS registered_capital,
                           e.`实缴资本`         AS actual_paid_capital,
                           e.`企业类型`         AS company_type,
                           e.`企业规模`         AS enterprise_size_type,
                           e.`经营范围`         AS business_scope,
                           e.`投融资轮次`       AS funding_round,
                           q.`社保人数`         AS social_security_count,
                           q. `税务评级`        AS tax_rating,
                           q.`是否为一般纳税人`  AS tax_type,
                           z.`高新技术企业`     AS is_high_tech,
                           z.`专精特新中小企业` AS is_specialized,
                           z.`创新型中小企业`   AS is_innovative
                    FROM `企业基本信息` e
                             LEFT JOIN `知识产权` z ON e.`企业名称` = z.`企业名称`
                             LEFT JOIN `企业经营信息` q ON e.`企业名称` = q.`企业名称`
                    WHERE e.`企业名称` = %s 
                    """
            params = (self.enterprise_name,)
        else:
            raise ValueError("必须提供企业ID或企业名称")

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        if not row:
            raise ValueError("未找到企业数据")

        # 将结果转换为字典
        self.data = {
            'name': row[0],
            'established_year': row[1],
            'registered_capital': row[2],
            'actual_paid_capital': row[3],
            'company_type': row[4],
            'enterprise_size_type': row[5],
            'business_scope': row[6],
            'funding_round': row[7],
            'social_security_count':row[8],
            'tax_rating':row[9],
            'tax_type':row[10]== 1,
            'is_high_tech': row[11] == 1,        # 关键：转为 bool
            'is_specialized': row[12] == 1,
            'is_innovative': row[13] == 1,
        }
        return self.data

    def get_patents(self):
        """获取该企业的专利数据（适配分散表）"""
        if not self.enterprise_id:
            return []

        # 请根据您的实际表名和字段修改
        query = """
                SELECT z.专利号, \
                       z.专利类型, \
                       z.专利名称, \
                       z.申请日
                FROM `企业基本信息` e
                             LEFT JOIN `专利信息` z ON e.`企业名称` = z.`申请人`
                WHERE e.id = %s \
                """
        params = (self.enterprise_id,)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                'patent_number': row[0],
                'patent_type': row[1],
                'patent_name': row[2],
                'application_date': row[3]
            }
            for row in rows
        ]

    def get_software_copyrights(self):
        """获取该企业的软件著作权数据"""
        if not self.enterprise_id:
            return []

        query = """
                SELECT z.软件名称, \
                       z.登记号, \
                       z.软件简称, \
                       z.登记批准日期, \
                       z.状态, \
                       z.取得方式
                FROM `企业基本信息` e
                             LEFT JOIN `软件著作权` z ON e.`企业名称` = z.`著作权人`
                WHERE e.id = %s \
                """
        params = (self.enterprise_id,)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                'copyright_name': row[0],
                'copyright_number': row[1],
                'copyright_short_name': row[2],
                'registration_date': row[3],
                'status': row[4],
                'acquisition_method': row[5]
            }
            for row in rows
        ]

    def get_certificates(self):
        """获取该企业的证书信息数据"""
        if not self.enterprise_id:
            return []

        query = """
                SELECT z.证书名称, \
                       z.证书类型, \
                       z.证书编号, \
                       z.发证日期, \
                       z.截止日期
                FROM `企业基本信息` e
                             LEFT JOIN `资质认证` z ON e.`企业名称` = z.`企业名称`
                WHERE e.id = %s \
                """
        params = (self.enterprise_id,)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                'certificate_name': row[0],
                'certificate_type': row[1],
                'certificate_number': row[2],
                'issue_date': row[3],
                'expiration_date': row[4]
            }
            for row in rows
        ]

    def get_client(self):
        """获取该企业的客户信息数据"""
        if not self.enterprise_id:
            return []

        query = """
                SELECT k.公司名称, \
                       k.客户名称
                FROM `企业基本信息` e
                             LEFT JOIN `客户信息` k ON e.`企业名称` = k.`公司名称`
                WHERE e.id = %s \
                """
        params = (self.enterprise_id,)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                'enterprise_name': row[0],
                'client_name': row[1]
            }
            for row in rows
        ]

    def get_supplier(self):
        """获取该企业的供应商信息数据"""
        if not self.enterprise_id:
            return []

        query = """
                SELECT g.企业名称, \
                       g.供应商
                FROM `企业基本信息` e
                             LEFT JOIN `供应商` g ON e.`企业名称` = g.`企业名称`
                WHERE e.id = %s \
                """
        params = (self.enterprise_id,)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                'enterprise_name': row[0],
                'supplier_name': row[1],
            }
            for row in rows
        ]

    def get_awardRanking(self):
        """获取该企业的上榜榜单信息数据"""
        if not self.enterprise_id:
            return []

        query = """
                SELECT b.企业名称, \
                       b.榜单名称, \
                       b.年份
                FROM `企业基本信息` e
                             LEFT JOIN `上榜榜单` b ON e.`企业名称` = b.`企业名称`
                WHERE e.id = %s \
                """
        params = (self.enterprise_id,)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                'enterprise_name': row[0],
                'award_name': row[1],
                'ranking_year': row[2]
            }
            for row in rows
        ]

    def get_industry(self):
        """获取该企业的分类数据"""
        if not self.enterprise_id:
            return []

        query = """
                SELECT h.企业名称, \
                       h.分类
                FROM `企业基本信息` e
                             LEFT JOIN `行业分类` h ON e.`企业名称` = h.`企业名称`
                WHERE e.id = %s \
                """
        params = (self.enterprise_id,)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                'enterprise_name': row[0],
                'industry': row[1]
            }
            for row in rows
        ]

    def get_risk(self):
        """获取该企业的风险信息"""
        if not self.enterprise_id:
            return []

        query = """
                SELECT f.企业名称, \
                       f.失信被执行, \
                       f.限制高消费, \
                       f.经营异常, \
                       f.集群注册
                FROM `企业基本信息` e
                             LEFT JOIN `风险信息` f ON e.`企业名称` = f.`企业名称`
                WHERE e.id = %s \
                """
        params = (self.enterprise_id,)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [
            {
                'enterprise_name': row[0],
                'dishonest': row[1],
                'restricted': row[2],
                'abnormal': row[3],
                'cluster_registration': row[4]
            }
            for row in rows
        ]

    def get_enterprise_model(self):
        """转换为 Enterprise 模型对象（包含关联数据）"""
        data = self.get_data()

        patents = self.get_patents()
        software_copyrights = self.get_software_copyrights()
        certificates = self.get_certificates()
        client = self.get_client()
        supplier = self.get_supplier()
        awardRanking = self.get_awardRanking()
        industry =self.get_industry()
        risk = self.get_risk()


        # 创建临时模型对象
        class FakeEnterprise:
            def __init__(self, data, patents, software_copyrights,certificates,client,supplier,awardRanking,industry,risk):
                self.name = data['name']
                self.established_year = data['established_year']
                self.registered_capital = data['registered_capital']
                self.actual_paid_capital = data['actual_paid_capital']
                self.company_type = data['company_type']
                self.enterprise_size_type = data['enterprise_size_type']
                self.business_scope = data['business_scope']
                self.funding_round = data['funding_round']
                self.social_security_count = data['social_security_count']
                self.tax_rating = data['tax_rating']
                self.tax_type = data['tax_type']
                self.is_high_tech = data['is_high_tech']
                self.is_specialized = data['is_specialized']
                self.is_innovative = data['is_innovative']

                # 添加关联数据
                self.patents = patents
                self.software_copyrights = software_copyrights
                self.certificates = certificates
                self.client = client
                self.supplier = supplier
                self.awardRanking = awardRanking
                self.industry = industry
                self.risk = risk


            # 为兼容性添加简单方法（使 len() 和遍历工作）
            def __len__(self):
                return len(self.patents)

            def __iter__(self):
                return iter(self.patents)

        return FakeEnterprise(data, patents, software_copyrights,certificates,client,supplier,awardRanking,industry,risk)






class ScoringCalculator:

    """评分计算器，实现评分逻辑"""

    def __init__(self, enterprise_id=None, enterprise_name=None):
        if not enterprise_id and not enterprise_name:
            raise ValueError("必须提供企业ID或名称")

        self.original_enterprise_id = enterprise_id
        self.enterprise_name = enterprise_name

        # 使用适配器获取数据
        self.adapter = DataAdapter(enterprise_id=self.original_enterprise_id, enterprise_name=self.enterprise_name)
        self.enterprise = self.adapter.get_enterprise_model()

        # 用于暂存所有的日志，最后统一批量写入数据库
        self.log_entries = []

        self.BASE_MAX = {
            "established_year": 5.0, "registered_capital": 6.0, "actual_paid_capital": 8.0,
            "company_type": 7.0, "enterprise_size_type": 5.0, "social_security_count": 6.0,
            "website": 2.0, "business_scope": 5.0, "tax_rating": 3.0, "tax_type": 3.0,
            "funding_round": 10.0, "patent_type": 15.0, "software_copyright": 15.0, "technology_enterprise": 10.0,
            "tech_patent_type": 10.0, "patent_tech_attribute": 20.0, "tech_software_copyright": 10.0,
            "software_copyright_tech_attribute": 20.0, "tech_technology_enterprise": 15.0,
            "industry_university_research": 15.0, "national_provincial_award": 10.0,
            "industry_market_size": 10.0, "industry_heat": 10.0, "industry_profit_margin": 10.0,
            "qualification": 20.0, "certificates": 20.0, "innovation": 10.0,
            "partnership_score": 10.0, "ranking": 10.0
        }

        # 2. 报错根源：必须先调用此方法赋值给 self.db_weights
        self.db_weights = self._load_db_weights()

    def _load_db_weights(self):
        """新增：从数据库获取实时权重"""
        return {
            "basic": ScoreModelBasicWeight.objects.first(),
            "tech": ScoreModelTechWeight.objects.first(),
            "pro": ScoreModelProfessionalWeight.objects.first(),
            "total": {w.model_name: float(w.model_weight) for w in ScoreModelTotalWeight.objects.all()}
        }

    def _get_scale(self, level, field_key):
        """新增：计算 权重/满分 的比例"""
        db_config = self.db_weights.get(level)
        base_max = self.BASE_MAX.get(field_key, 1.0)
        # 如果数据库没有配置，则不进行缩放（比例为 1.0）
        target_weight = float(getattr(db_config, field_key, base_max)) if db_config else base_max
        return target_weight / base_max


    def _add_log(self, score_type, score, description):
        """统一的日志记录辅助方法"""
        self.log_entries.append({
            'score_type': score_type,
            'score': score,
            'description': description
        })

    def calculate_all_scores(self):
        """计算所有维度的分数并更新总分"""
        with transaction.atomic():
            b_score = self.calculate_basic_score()
            t_score = self.calculate_tech_score()
            p_score = self.calculate_professional_score()

            # 获取总模型权重配置表 (score_model_total_weight)
            w_total = self.db_weights['total']

            # 匹配名称：对应你 SQL INSERT 里的名字
            r_basic = w_total.get('企业基础标准评分模型', 34) / 100.0
            r_tech = w_total.get('科技属性标准评分模型', 33) / 100.0
            r_pro = w_total.get('专业能力标准评分模型', 33) / 100.0

            total_score = (b_score * r_basic) + (t_score * r_tech) + (p_score * r_pro)

            # 2. 统一保存或更新 ScoreResult（修复了 enterprise_name 丢失的问题）
            score_result, created = ScoreResult.objects.update_or_create(
                enterprise_id=self.original_enterprise_id,
                defaults={
                    'enterprise_name': self.enterprise.name,
                    'total_score': round(total_score, 2),
                    'basic_score': round(b_score, 2),
                    'tech_score': round(t_score, 2),
                    'professional_score': round(p_score, 2)
                }
            )

            # 3. 统一保存 ScoreLog
            # 为防止多次运行产生重复日志，先清空旧日志
            ScoreLog.objects.filter(enterprise_id=self.original_enterprise_id).delete()

            # 使用 ORM 批量创建，性能更好且不会与模型定义冲突
            logs_to_create = [
                ScoreLog(
                    enterprise_id=self.original_enterprise_id,  # 对应 models 中的 ForeignKey
                    enterprise_name=self.enterprise.name,
                    score_type=log['score_type'],
                    score_value=log['score'],
                    description=log['description']
                )
                for log in self.log_entries
            ]
            if logs_to_create:
                ScoreLog.objects.bulk_create(logs_to_create)

        return round(total_score, 2)

    def calculate_basic_score(self):
        """计算基础评分 (按数据库权重等比缩放)"""
        score = 0
        raw_total = 0  # 用于对比原始总分

        # 辅助函数：执行原函数并乘上缩放因子
        def add(func, field_key):
            raw = func()
            nonlocal raw_total
            raw_total += raw
            return raw * self._get_scale('basic', field_key)

        # 1-14. 依次调用你的原函数并进行缩放
        score += add(self.calculate_established_year, 'established_year')
        score += add(self.calculate_registered_capital, 'registered_capital')
        score += add(self.calculate_actual_paid_capital, 'actual_paid_capital')
        score += add(self.calculate_company_type, 'company_type')
        score += add(self.calculate_enterprise_size_type, 'enterprise_size_type')
        score += add(self.calculate_social_security_count, 'social_security_count')

        # 你的注释里网址被注释掉了，如果启用就是：
        # score += add(self.calculate_website, 'website')

        score += add(self.calculate_business_scope, 'business_scope')
        score += add(self.calculate_tax_rating, 'tax_rating')
        score += add(self.calculate_tax_type, 'tax_type')
        score += add(self.calculate_funding_round, 'funding_round')
        score += add(self.calculate_patent_type, 'patent_type')
        score += add(self.calculate_software_copyright, 'software_copyright')
        score += add(self.calculate_technology_enterprise, 'technology_enterprise')

        # 15. 扣分项 (重要：扣分项通常不需要根据动态权重缩放，直接加减即可)
        deduction = self.calculate_risk_penalties()
        score += deduction

        # 记录一个总的调整日志，解释分差
        final_score = max(round(score, 2), 0)
        self._add_log('basic', final_score,
                      f"基础模块计算完毕：原始累加分 {round(raw_total, 2)}，根据数据库动态权重缩放后得分为 {final_score}")

        return final_score

    # === 基础评分方法 ===

    #扣分
    def calculate_risk_penalties(self):
        """计算风险扣分项"""
        penalty_total = 0

        # 1. 失信被执行人 (-50)
        if self.enterprise.risk[0].get('dishonest') != 0:
            penalty_total -= 50
            self._add_log('basic', -50, '风险项：企业存在失信被执行记录，扣50分')

        # 2. 限制高消费 (-50)
        if self.enterprise.risk[0].get('restricted') != 0:
            penalty_total -= 50
            self._add_log('basic', -50, '风险项：企业存在限制高消费记录，扣50分')

        # 3. 经营异常 (-10)
        if self.enterprise.risk[0].get('abnormal') != 0:
            penalty_total -= 10
            self._add_log('basic', -10, '风险项：企业经营异常，扣10分')

        # 4. 注册地址（集群注册）
        if self.enterprise.risk[0].get('cluster_registration') != 0:
            penalty_total -= 2
            self._add_log('basic', -2, f'风险项：注册地址(集群注册)，扣2分')

        return penalty_total

    def calculate_established_year(self):
        """计算成立年限得分（支持 'YYYY-MM-DD' 格式的成立日期）"""
        from datetime import datetime

        score = 0
        now = datetime.now()  # 当前时间：2026-03-01 18:22:xx

        if self.enterprise.established_year is None:
            score = 1
            self._add_log(
                'basic', score,'成立年限：未提供，基础分1分'
            )
        else:
            try:
                # 解析字符串为 datetime 对象
                est_date = datetime.strptime(self.enterprise.established_year, '%Y-%m-%d')
            except (ValueError, TypeError):
                # 如果格式错误或无法解析，视为未提供
                score = 1
                self._add_log(
                    'basic', score, '成立年限：格式无效，视为未提供，1分'
                )
                return score

            # 计算完整年数（考虑月日）
            years = now.year - est_date.year
            # 如果当前日期还没到成立日的周年，则减1年
            if (now.month, now.day) < (est_date.month, est_date.day):
                years -= 1

            if years <= 1:
                score = 1
                desc = '成立年限：1年内，1分'
            elif years <= 5:  # 1 < years <= 5
                score = 3
                desc = '成立年限：1-5年，3分'
            elif years <= 10:  # 5 < years <= 10
                score = 4
                desc = '成立年限：5-10年，4分'
            else:  # years > 10
                score = 5
                desc = '成立年限：10年以上，5分'

            self._add_log(
                'basic',score, desc
            )

        return score

    def calculate_registered_capital(self):
        """计算注册资本得分（支持 '6578.1万元人民币' 格式）"""
        score = 0
        capital_str = self.enterprise.registered_capital

        if capital_str is None:
            score = 2
            self._add_log(
                'basic', score,'注册资本：未提供，基础分2分'
            )
            return score

        try:
            # 提取数字部分（支持 "6578.1万"、"6578.1万元"、"6578.1万元人民币" 等）
            import re
            # 匹配数字（整数或小数），如 6578.1
            num_match = re.search(r'(\d+\.?\d*)', capital_str)
            if not num_match:
                raise ValueError("无法提取数字")
            capital = float(num_match.group(1))  # 得到 6578.1（单位：万元）

            # 评分逻辑（直接按万元单位计算）
            if capital <= 100:
                score = 2
                desc = '注册资本：0-100万，2分'
            elif capital <= 200:
                score = 3
                desc = '注册资本：100-200万，3分'
            elif capital <= 500:
                score = 4
                desc = '注册资本：200-500万，4分'
            elif capital <= 1000:
                score = 5
                desc = '注册资本：500-1000万，5分'
            else:
                score = 6
                desc = '注册资本：1000万以上，6分'

            self._add_log(
                'basic',score, desc)

        except (ValueError, TypeError) as e:
            # 格式错误时视为未提供
            score = 2
            self._add_log(
                'basic', score, f'注册资本：格式无效（{str(e)}），视为未提供，2分'
            )

        return score

    def calculate_actual_paid_capital(self):
        """计算实缴资本得分（支持 '100291.9万元人民币' 格式）"""
        score = 0
        capital_str = self.enterprise.actual_paid_capital

        if capital_str is None:
            score = 1
            self._add_log(
                'basic',score, '实缴资本：未提供，基础分1分'
            )
            return score

        try:
            # 提取数字部分（支持 "100291.9万"、"100291.9万元" 等）
            import re
            num_match = re.search(r'(\d+\.?\d*)', capital_str)
            if not num_match:
                raise ValueError("无法提取数字")
            capital = float(num_match.group(1))  # 得到 100291.9（单位：万元）

            # 评分逻辑（直接按万元单位计算）
            if capital == 0:
                score = 1
                desc = '实缴资本：无实缴，1分'
            elif capital <= 100:
                score = 3
                desc = '实缴资本：0-100万，3分'
            elif capital <= 500:
                score = 6
                desc = '实缴资本：100-500万，6分'
            else:
                score = 8
                desc = '实缴资本：500万以上，8分'

            self._add_log(
                'basic', score, desc
            )

        except (ValueError, TypeError) as e:
            # 格式错误时视为未提供
            score = 1
            self._add_log(
                'basic', score, f'实缴资本：格式无效（{str(e)}），视为未提供，1分'
            )

        return score

    def calculate_company_type(self):
        """计算公司类型得分"""
        score = 0
        if self.enterprise.company_type is None:
            score = 1
            self._add_log(
                'basic',score,'公司类型：未提供，基础分1分'
            )
        else:
            if self.enterprise.company_type in ['央企', '上市公司']:
                score = 7
                self._add_log(
                'basic',score,'公司类型：央企/上市公司，7分'
                )
            elif self.enterprise.company_type in ['国有企业', '股份有限公司']:
                score = 5
                self._add_log(
                'basic', score, '公司类型：国有企业/股份有限公司，5分'
                )
            elif self.enterprise.company_type in ['有限责任公司', '外商投资']:
                score = 4
                self._add_log(
                'basic',score,'公司类型：有限责任公司/外商投资，4分'
                )
            elif self.enterprise.company_type in ['自然人投资或控股', '股份合作制']:
                score = 3
                self._add_log(
                'basic', score, '公司类型：自然人投资或控股/股份合作制，3分'
                )
            elif self.enterprise.company_type in ['个人独资', '自然人独资', '合伙']:
                score = 2
                self._add_log(
                'basic',score, '公司类型：个人独资/自然人独资/合伙，2分'
                )
            else:
                score = 1
                self._add_log(
                'basic',score, '公司类型：其他，1分'
                )
        return score

    def calculate_enterprise_size_type(self):
        """计算企业规模（分型）得分"""
        score = 0
        if self.enterprise.enterprise_size_type is None:
            score = 1
            self._add_log(
                'basic', score,'企业规模（分型）：未提供，基础分1分'
            )
        else:
            if self.enterprise.enterprise_size_type == '大型企业':
                score = 5
                self._add_log(
                'basic', score,'企业规模（分型）：大，5分'
                )
            elif self.enterprise.enterprise_size_type == '中型企业':
                score = 4
                self._add_log(
                'basic',score,'企业规模（分型）：中，4分'
                )
            elif self.enterprise.enterprise_size_type == '小型企业':
                score = 3
                self._add_log(
                'basic',score, '企业规模（分型）：小，3分'
                )
            elif self.enterprise.enterprise_size_type == '微型企业':
                score = 2
                self._add_log(
                    'basic',score,
                     '企业规模（分型）：微，2分'
                )
            else:
                score = 1
                self._add_log(
                    'basic',score,
                     '企业规模（分型）：其他，1分'
                )
        return score

    def calculate_social_security_count(self):
        """计算企业规模（社保人数）得分"""
        score = 0
        if self.enterprise.social_security_count is None:
            score = 0
            self._add_log(
                'basic',score,
                 '社保人数：未提供，0分'
            )
        else:
            if self.enterprise.social_security_count < 30:
                score = 2
                self._add_log(
                    'basic',score,
                     '社保人数：小于30人，2分'
                )
            elif 30 <= self.enterprise.social_security_count < 50:
                score = 3
                self._add_log(
                    'basic',score,
                     '社保人数：30-50人，3分'
                )
            elif 50 <= self.enterprise.social_security_count < 100:
                score = 4
                self._add_log(
                    'basic',score,
                     '社保人数：50-99人，4分'
                )
            elif 100 <= self.enterprise.social_security_count < 500:
                score = 5
                self._add_log(
                    'basic',score,
                     '社保人数：100-499人，5分'
                )
            else:
                score = 6
                self._add_log(
                    'basic',score,
                     '社保人数：500人以上，6分'
                )
        return score

    def calculate_website(self):
        """计算网址得分"""
        score = 0
        if self.enterprise.website:
            score = 2
            self._add_log(
                'basic',score,
                 '网址：有，2分'
            )
        else:
            score = 0
            self._add_log(
                'basic',score,
                 '网址：无，0分'
            )
        return score

    def calculate_business_scope(self):
        """计算经营范围得分（智能分割版，适配真实数据）"""
        score = 0
        if self.enterprise.business_scope is None:
            score = 1
            self._add_log(
                'basic',score,
                 '经营范围：未提供，基础分1分'
            )
            return score

        business_scope = self.enterprise.business_scope
        # 定义类别匹配词组（含符号变体和常见同义词）
        class3_keywords = ['第三类', 'III类', 'Ⅲ类', '三类', '第三类医疗器械', '三类医疗器械']
        class2_keywords = ['第二类', 'II类', 'Ⅱ类', '二类', '第二类医疗器械', '二类医疗器械']
        class1_keywords = ['第一类', 'I类', 'Ⅰ类', '一类', '第一类医疗器械', '一类医疗器械']

        # 1. 智能分割经营范围（优先分号，智能处理句号）
        # 步骤：
        # a) 将中文分号（；）替换为临时标记
        # b) 将描述性句号（.）保留，但项目分隔句号替换为分号
        # c) 按分号分割
        temp_marker = "###TEMP###"
        business_scope_clean = business_scope.replace('；', temp_marker)

        # 仅将作为项目分隔符的句号替换（避免描述性句号）
        # 规则：如果句号后是"许可项目"或"一般项目"或下一个项目开头，视为分隔符
        # 但为简化，我们假设：句号后紧跟中文/数字/字母（非标点）视为项目分隔
        import re
        # 替换项目分隔句号：句号后跟中文/数字/字母
        business_scope_clean = re.sub(r'。(?=[\u4e00-\u9fff0-9a-zA-Z])', ';', business_scope_clean)

        # 将临时标记替换回分号
        business_scope_clean = business_scope_clean.replace(temp_marker, ';')

        # 按分号分割
        scope_items = [item.strip() for item in business_scope_clean.split(';')]

        # 2. 逐个经营项目短语检查
        for item in scope_items:
            # 跳过空项目
            if not item:
                continue

            # 1. 检查3类生产（最高优先级）
            if any(keyword in item for keyword in class3_keywords) and (
                    '生产' in item or '制造' in item or '加工' in item):
                score = 5
                self._add_log(
                    'basic',score,
                     f'经营范围：{item}（3类生产），5分'
                )
                return score

            # 2. 检查二类生产
            elif any(keyword in item for keyword in class2_keywords) and (
                    '生产' in item or '制造' in item or '加工' in item):
                score = 4
                self._add_log(
                    'basic',score,
                     f'经营范围：{item}（二类生产），4分'
                )
                return score

            # 3. 检查3类销售/经营
            elif any(keyword in item for keyword in class3_keywords) and ('销售' in item or '经营' in item):
                score = 3
                self._add_log(
                    'basic',score,
                     f'经营范围：{item}（3类销售/经营），3分'
                )
                return score

            # 4. 检查二类销售/经营
            elif any(keyword in item for keyword in class2_keywords) and ('销售' in item or '经营' in item):
                score = 2
                self._add_log(
                    'basic',score,
                     f'经营范围：{item}（二类销售/经营），2分'
                )
                return score

            # 5. 检查一类销售/经营
            elif any(keyword in item for keyword in class1_keywords) and ('销售' in item or '经营' in item):
                score = 1
                self._add_log(
                    'basic',score,
                     f'经营范围：{item}（一类销售/经营），1分'
                )
                return score

        # 未匹配到任何有效项目
        score = 1
        self._add_log(
            'basic',score,
             '经营范围：无有效类别，1分'
        )
        return score

    def calculate_tax_rating(self):
        """计算纳税人等级得分"""
        score = 0
        if self.enterprise.tax_rating == 'A':
            score = 3
            self._add_log(
                'basic',score,
                 '纳税人等级：A级，3分'
            )
        else:
            score = 1
            self._add_log(
                'basic',score,
                 '纳税人等级：非A级，1分'
            )
        return score

    def calculate_tax_type(self):
        """计算纳税人类型得分"""
        score = 0
        if self.enterprise.tax_type == 1:
            score = 3
            self._add_log(
                'basic',score,
                 '纳税人类型：一般纳税人，3分'
            )
        else:
            score = 1
            self._add_log(
                'basic',score,
                 '纳税人类型：非一般纳税人，1分'
            )
        return score

    def calculate_funding_round(self):
        """计算投融资轮次得分"""
        score = 0
        if self.enterprise.funding_round is None or self.enterprise.funding_round=="无投融资信息":
            score = 1
            self._add_log(
                'basic',score,
                 '投融资轮次：未融资，1分'
            )
        else:
            if self.enterprise.funding_round in ['天使轮', 'A轮']:
                score = 4
                self._add_log(
                    'basic',score,
                     '投融资轮次：天使轮/A轮，4分'
                )
            elif self.enterprise.funding_round in ['B轮', '股权融资']:
                score = 5
                self._add_log(
                    'basic',score,
                     '投融资轮次：B轮/股权融资，5分'
                )
            elif self.enterprise.funding_round in ['C轮', '战略投资']:
                score = 6
                self._add_log(
                    'basic',score,
                     '投融资轮次：C轮/战略投资，6分'
                )
            elif self.enterprise.funding_round in ['D轮', 'E轮']:
                score = 8
                self._add_log(
                    'basic',score,
                     '投融资轮次：D/E轮，8分'
                )
            elif self.enterprise.funding_round in ['Pre-IPO', '已上市']:
                score = 10
                self._add_log(
                    'basic',score,
                     '投融资轮次：Pre-IPO/已上市，10分'
                )
            else:
                score = 1
                self._add_log(
                    'basic',score,
                     '投融资轮次：其他，1分'
                )
        return score

    def calculate_patent_type(self):
        """计算专利类型得分"""
        score = 0
        patents = self.enterprise.patents

        for patent in patents:
            pt = patent.get('patent_type')
            if pt == 'PCT':
                score += 4
            elif pt == 'Invention_Authorized': #发明授权
                score += 2
            elif pt == 'Invention_Publication': #发明公开
                score += 1
            elif pt in ["实质审查","实用新型","外观","商标"]:
                score += 0.5
            else:
                score += 0

        # 限制满分15分
        if score > 15:
            score = 15

        self._add_log(
            'basic',score,
             f'专利类型：{len(patents)}项专利，{score}分'
        )

        return score

    def calculate_software_copyright(self):
        """计算软件著作权得分"""
        score = 0
        copyrights = self.enterprise.software_copyrights

        score = len(copyrights)

        # 限制满分15分
        if score > 15:
            score = 15

        self._add_log(
            'basic',score,
             f'软件著作权：{len(copyrights)}项，{score}分'
        )

        return score

    def calculate_technology_enterprise(self):
        """计算科技型企业得分（支持多资质叠加，满分10分）"""
        score = 0
        descriptions = []

        # 累加各项资质得分
        if self.enterprise.is_specialized == 1:
            score += 8
            descriptions.append('专精特新')
        if self.enterprise.is_innovative == 1:
            score += 6
            descriptions.append('创新型企业')
        if self.enterprise.is_high_tech == 1:
            score += 4
            descriptions.append('高新企业')

        # 封顶10分，且至少0分（即使全无）
        if score == 0:
            final_score = 0
            desc_text = '无'
        else:
            final_score = min(score, 10)
            desc_text = '、'.join(descriptions)

        self._add_log(
            'basic',final_score,
             f'科技型企业：{desc_text}，{final_score}分'
        )

        return final_score

    # === 科技属性评分方法 ===
    def calculate_tech_score(self):
        score = 0.0

        def add(func, field_key):
            return func() * self._get_scale('tech', field_key)

        score += add(self.calculate_tech_patent_type, 'tech_patent_type')
        score += add(self.calculate_patent_tech_attribute, 'patent_tech_attribute')
        score += add(self.calculate_tech_software_copyright, 'tech_software_copyright')
        score += add(self.calculate_software_copyright_tech_attribute, 'software_copyright_tech_attribute')
        score += add(self.calculate_tech_technology_enterprise, 'tech_technology_enterprise')
        score += add(self.calculate_industry_university_research, 'industry_university_research')
        score += add(self.calculate_national_provincial_award, 'national_provincial_award')

        return max(score, 0)

    def calculate_tech_patent_type(self):
        """计算专利类型科技属性得分"""
        score = 0
        patents = self.enterprise.patents

        pct_count = sum(1 for p in patents if p['patent_type'] == 'PCT')
        # 统计发明授权 + 发明公开 的专利数量
        invention_count = sum(
                1 for p in patents
                if p['patent_type'] in ['Invention_Authorized', 'Invention_Publication']
            )

        if pct_count >= 5 or invention_count >= 20:
            score = 10
            self._add_log(
                'tech',score,
                 '专利类型：PCT专利5项以上或发明专利20个以上，10分'
            )
        elif (3 <= pct_count <= 5) or (10 <= invention_count <= 20):
            score = 8
            self._add_log(
                'tech',score,
                 '专利类型：PCT专利3-5项或发明专利10-20个，8分'
            )
        elif (1 <= pct_count <= 3) or (5 <= invention_count <= 10):
            score = 6
            self._add_log(
                'tech',score,
                 '专利类型：PCT专利1-3项或发明专利5-10个，6分'
            )
        elif 1 <= invention_count <= 5:
            score = 3
            self._add_log(
                'tech',score,
                 '专利类型：发明专利1-5个，3分'
            )
        else:
            # 没有发明/PCT，尝试计算其他类型加分（最多2分）
            other_types = {'Pending', 'Utility_Model', 'Design_Patent', 'Trademark'}  # 用 set 提升 in 查询效率
            other_count = sum(1 for p in patents if p.get('patent_type') in other_types)

            # 每项0.5分，上限2分 → 最多4项
            score = min(other_count * 0.5, 2.0)
            if score > 0:
                self._add_log(
                    'tech', score,
                    f'专利类型：实质审查/实用新型/外观/商标共{other_count}项，+{score}分（0.5分/项，满分2分）'
                )
            else:
                self._add_log(
                    'tech',0,
                     '专利类型：无任何专利或知识产权记录，0分'
                )

        return score

    def calculate_patent_tech_attribute(self):
        """计算专利科技属性得分"""
        score = 0
        tech_keywords = ['AI', '算法', '5G', '物联网', '传感器', '区块链', '机器人', '3D打印',
                         '人工智能', '人机交互', '基因', '基因技术', '生物', '生物技术',
                         '诊断', '体外诊断', 'IVD', '可穿戴', '医学影像']

        patents = self.enterprise.patents  # list of dict

        for patent in patents:
            name = patent.get('patent_name', '')
            if not name:
                continue
            for kw in tech_keywords:
                if kw in name:
                    score += 1
                    break

        # 限制满分20分
        if score > 20:
            score = 20

        self._add_log(
            'tech',score,
             f'专利科技属性：{score}分'
        )

        return score

    def calculate_tech_software_copyright(self):
        """计算软件著作权科技属性得分"""
        score = 0
        copyrights = self.enterprise.software_copyrights  # 直接是列表
        count = len(copyrights)

        if count >= 20:
            score = 10
            self._add_log(
                'tech',score,
                 '软件著作权：20个以上，10分'
            )
        elif 10 <= count < 20:
            score = 8
            self._add_log(
                'tech',score,
                 '软件著作权：10-20个，8分'
            )
        elif 5 <= count < 10:
            score = 6
            self._add_log(
                'tech',score,
                 '软件著作权：5-10个，6分'
            )
        elif 3 <= count < 5:
            score = 2
            self._add_log(
                'tech',score,
                 '软件著作权：3-5个，2分'
            )
        elif 1 <= count < 3:
            score = 1
            self._add_log(
                'tech',score,
                 '软件著作权：1-3个，1分'
            )
        else:
            score = 0
            self._add_log(
                'tech',score,
                 '软件著作权：无，0分'
            )

        return score

    def calculate_software_copyright_tech_attribute(self):
        """计算软著科技属性得分"""
        score = 0
        tech_keywords = [
            'AI', '算法', '5G', '物联网', '传感器', '区块链', '机器人', '3D打印',
            '人工智能', '人机交互', '基因', '基因技术', '生物', '生物技术',
            '诊断', '体外诊断', 'IVD', '可穿戴', '医学影像'
        ]

        for soft in self.enterprise.software_copyrights:
            name = soft.get('copyright_name') or ''
            if any(keyword in name for keyword in tech_keywords):
                score += 1

        # 限制满分20分
        if score > 20:
            score = 20

        self._add_log(
            'tech',score,
             f'软著科技属性：{score}分'
        )

        return score

    def calculate_professional_score(self):
        score = 0.0

        def add(func, field_key):
            return func() * self._get_scale('pro', field_key)

        score += add(self.calculate_industry_market_size, 'industry_market_size')
        score += add(self.calculate_industry_heat, 'industry_heat')
        score += add(self.calculate_industry_profit_margin, 'industry_profit_margin')
        score += add(self.calculate_qualification, 'qualification')
        score += add(self.calculate_certificates, 'certificates')
        score += add(self.calculate_innovation, 'innovation')
        score += add(self.calculate_partnership_score, 'partnership_score')
        score += add(self.calculate_ranking_score, 'ranking') # 请确保子函数名一致

        return max(score, 0)

    def calculate_tech_technology_enterprise(self):
        """计算科技型企业科技属性得分（支持多资质叠加，满分15分）"""
        score = 0

        descriptions = []

        # 累加各项资质得分
        if self.enterprise.is_specialized == 1:
            score += 8
            descriptions.append('专精特新')
        if self.enterprise.is_innovative == 1:
            score += 6
            descriptions.append('创新型企业')
        if self.enterprise.is_high_tech == 1:
            score += 4
            descriptions.append('高新企业')

        # 封顶10分，且至少1分（即使全无）
        if score == 0:
            final_score = 0
            desc_text = '无'
        else:
            final_score = min(score, 15)
            desc_text = '、'.join(descriptions)

        self._add_log(
            'tech', final_score,
            f'科技型企业：{desc_text}，{final_score}分'
        )

        return final_score



    def calculate_industry_university_research(self):
        """计算产学研合作得分"""
        '''
        score = 0
        # 实际应用中应从数据库查询产学研合作记录
        # 示例：检查是否有"产学研合作"关键词
        if '产学研合作' in self.enterprise.business_scope or '校企合作' in self.enterprise.business_scope:
            score = 5
            self._add_log(
                'tech',score,
                 '产学研合作：包含产学研/校企合作，5分'
            )
        else:
            score = 0
            self._add_log(
                'tech',score,
                 '产学研合作：无，0分'
            )
        '''
        score = 15
        return score

    def calculate_national_provincial_award(self):
        """计算国家/省级奖励得分"""
        score = 10
        # 实际应用中应检查是否有国家级/省级奖励
        # 示例：检查企业是否获得过省级以上科技奖励
        '''
        if self.enterprise.is_specialized or self.enterprise.is_innovative:
            score = 7
            self._add_log(
                'tech',score,
                 '国家/省级奖励：专精特新/创新型企业，7分'
            )
        else:
            score = 0
            self._add_log(
                'tech',score,
                 '国家/省级奖励：无，0分'
            )
            '''
        return score




    # === 专业能力评分方法 ===
    def calculate_professional_score(self):
        """计算专业能力评分"""
        score = 0

        # 1. 行业市场规模分值
        score += self.calculate_industry_market_size()

        # 2. 行业热度分值
        score += self.calculate_industry_heat()

        # 3. 行业利润率分值
        score += self.calculate_industry_profit_margin()

        # 4. 资质
        score += self.calculate_qualification()

        # 5. 证书
        score += self.calculate_certificates()

        # 6. 创新性
       # score += self.calculate_innovation()

        # 7. 合作上下游
        score += self.calculate_partnership_score()

        # 8. 专业榜单入选
        score += self.calculate_ranking_score()

        return score

    def calculate_industry_market_size(self):
        """计算行业市场规模得分（满分10分）"""
        industries = self.enterprise.industry
        if not industries :
            self._add_log('professional', 3, '行业市场规模：无行业分类数据，3分')
            return 3

        industry_str = industries[0].get('industry', '').strip()

        # 行业市场规模评分规则（按分值从高到低）
        rules = [
            # 10分：医药流通/零售
            (['医药流通', '医药零售'], 10, '医药流通/零售'),
            # 8分：CXO、医疗器械（高值耗材）
            (['CXO', '医疗器械（高值耗材）'], 8, 'CXO、医疗器械（高值耗材）'),
            # 7分：创新药/生物技术、医疗器械（设备）、医疗服务（民营医院）
            (['创新药', '生物技术', '医疗器械（设备）', '医疗服务（民营医院）'], 7,
             '创新药/生物技术、医疗器械（设备）、医疗服务（民营医院）'),
            # 6分：数字医疗/医疗信息化、中药、生物制品（疫苗）、医疗服务（第三方医学检验）
            (['数字医疗', '医疗信息化', '中药', '生物制品（疫苗）', '医疗服务（第三方医学检验）'], 6,
             '数字医疗/医疗信息化、中药、生物制品（疫苗）、医疗服务（第三方医学检验）'),
            # 5分：化学原料药、生物制品（血制品）
            (['化学原料药', '生物制品（血制品）'], 5, '化学原料药、生物制品（血制品）'),
            # 4分：医疗AI
            (['医疗AI'], 4, '医疗AI'),
            # 3分：其他
            ([], 3, '其他')
        ]

        # 按规则顺序匹配
        for keywords, score, reason in rules:
            if any(kw in industry_str for kw in keywords):
                self._add_log('professional', score, f'行业市场规模：{industry_str} -> {reason}，{score}分')
                return score

        # 如果没有匹配任何规则，返回默认3分
        self._add_log('professional', 3, f'行业市场规模：{industry_str} -> 其他，3分')
        return 3

    def calculate_industry_heat(self):
        """计算行业热度得分（满分10分）"""
        industries = self.enterprise.industry
        if not industries :
            self._add_log('professional', 3, '行业热度：无行业分类数据，3分')
            return 3

        industry_str = industries[0].get('industry', '').strip()

        # 行业热度评分规则（按分值从高到低）
        rules = [
            # 9分：创新药/生物技术、医疗AI
            (['创新药', '生物技术', '医疗AI'], 9, '创新药/生物技术、医疗AI'),
            # 8分：数字医疗/医疗信息化
            (['数字医疗', '医疗信息化'], 8, '数字医疗/医疗信息化'),
            # 7分：医疗器械（高值耗材）
            (['医疗器械（高值耗材）'], 7, '医疗器械（高值耗材）'),
            # 6分：CXO、医疗器械（设备）
            (['CXO', '医疗器械（设备）'], 6, 'CXO、医疗器械（设备）'),
            # 5分：中药、生物制品（疫苗）、医疗服务（民营医院）
            (['中药', '生物制品（疫苗）', '医疗服务（民营医院）'], 5, '中药、生物制品（疫苗）、医疗服务（民营医院）'),
            # 4分：化学原料药、生物制品（血制品）、医疗服务（第三方医学检验）、医药流通/零售
            (['化学原料药', '生物制品（血制品）', '医疗服务（第三方医学检验）', '医药流通', '医药零售'], 4,
             '化学原料药、生物制品（血制品）、医疗服务（第三方医学检验）、医药流通/零售'),
            # 3分：其他
            ([], 3, '其他')
        ]

        # 按规则顺序匹配
        for keywords, score, reason in rules:
            if any(kw in industry_str for kw in keywords):
                self._add_log('professional', score, f'行业热度：{industry_str} -> {reason}，{score}分')
                return score+1

        # 如果没有匹配任何规则，返回默认3分
        self._add_log('professional', 3, f'行业热度：{industry_str} -> 其他，3分')
        return 3

    def calculate_industry_profit_margin(self):
        """计算行业利润率得分（满分10分）"""
        industries = self.enterprise.industry
        if not industries :
            self._add_log('professional', 3, '行业利润率：无行业分类数据，3分')
            return 3

        industry_str = industries[0].get('industry', '').strip()

        # 行业利润率评分规则（按分值从高到低）
        rules = [
            # 9分：生物制品（血制品）
            (['生物制品（血制品）'], 9, '生物制品（血制品）'),
            # 8分：医疗器械（高值耗材）、生物制品（疫苗）、中药
            (['医疗器械（高值耗材）', '生物制品（疫苗）', '中药'], 8, '医疗器械（高值耗材）、生物制品（疫苗）、中药'),
            # 7分：CXO、医疗器械（设备）
            (['CXO', '医疗器械（设备）'], 7, 'CXO、医疗器械（设备）'),
            # 6分：医疗服务（民营医院）
            (['医疗服务（民营医院）'], 6, '医疗服务（民营医院）'),
            # 5分：创新药/生物技术、化学原料药、医疗服务（第三方医学检验）
            (['创新药', '生物技术', '化学原料药', '医疗服务（第三方医学检验）'], 5,
             '创新药/生物技术、化学原料药、医疗服务（第三方医学检验）'),
            # 4分：数字医疗/医疗信息化
            (['数字医疗', '医疗信息化'], 4, '数字医疗/医疗信息化'),
            # 3分：医疗AI、医药流通/零售
            (['医疗AI', '医药流通', '医药零售'], 3, '医疗AI、医药流通/零售'),
            # 2分：其他
            ([], 2, '其他')
        ]

        # 按规则顺序匹配
        for keywords, score, reason in rules:
            if any(kw in industry_str for kw in keywords):
                self._add_log('professional', score, f'行业利润率：{industry_str} -> {reason}，{score}分')
                return score+1

        # 如果没有匹配任何规则，返回默认2分
        self._add_log('professional', 2, f'行业利润率：{industry_str} -> 其他，2分')
        return 2

    def calculate_qualification(self):
        """
        计算“资质”得分（满分20分）
        规则涵盖生产许可、经营许可、体系认证等，未明确列出的计入“其他”加0.5分。
        """
        certificates_data = self.enterprise.certificates
        score = 0.0

        for item in certificates_data:
            cert_name = str(item.get('certificate_name')  or '').strip().upper()
            cert_type = str(item.get('certificate_type') or '').strip().upper()
            combined_text = f"{cert_name} {cert_type}"

            # --- 排他逻辑 ---
            # 如果当前记录已经被计入“证书”得分，则直接跳过，防止被计入最下方的“其他：+0.5分”
            is_certificate = (
                    ('药品' in combined_text and '注册' in combined_text) or
                    ('器械' in combined_text and '注册' in combined_text) or
                    ('临床' in combined_text) or
                    any(k in combined_text for k in ['受理', '在审', '原料', '辅料', '包材', '原辅包']) or
                    ('器械' in combined_text and '产品' in combined_text and '备案' in combined_text)
            )
            if is_certificate:
                continue

            # --- 资质匹配逻辑（由高分到低分判断） ---
            # 5分项
            if '药品' in combined_text and '生产' in combined_text and '许可' in combined_text:
                score += 5.0
            elif '器械' in combined_text and '生产' in combined_text and '许可' in combined_text:
                score += 5.0
            elif 'GMP' in combined_text:
                score += 5.0
            elif '深度合成' in combined_text and '算法' in combined_text:
                score += 5.0
            # 3分项
            elif '实验动物' in combined_text:
                score += 3.0
            elif '病原微生物' in combined_text:
                score += 3.0
            elif '互联网药品信息' in combined_text:
                score += 3.0
            elif '网络信息服务备案' in combined_text:
                score += 3.0
            # 2分项
            elif '辐射安全' in combined_text:
                score += 2.0
            elif '核辐射' in combined_text:
                score += 2.0
            elif '器械' in combined_text and '经营' in combined_text:
                # 这里会同时包揽你数据中的“医疗器械经营企业（许可）”和“医疗器械经营企业（备案）”
                score += 2.0
            elif '电信' in combined_text and '许可' in combined_text:
                score += 2.0
            elif '监控化学品' in combined_text:
                score += 2.0
            elif '中药提取物' in combined_text:
                score += 2.0
            # 1分项
            elif '器械' in combined_text and '生产' in combined_text and '备案' in combined_text:
                score += 1.0
            elif '出口证书' in combined_text:
                score += 1.0
            elif '质量管理' in combined_text or 'ISO9001' in combined_text:
                score += 1.0
            elif '环境管理' in combined_text or 'ISO14001' in combined_text:
                score += 1.0
            elif '职业健康' in combined_text or 'ISO45001' in combined_text:
                score += 1.0
            # 其他项：0.5分
            # 你数据中的“排污登记信息”、“食品经营许可证”、“仅销售预包装食品备案”、“高新技术企业”等，都会落到这里
            else:
                score += 0.5

        # 返回最高不超过20分
        return min(score, 20.0)

    def calculate_certificates(self):
        """
        计算“证书”得分（满分20分）
        规则：药品/器械注册证10分/项；临床批件5分/项；受理/在审/辅料等3分/项；医疗器械产品备案1分/项。
        """
        certificates_data = self.enterprise.certificates
        score = 0.0

        for item in certificates_data:
            # 兼容字典键的拼写错误 (certificate_name)
            cert_name = str(item.get('certificate_name')  or '').strip().upper()
            cert_type = str(item.get('certificate_type') or '').strip().upper()
            # 将名称和类型拼接，防止关键字拆分在不同字段
            combined_text = f"{cert_name} {cert_type}"

            # 1. 药品注册证 / 器械注册证: 10分/项
            if ('药品' in combined_text and '注册' in combined_text) or \
                    ('器械' in combined_text and '注册' in combined_text):
                score += 10.0
                continue

            # 2. 临床批件 (数据中可能体现为“药物临床试验”等): 5分/项
            if '临床' in combined_text or '临床批件' in combined_text:
                score += 5.0
                continue

            # 3. 受理品种、在审品种、在审公示、受理公示、原料、辅料、包材、原辅包登记: 3分/项
            if any(k in combined_text for k in ['受理', '在审', '原料', '辅料', '包材', '原辅包']):
                score += 3.0
                continue

            # 4. 医疗器械产品备案: 1分/项
            # 必须包含“产品”或明确排除“生产/经营”，以避免和资质体系混淆
            if '器械' in combined_text and '产品' in combined_text and '备案' in combined_text:
                score += 1.0
                continue

        # 返回最高不超过20分
        return min(score, 20.0)

    def calculate_innovation(self):
        """计算创新性得分"""
        score = 0
        # 检查创新性指标
        if self.enterprise.is_specialized or self.enterprise.is_innovative:
            score = 8
            self._add_log(
                'professional',score,
                 '创新性：专精特新/创新型企业，8分'
            )
        elif self.enterprise.is_high_tech:
            score = 5
            self._add_log(
                'professional',score,
                 '创新性：高新企业，5分'
            )
        else:
            score = 2
            self._add_log(
                'professional',score,
                 '创新性：普通企业，2分'
            )
        return score

    def calculate_partnership_score(self):
        """
        计算“合作上下游”得分（满分10分）
        规则：客户 0.5分/个；供应商 0.5分/个
        """
        # 1. 获取原始数据
        clients_data = self.enterprise.client
        suppliers_data = self.enterprise.supplier

        # 2. 清洗数据（排除掉 client_name 或 supplier_name 为空的情况）
        client_list = [c for c in clients_data if c.get('client_name')]
        supplier_list = [s for s in suppliers_data if s.get('supplier_name')]

        client_count = len(client_list)
        supplier_count = len(supplier_list)

        # 3. 计算分数
        raw_score = (client_count * 0.5) + (supplier_count * 0.5)

        # 限制最高分为10分
        score = min(raw_score, 10.0)

        # 4. 记录日志
        if score == 0:
            description = "上下游合作：未获取到有效的客户或供应商信息，0分"
        else:
            description = (
                f"上下游合作：有效客户{client_count}个({client_count * 0.5}分)，"
                f"有效供应商{supplier_count}个({supplier_count * 0.5}分)。"
            )
            if raw_score > 10:
                description += f" 原始总计{raw_score}分，触发上限，计10分"
            else:
                description += f" 总计{score}分"

        self._add_log('professional', score, description)
        return score

    def calculate_ranking_score(self):
        """
        计算“专业榜单入选”得分（满分10分）
        规则：上榜榜单 +1分/个
        """
        # 1. 获取原始数据
        awards_data = self.enterprise.awardRanking

        # 2. 清洗数据（排除 award_name 为空的情况）
        valid_awards = [a for a in awards_data if a.get('award_name')]
        award_count = len(valid_awards)

        # 3. 计算分数
        raw_score = award_count * 1.0

        # 限制最高分为10分
        score = min(raw_score, 10.0)

        # 4. 记录日志
        if score == 0:
            description = "专业榜单入选：未获取到上榜信息，0分"
        else:
            description = f"专业榜单入选：入选{award_count}个榜单。"
            if raw_score > 10:
                description += f" 原始总计{raw_score}分，触发上限，计10分"
            else:
                description += f" 总计{score}分"

        self._add_log('professional', score, description)
        return score



