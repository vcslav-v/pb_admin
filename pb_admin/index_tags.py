import string
import secrets

from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
from loguru import logger
from requests_toolbelt import MultipartEncoder
import uuid
from datetime import datetime
import json


class IndexTags():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get_list(self, search: str = None, limit: int | None = None) -> list[schemas.IndexTag]:
        """Get list of all tags in short version id, name, title, description, meta_title, meta_description, no_index."""
        tags = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search or '',
        }
        while is_next_page and (limit is None or len(tags) < limit):
            async with self.session.get(f'{self.site_url}/nova-api/index-tags', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()

                for row in raw_page['resources']:
                    values = {}
                    for cell in row['fields']:
                        if cell['attribute'] == 'category':
                            values['category_id'] = cell['belongsToId']
                        else:
                            values[cell['attribute']] = cell['value']

                    tags.append(
                        schemas.IndexTag(
                            ident=values.get('id'),
                            title=values.get('title'),
                            weight=values.get('weight'),
                            no_index=values.get('no_index'),
                            category_id=values.get('category_id'),
                        )
                    )

                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))

                else:
                    is_next_page = False

        return tags

    async def get(self, tag_ident: int) -> schemas.IndexTag:
        """Get tag by id."""
        async with self.session.get(f'{self.site_url}/nova-api/index-tags/{tag_ident}') as resp:
            resp.raise_for_status()
            raw_tag = await resp.json()
            raw_tag_fields = raw_tag['resource']['fields']
            values = {}
            for raw_tag_field in raw_tag_fields:
                if raw_tag_field['attribute'] == 'category':
                    values['category_id'] = raw_tag_field['belongsToId']
                elif raw_tag_field['attribute'] == 'options__faq':
                    values['faq'] = []
                    for option in raw_tag_field['value']:
                        _question = {}
                        for attr in option['attributes']:
                            if attr['attribute'] == 'title':
                                _question['question'] = attr['value']
                            elif attr['attribute'] == 'description':
                                _question['answer'] = attr['value']
                        values['faq'].append(schemas.FAQItem(
                            key=option['key'],
                            question=_question.get('question', ''),
                            answer=_question.get('answer', '')
                        ))
                elif raw_tag_field['attribute'] == 'options':
                    for option in raw_tag_field['value']:
                        if option == 'tags_cut_mob':
                            values['mobile_tags_count'] = raw_tag_field['value'][option]
                            if isinstance(values['mobile_tags_count'], str) and values['mobile_tags_count'].isdigit():
                                values['mobile_tags_count'] = int(values['mobile_tags_count'])
                        elif option == 'tags_cut_tab':
                            values['tablet_tags_count'] = raw_tag_field['value'][option]
                            if isinstance(values['tablet_tags_count'], str) and values['tablet_tags_count'].isdigit():
                                values['tablet_tags_count'] = int(values['tablet_tags_count'])
                        elif option == 'tags_cut_desk':
                            values['desktop_tags_count'] = raw_tag_field['value'][option]
                            if isinstance(values['desktop_tags_count'], str) and values['desktop_tags_count'].isdigit():
                                values['desktop_tags_count'] = int(values['desktop_tags_count'])
                else:
                    values[raw_tag_field['attribute']] = raw_tag_field['value']
        async with self.session.get(
            f'{self.site_url}/nova-vendor/nova-attach-many/index-tags/{values["id"]}/attachable/tags'
        )  as resp:
            raw_relevanted_tags = await resp.json()
            relevanted_tags_ids = list(set(raw_relevanted_tags['selected']))

        return schemas.IndexTag(
            ident=values.get('id'),
            title=values.get('title'),
            slug=values.get('slug'),
            weight=values.get('weight'),
            no_index=values.get('no_index'),
            category_id=values.get('category_id'),
            relevanted_tags_ids=relevanted_tags_ids,
            desktop_tags_count=values.get('desktop_tags_count'),
            tablet_tags_count=values.get('tablet_tags_count'),
            mobile_tags_count=values.get('mobile_tags_count'),
            excerpt=values.get('excerpt'),
            description=values.get('description'),
            faq=values.get('faq', []),
            meta_title=values.get('meta_title'),
            meta_description=values.get('meta_description'),
        )
    
    async def create(self, tag: schemas.IndexTag, is_lite: bool = False) -> schemas.IndexTag | None:
        """Create new tag."""
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }

        fields = {
            'title': tag.title,
            'slug': tag.slug,
            'weight': str(tag.weight) if tag.weight is not None else '0',
            'no_index': '1' if tag.no_index else '0',
            'category': str(tag.category_id) if tag.category_id is not None else '',
            'category_trashed': 'false',
            'tags': str(tag.relevanted_tags_ids),
            'options[tags_cut_desk]': str(tag.desktop_tags_count) if tag.desktop_tags_count is not None else '',
            'options[tags_cut_tab]': str(tag.tablet_tags_count) if tag.tablet_tags_count is not None else '',
            'options[tags_cut_mob]': str(tag.mobile_tags_count) if tag.mobile_tags_count is not None else '',
            'excerpt': tag.excerpt or '',
            'description': tag.description or '',
            '___nova_flexible_content_fields': '["options__faq"]',
            'meta_title': tag.meta_title or '',
            'meta_description': tag.meta_description or '',
            'viaResource': '',
            'viaResourceId': '',
            'viaRelationship': '',
        }
        if tag.faq:
            faq_fields = []
            for faq in tag.faq:
                key = self.generate_layout_key()
                faq_fields.append({
                    'layout': 'faq',
                    'key': f'{key}-faq',
                    'attributes': {
                        f'{key}-faq__title': faq.question,
                        f'{key}-faq__description': faq.answer,
                    }
                })
            fields['options__faq'] = str(faq_fields).replace("'", '"')



        form = MultipartEncoder(fields, boundary=boundary)
        async with self.session.post(
            f'{self.site_url}/nova-api/index-tags?editing=true&editMode=create',
            data=form.to_string(),
            headers=headers,
            allow_redirects=False
        ) as resp:
            resp.raise_for_status()
            if resp.status == 201:
                if is_lite:
                    return
                response_json = await resp.json()
                return await self.get(response_json['resource']['id'])
            else:
                error_text = await resp.text()
                logger.error(error_text)
                raise Exception(error_text)

    async def update(self, updated_tag: schemas.IndexTag, is_lite: bool = False) -> schemas.IndexTag | None:
        """Update tag."""
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        if not updated_tag.ident:
            raise Exception('Tag id is required.')
        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }

        fields = {
            'title': updated_tag.title,
            'slug': updated_tag.slug,
            'weight': str(updated_tag.weight) if updated_tag.weight is not None else '0',
            'no_index': '1' if updated_tag.no_index else '0',
            'category': str(updated_tag.category_id) if updated_tag.category_id is not None else '',
            'category_trashed': 'false',
            'tags': str(updated_tag.relevanted_tags_ids),
            'options[tags_cut_desk]': str(updated_tag.desktop_tags_count) if updated_tag.desktop_tags_count is not None else '',
            'options[tags_cut_tab]': str(updated_tag.tablet_tags_count) if updated_tag.tablet_tags_count is not None else '',
            'options[tags_cut_mob]': str(updated_tag.mobile_tags_count) if updated_tag.mobile_tags_count is not None else '',
            'excerpt': updated_tag.excerpt or '',
            'description': updated_tag.description or '',
            '___nova_flexible_content_fields': '["options__faq"]',
            'meta_title': updated_tag.meta_title or '',
            'meta_description': updated_tag.meta_description or '',
            '_method': 'PUT',
            '_retrieved_at': str(int(datetime.now().timestamp())),
        }
        if updated_tag.faq:
            faq_fields = []
            for faq in updated_tag.faq:
                key = faq.key or self.generate_layout_key()
                faq_fields.append({
                    'layout': 'faq',
                    'key': f'{key}-faq',
                    'attributes': {
                        f'{key}-faq__title': faq.question,
                        f'{key}-faq__description': faq.answer,
                    }
                })
            fields['options__faq'] = json.dumps(faq_fields)

        params = {'editing': 'true', 'editMode': 'update'}

        form = MultipartEncoder(fields, boundary=boundary)
        async with self.session.post(
            f'{self.site_url}/nova-api/index-tags/{updated_tag.ident}',
            data=form.to_string(),
            headers=headers,
            allow_redirects=False,
            params=params
        ) as resp:
            resp.raise_for_status()
            if resp.status == 200:
                if is_lite:
                    return
                raw_tag = await resp.json()
                return await self.get(raw_tag['resource']['id'])
            else:
                logger.error(resp.text)
                raise Exception(resp.text)

    async def add_to_category(self, tag_ident: int, category_ident: int) -> None:
        """Add tag to category."""
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        page_id = config.CATEGORY_PAGE_MAP.get(category_ident)
        if not page_id:
            raise Exception(f'Category id {category_ident} not found in config.')
        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }
        fields = {
            'tags': str(tag_ident),
            'tags_trashed': 'false',
            'viaRelationship': 'index_tags',
        }

        form = MultipartEncoder(fields, boundary=boundary)

        params = {
            'editing': 'true',
            'editMode': 'attach',
        }
        async with self.session.post(
            f'{self.site_url}/nova-api/pages/{page_id}/attach-morphed/index_tags',
            params=params,
            data=form.to_string(),
            headers=headers,
            allow_redirects=False
        ) as resp:
            if resp.status != 200:
                try:
                    error = await resp.json()
                except Exception:
                    error = await resp.text()
                    logger.error(error)
                    raise Exception(f'Error attaching tag {tag_ident} to category {category_ident}: {error}')
                if error.get('message') and error['message'] == 'This tag is already attached.':
                    logger.error(error['message'])
                    return
            resp.raise_for_status()

    @staticmethod
    def generate_layout_key(length=21):
        alphabet = string.ascii_lowercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))