from django.shortcuts import render

# Create your views here.
# views.py
import json
from django.http import JsonResponse
from django.db import connection


def build_tree(paths):
    """将扁平路径列表转为嵌套树"""
    root = {}
    for item in paths:
        parts = item['industry_path'].split('/')
        current = root
        for i, part in enumerate(parts):
            if part not in current:
                current[part] = {
                    'name': part,
                    'value': None,
                    'children': {},
                    'path_level': i
                }
            current = current[part]['children']
        # 叶子节点才赋值（或根据需求调整）
        parent = root
        for part in parts[:-1]:
            parent = parent[part]['children']
        leaf = parent[parts[-1]]
        leaf['value'] = float(item['avg_score'])
        leaf['company_count'] = item['company_count']

    # 转为列表格式
    def dict_to_list(d):
        result = []
        for key, node in d.items():
            children_list = dict_to_list(node['children']) if node['children'] else []
            result.append({
                'name': node['name'],
                'value': node['value'],
                'children': children_list,
                'company_count': node.get('company_count', 0)
            })
        return result

    return dict_to_list(root)


def get_industry_tree(request):
    with connection.cursor() as cursor:
        cursor.execute("""
                       SELECT industry_path, path_level, avg_score, company_count
                       FROM score_industry_path
                       ORDER BY industry_path
                       """)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    tree_data = build_tree(results)
    return JsonResponse(tree_data, safe=False)