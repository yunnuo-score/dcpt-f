# your_app/management/commands/run_scoring.py

import pandas as pd
import threading
from sqlalchemy import create_engine, String, Integer, Numeric, SmallInteger
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from scoring.scoring import ScoringCalculator
from sqlalchemy import text


class Command(BaseCommand):
    help = '合并任务：1. 对全量企业进行评分；2. 计算行业路径平均得分'

    def handle(self, *args, **options):
        # ==========================================
        # 阶段一：全量企业评分 (Scoring Phase)
        # ==========================================
        self.stdout.write(self.style.MIGRATE_HEADING(">>> 正在启动阶段一：全量企业评分..."))

        # 1. 获取企业ID列表
        with connection.cursor() as cursor:
            # 确保表名与数据库一致，如果是 Django 模型生成的通常是 scoring_enterprise
            cursor.execute("SELECT id FROM 企业基本信息")
            enterprise_ids = [row[0] for row in cursor.fetchall()]

        total = len(enterprise_ids)
        self.stdout.write(f'开始对 {total} 家企业进行评分...')

        for i, eid in enumerate(enterprise_ids, 1):
            try:
                calculator = ScoringCalculator(enterprise_id=eid)
                # 执行计算并保存到数据库 (ScoringCalculator 内部应处理 save 逻辑)
                total_score = calculator.calculate_all_scores()

                # 动态显示进度
                if i % 10 == 0 or i == total:
                    self.stdout.write(f"进度: [{i}/{total}] 已完成...")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'ID={eid} 评分失败: {str(e)}'))

        self.stdout.write(self.style.SUCCESS("✅ 阶段一：全量企业评分完成！\n"))

        # ==========================================
        # 阶段二：行业路径聚合 (Aggregation Phase)
        # ==========================================
        self.stdout.write(self.style.MIGRATE_HEADING(">>> 正在启动阶段二：计算行业路径得分..."))

        db_config = settings.DATABASES['default']
        engine = create_engine(
            f"mysql+pymysql://{db_config['USER']}:{db_config['PASSWORD']}@"
            f"{db_config['HOST'] or 'localhost'}:{db_config['PORT'] or '3306'}/{db_config['NAME']}"
        )

        try:
            # 1. 读取刚更新好的评分数据和行业数据
            scoring_df = pd.read_sql("SELECT enterprise_id, total_score FROM scoring_scoreresult", con=engine)
            industry_df = pd.read_sql("SELECT id, `分类` FROM `行业分类`", con=engine)

            if scoring_df.empty or industry_df.empty:
                self.stdout.write(self.style.WARNING("⚠️ 评分表或行业分类表为空，跳过阶段二。"))
                return

            merged = pd.merge(scoring_df, industry_df, left_on='enterprise_id', right_on='id', how='inner')

            # 2. 生成前缀路径逻辑
            records = []
            for _, row in merged.iterrows():
                score = row['total_score']
                full_path_str = row['分类']
                if not isinstance(full_path_str, str) or not full_path_str:
                    continue

                tags = full_path_str.split('/')
                for j in range(len(tags)):
                    prefix_path = '/'.join(tags[:j + 1])
                    records.append({
                        'industry_path': prefix_path,
                        'path_level': j,
                        'total_score': score
                    })

            if not records:
                self.stdout.write(self.style.WARNING("⚠️ 处理后无有效记录"))
                return

            path_df = pd.DataFrame(records)

            # 3. 聚合计算
            agg_df = path_df.groupby(['industry_path', 'path_level'])['total_score'].agg(
                avg_score='mean',
                company_count='size'
            ).reset_index()

            agg_df['avg_score'] = agg_df['avg_score'].round(2)
            agg_df = agg_df.sort_values(['path_level', 'industry_path']).reset_index(drop=True)

            # 4. 写入数据库
            agg_df.to_sql(
                name='score_industry_path',
                con=engine,
                if_exists='replace',
                index=False,
                dtype={
                    'industry_path': String(255),
                    'path_level': SmallInteger,
                    'avg_score': Numeric(5, 2),
                    'company_count': Integer
                }
            )

            # 2. 写入完成后，手动修改列为非空并添加主键
            with engine.connect() as conn:
                # 注意：某些数据库（如 MySQL）要求主键列必须显式设为 NOT NULL
                conn.execute(text("ALTER TABLE score_industry_path MODIFY industry_path VARCHAR(255) NOT NULL;"))
                conn.execute(text("ALTER TABLE score_industry_path ADD PRIMARY KEY (industry_path);"))
                conn.commit()

            self.stdout.write(self.style.SUCCESS(f"✅ 阶段二：成功汇总 {len(agg_df)} 条行业得分！"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 阶段二执行出错: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("\n🎉 所有评分与汇总任务已全部执行完毕！"))