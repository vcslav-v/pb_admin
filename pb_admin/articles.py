from requests import Session
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas, _image_tools as image_tools, _config as config
from loguru import logger
import json
from requests_toolbelt import MultipartEncoder
import uuid
from datetime import datetime


class Articles():
    def __init__(self, session: Session, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    def get_list(self, search: str = None) -> list[schemas.Article]:
        articles = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search or '',
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/articles', params=params)
            resp.raise_for_status()
            raw_page = resp.json()
            values = {}
            for row in raw_page['resources']:
                for raw_article_field in row['fields']:
                    if raw_article_field['attribute'] == 'author':
                        values[raw_article_field['attribute']] = raw_article_field['belongsToId']
                    else:
                        values[raw_article_field['attribute']] = raw_article_field['value']
                articles.append(
                    schemas.Article(
                        ident=values.get('id'),
                        created_at=datetime.fromisoformat(values.get('created_at')),
                        title=values.get('title'),
                        slug=values.get('slug'),
                        is_live=True if values.get('status') == 'Live' else False,
                        is_sponsored=values.get('sponsored'),
                        show_statistic=values.get('show_stats'),
                        count_views=values.get('count_views'),
                        author=values.get('author'),
                    )
                )

            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))

            else:
                is_next_page = False

        return articles

    def get(self, article_ident: int) -> schemas.Article:
        resp = self.session.get(f'{self.site_url}/nova-api/articles/{article_ident}')
        resp.raise_for_status()
        raw_article = resp.json()
        raw_article_fields = raw_article['resource']['fields']
        values = {}
        for raw_article_field in raw_article_fields:
            if raw_article_field['attribute'] == 'author':
                values[raw_article_field['attribute']] = raw_article_field['belongsToId']
            else:
                values[raw_article_field['attribute']] = raw_article_field['value']
        if values.get('options'):
            meta_title = values['options'].get('meta_title')
            meta_description = values['options'].get('meta_description')
            meta_keywords = values['options'].get('meta_keywords')
        else:
            meta_title = None
            meta_description = None
            meta_keywords = None

        categories_resp = self.session.get(
            f'{self.site_url}/nova-vendor/nova-attach-many/articles/{values["id"]}/attachable/categories'
        )
        raw_categoies = categories_resp.json()
        categories_ids = list(set(raw_categoies['selected']))

        return schemas.Article(
            ident=values.get('id'),
            created_at=datetime.fromisoformat(values.get('created_at')),
            title=values.get('title'),
            slug=values.get('slug'),
            is_live=True if values.get('status') == 'Live' else False,
            is_sponsored=values.get('sponsored'),
            show_statistic=values.get('show_stats'),
            count_views=values.get('count_views'),
            author_id=values.get('author'),
            short_description=values.get('short_description'),
            thumbnail=schemas.Image(
                ident=values['material_image'][0]['id'],
                mime_type=values['material_image'][0]['mime_type'],
                original_url=values['material_image'][0]['original_url'],
                file_name=values['material_image'][0]['file_name'],
                alt=values['material_image'][0]['custom_properties'].get('alt') if values['material_image'][0]['custom_properties'] else None,
            ) if values.get('material_image') else None,
            thumbnail_retina=schemas.Image(
                ident=values['material_image_retina'][0]['id'],
                mime_type=values['material_image_retina'][0]['mime_type'],
                original_url=values['material_image_retina'][0]['original_url'],
                file_name=values['material_image_retina'][0]['file_name'],
                alt=values['material_image_retina'][0]['custom_properties'].get('alt') if values['material_image_retina'][0]['custom_properties'] else None,
            ) if values.get('material_image_retina') else None,
            push_image=schemas.Image(
                ident=values['push_image'][0]['id'],
                mime_type=values['push_image'][0]['mime_type'],
                original_url=values['push_image'][0]['original_url'],
                file_name=values['push_image'][0]['file_name'],
                alt=values['push_image'][0]['custom_properties'].get('alt') if values['push_image'][0]['custom_properties'] else None,
            ) if values.get('push_image') else None,
            main_image=schemas.Image(
                ident=values['article_main'][0]['id'],
                mime_type=values['article_main'][0]['mime_type'],
                original_url=values['article_main'][0]['original_url'],
                file_name=values['article_main'][0]['file_name'],
                alt=values['article_main'][0]['custom_properties'].get('alt') if values['article_main'][0]['custom_properties'] else None,
            ) if values.get('article_main') else None,
            main_image_retina=schemas.Image(
                ident=values['article_main_retina'][0]['id'],
                mime_type=values['article_main_retina'][0]['mime_type'],
                original_url=values['article_main_retina'][0]['original_url'],
                file_name=values['article_main_retina'][0]['file_name'],
                alt=values['article_main_retina'][0]['custom_properties'].get('alt') if values['article_main_retina'][0]['custom_properties'] else None,
            ) if values.get('article_main_retina') else None,
            meta_title=meta_title,
            meta_description=meta_description,
            meta_keywords=meta_keywords,
            category_ids=categories_ids,
            content=[self.get_article_block(block) for block in values['content']] if values.get('content') else [],
        )

    def update(self, article: schemas.Article, is_lite: bool = True) -> schemas.Article:
        if not self.edit_mode:
            raise ValueError('Edit mode is required')
        if not article.ident:
            raise ValueError('Article id is required')
        boundary = str(uuid.uuid4())
        article = self._prepare_imgs(article)
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-XSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-Requested-With': 'XMLHttpRequest',
        }
        params = {'editing': 'true', 'editMode': 'update'}
        fields = {
                'title': article.title,
                'created_at': article.created_at.strftime("%Y-%m-%d") if article.created_at else None,
                'slug': article.slug,
                'status': '1' if article.is_live else '0',
                'sponsored': '1' if article.is_sponsored else '0',
                'show_stats': '1' if article.show_statistic else '0',
                'short_description': article.short_description,
                'count_views': str(article.count_views) if article.count_views else None,
                'author': str(article.author_id) if article.author_id else None,
                'categories': str(article.category_ids),
                'options[meta_title]': article.meta_title,
                'options[meta_description]': article.meta_description,
                'options[meta_keywords]': article.meta_keywords,
                'content': json.dumps([self._render_article_block(block) for block in article.content]),
                '___nova_flexible_content_fields': '["content"]',
                'author_trashed': 'false',
                '_method': 'PUT',
                '_retrieved_at': str(int(datetime.now().timestamp())),
            }
        if article.thumbnail:
            fields['__media__[material_image][0]'] = image_tools.make_img_field(article.thumbnail)
        if article.thumbnail_retina:
            fields['__media__[material_image_retina][0]'] = image_tools.make_img_field(article.thumbnail_retina)
        if article.push_image:
            fields['__media__[push_image][0]'] = image_tools.make_img_field(article.push_image)
        if article.main_image:
            fields['__media__[article_main][0]'] = image_tools.make_img_field(article.main_image)
        if article.main_image_retina:
            fields['__media__[article_main_retina][0]'] = image_tools.make_img_field(article.main_image_retina)

        form = MultipartEncoder(fields, boundary=boundary)
        resp = self.session.post(
            f'{self.site_url}/nova-api/articles/{article.ident}',
            headers=headers,
            data=form.to_string(),
            params=params,
            allow_redirects=False,
        )
        resp.raise_for_status()
        if is_lite:
            return
        return self.get(article.ident)

    @staticmethod
    def get_article_block(
        data: dict
    ) -> schemas.ArticleText:
        article_type = schemas.ArticleType(data['layout'])
        if article_type == schemas.ArticleType.text:
            result = schemas.ArticleText(
                layout=article_type,
                key=data['key'],
                value=data['attributes'][0]['value'] or '',
            )
        elif article_type == schemas.ArticleType.card:
            result = schemas.ArticleCard(
                layout=article_type,
                key=data['key'],
            )
            for attr in data['attributes']:
                if attr['attribute'] == 'title':
                    result.title = attr['value']
                elif attr['attribute'] == 'description':
                    result.description = attr['value']
                elif attr['attribute'] == 'button_text':
                    result.button_text = attr['value']
                elif attr['attribute'] == 'link_url':
                    result.link_url = attr['value']
                elif attr['attribute'] == 'link_text':
                    result.link_text = attr['value']
        elif article_type == schemas.ArticleType.video:
            result = schemas.ArticleVideo(
                layout=article_type,
                key=data['key'],
            )
            for attr in data['attributes']:
                if attr['attribute'] == 'title':
                    result.title = attr['value']
                elif attr['attribute'] == 'link':
                    result.link = attr['value']
        elif article_type == schemas.ArticleType.quote:
            result = schemas.ArticleQuote(
                layout=article_type,
                key=data['key'],
            )
            for attr in data['attributes']:
                if attr['attribute'] == 'text':
                    result.text = attr['value']
                elif attr['attribute'] == 'link_text':
                    result.link_text = attr['value']
                elif attr['attribute'] == 'author_link':
                    result.author_link = attr['value']
                elif attr['attribute'] == 'author_job':
                    result.author_job = attr['value']
        elif article_type == schemas.ArticleType.image:
            result = schemas.ArticleImage(
                layout=article_type,
                key=data['key'],
            )
            for attr in data['attributes']:
                if attr['attribute'] == 'image_link':
                    result.image_link = attr['value']
                elif attr['attribute'] == 'in_new_tab':
                    result.in_new_tab = attr['value']
                elif attr['attribute'] == 'nofollow':
                    result.nofollow = attr['value']
                elif attr['attribute'] == 'image_alt':
                    result.image_alt = attr['value']
                elif attr['attribute'] == 'image_title':
                    result.image_title = attr['value']
        return result

    @staticmethod
    def _render_article_block(block: schemas.ArticleText) -> dict:
        if block.layout == schemas.ArticleType.text:
            return {
                'layout': block.layout.value,
                'key': block.key,
                'attributes': {
                    f'{block.key}__text': block.value or '',
                }
            }
        elif block.layout == schemas.ArticleType.card:
            return {
                'layout': block.layout.value,
                'key': block.key,
                'attributes': {
                    f'{block.key}__title': block.title or '',
                    f'{block.key}__description': block.description or '',
                    f'{block.key}__button_text': block.button_text or '',
                    f'{block.key}__link_url': block.link_url or '',
                    f'{block.key}__link_text': block.link_text or '',
                }
            }
        elif block.layout == schemas.ArticleType.video:
            return {
                'layout': block.layout.value,
                'key': block.key,
                'attributes': {
                    f'{block.key}__title': block.title or '',
                    f'{block.key}__link': block.link or '',
                }
            }
        elif block.layout == schemas.ArticleType.quote:
            return {
                'layout': block.layout.value,
                'key': block.key,
                'attributes': {
                    f'{block.key}__text': block.text or '',
                    f'{block.key}__link_text': block.link_text or '',
                    f'{block.key}__author_link': block.author_link or '',
                    f'{block.key}__author_job': block.author_job or '',
                }
            }
        elif block.layout == schemas.ArticleType.image:
            return {
                'layout': block.layout.value,
                'key': block.key,
                'attributes': {
                    f'{block.key}__image_link': block.image_link or '',
                    f'{block.key}__in_new_tab': '1' if block.in_new_tab else '0',
                    f'{block.key}__nofollow': '1' if block.nofollow else '0',
                    f'{block.key}__image_alt': block.image_alt or '',
                    f'{block.key}__image_title': block.image_title or '',
                }
            }
    # @staticmethod
    def _prepare_imgs(self, article: schemas.Article) -> schemas.Article:
        article.thumbnail = image_tools.prepare_image(article.thumbnail, session=self.session) if article.thumbnail else None
        article.thumbnail_retina = image_tools.prepare_image(article.thumbnail_retina, session=self.session) if article.thumbnail_retina else None
        article.push_image = image_tools.prepare_image(article.push_image, session=self.session) if article.push_image else None
        article.main_image = image_tools.prepare_image(article.main_image, session=self.session) if article.main_image else None
        article.main_image_retina = image_tools.prepare_image(article.main_image_retina, session=self.session) if article.main_image_retina else None
        return article