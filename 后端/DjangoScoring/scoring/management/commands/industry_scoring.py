# scoring/management/commands/industry_scoring.py

import pandas as pd
from sqlalchemy import create_engine, String, Integer, Numeric, SmallInteger
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = '计算各行业路径的平均得分并写入数据库表 industry_path_score'

    def handle(self, *args, **options):
        # ==============================
        # 1. 数据库连接（推荐使用 Django 的 DATABASES 配置）
        # ==============================
        db = settings.DATABASES['default']
        DB_USER = db['USER']
        DB_PASSWORD = db['PASSWORD']
        DB_HOST = db['HOST'] or 'localhost'
        DB_PORT = db['PORT'] or '3306'
        DB_NAME = db['NAME']

        engine = create_engine(
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )

        # ==============================
        # 2. 读取数据
        # ==============================
        scoring_df = pd.read_sql("SELECT id, total_score FROM scoring_scoreresult", con=engine)
        industry_df = pd.read_sql("SELECT id, `分类` FROM `行业分类`", con=engine)

        merged = pd.merge(scoring_df, industry_df, on='id', how='inner')

        # ==============================
        # 3. 生成所有前缀路径
        # ==============================
        records = []
        for _, row in merged.iterrows():
            score = row['total_score']
            full_path_str = row['分类']
            if not isinstance(full_path_str, str):
                continue
            tags = full_path_str.split('/')
            for i in range(len(tags)):
                prefix_path = '/'.join(tags[:i + 1])
                records.append({
                    '企业id': row['id'],
                    '总分': score,
                    'industry_path': prefix_path,
                    'path_level': i
                })

        if not records:
            self.stdout.write(self.style.WARNING("⚠️ 无有效行业分类数据"))
            return

        path_df = pd.DataFrame(records)

        # ==============================
        # 4. 聚合计算
        # ==============================
        agg_df = path_df.groupby(['industry_path', 'path_level'])['总分'].agg(
            avg_score='mean',
            company_count='size'
        ).reset_index()

        agg_df['avg_score'] = agg_df['avg_score'].round(2)
        agg_df['company_count'] = agg_df['company_count'].astype(int)
        agg_df = agg_df.sort_values(['path_level', 'industry_path']).reset_index(drop=True)

        # ==============================
        # 5. 写入数据库
        # ==============================
        agg_df.to_sql(
            name='industry_path_score',
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

        self.stdout.write(
            self.style.SUCCESS(f"✅ 成功写入 {len(agg_df)} 条行业路径得分到 industry_path_score 表")
        )
        self.stdout.write("预览前5条：")
        for _, row in agg_df.head().iterrows():
            self.stdout.write(f"  {row['industry_path']} (level {row['path_level']}): {row['avg_score']}")