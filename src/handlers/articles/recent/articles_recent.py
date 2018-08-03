# -*- coding: utf-8 -*-
import json
import settings
from lambda_base import LambdaBase
from jsonschema import validate
from decimal_encoder import DecimalEncoder
from parameter_util import ParameterUtil
from es_util import ESUtil


class ArticlesRecent(LambdaBase):
    def get_schema(self):
        return {
            'type': 'object',
            'properties': {
                'limit': settings.parameters['limit'],
                'article_id': settings.parameters['article_id'],
                'sort_key': settings.parameters['sort_key'],
                'page': settings.parameters['page'],
                'topic': settings.parameters['topic']
            }
        }

    def validate_params(self):
        ParameterUtil.cast_parameter_to_int(self.params, self.get_schema())

        validate(self.params, self.get_schema())

    def exec_main_proc(self):
        limit = int(self.params.get('limit')) if self.params.get('limit') is not None \
            else settings.article_recent_default_limit
        page = int(self.params.get('page')) if self.params.get('page') is not None else 1

        topic = self.params.get('topic')

        params = {}
        if topic:
            params.update({'topic': topic})
        if self.params.get('article_id') is not None and self.params.get('sort_key') is not None:
            params.update({
                'article_id': self.params.get('article_id'),
                'sort_key': self.params.get('sort_key')
            })

        results = ESUtil.search_recent_articles(self.elasticsearch, params, limit, page)

        articles = []
        for item in results['hits']['hits']:
            articles.append(item['_source'])

        response = {
            'Items': articles
        }

        return {
            'statusCode': 200,
            'body': json.dumps(response, cls=DecimalEncoder)
        }
