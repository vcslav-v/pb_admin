from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas, _image_tools as image_tools, _config as config
from loguru import logger
from requests_toolbelt import MultipartEncoder
import uuid
from datetime import datetime


class Tags():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get_list(self, search: str = None, limit: int | None = None) -> list[schemas.Tag]:
        """Get list of all tags in short version id, name, title, description, meta_title, meta_description, no_index."""
        tags = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search or '',
        }
        while is_next_page and (limit is None or len(tags) < limit):
            async with self.session.get(f'{self.site_url}/nova-api/tags', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()

                for row in raw_page['resources']:
                    values = {cell['attribute']: cell['value'] for cell in row['fields']}
                    tags.append(
                        schemas.Tag(
                            ident=values.get('id'),
                            name=values.get('name'),
                            title=values.get('title'),
                            description=values.get('description'),
                            meta_title=values.get('meta_title'),
                            meta_description=values.get('meta_description'),
                            no_index=values.get('no_index'),
                            is_group=values.get('group_size', False),
                        )
                    )

                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))

                else:
                    is_next_page = False

        return tags

    async def get(self, tag_ident: int) -> schemas.Tag:
        """Get tag by id."""
        async with self.session.get(f'{self.site_url}/nova-api/tags/{tag_ident}') as resp:
            resp.raise_for_status()
            raw_tag = await resp.json()
            raw_tag_fields = raw_tag['resource']['fields']
            values = {raw_tag_field['attribute']: raw_tag_field['value'] for raw_tag_field in raw_tag_fields}
            if values['meta_image']:
                raw_img = values['meta_image'][0]
                img = schemas.Image(
                    ident=raw_img['id'],
                    mime_type=raw_img['mime_type'],
                    original_url=raw_img['original_url'],
                    file_name=raw_img['file_name']
                )
            else:
                img = None

        async with self.session.get(
            f'{self.site_url}/nova-vendor/nova-attach-many/tags/{values["id"]}/attachable/tags'
        )  as resp:
            raw_relevanted_tags = await resp.json()
            relevanted_tags_ids = list(set(raw_relevanted_tags['selected']))

        async with self.session.get(
            f'{self.site_url}/nova-vendor/nova-attach-many/tags/{values["id"]}/attachable/subtags'
        ) as resp:
            raw_sub_tags = await resp.json()
            sub_tags_ids = list(set(raw_sub_tags['selected']))

        return schemas.Tag(
            ident=values['id'],
            name=values['name'],
            title=values['title'],
            description=values['description'],
            meta_title=values['meta_title'],
            meta_description=values['meta_description'],
            image=img,
            no_index=values['no_index'],
            relevanted_tags_ids=relevanted_tags_ids,
            sub_tags_ids=sub_tags_ids,
            is_group=True if sub_tags_ids else False,
        )

    async def create(self, tag: schemas.Tag, is_lite: bool = False) -> schemas.Tag | None:
        """Create new tag."""
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        boundary = str(uuid.uuid4())
        if tag.image:
            tag.image = await image_tools.prepare_image(tag.image, config.TAG_IMG_SIZE, config.TAG_IMG_SIZE)
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }

        fields = {
            'name': tag.name,
            'title': tag.title,
            'description': tag.description,
            'meta_title': tag.meta_title,
            'meta_description': tag.meta_description,
            'no_index': '1' if tag.no_index else '0',
            'tags': str(tag.relevanted_tags_ids),
            'subtags': str(tag.sub_tags_ids),
        }
        if tag.image:
            fields['__media__[meta_image][0]'] = (
                tag.image.file_name,
                tag.image.data,
                tag.image.mime_type
            )
        form = MultipartEncoder(fields, boundary=boundary)
        async with self.session.post(
            f'{self.site_url}/nova-api/tags?editing=true&editMode=create',
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

    async def delete(self, tag_ident: int) -> None:
        """Delete tag by id."""
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        params = {'resources[]': tag_ident}
        headers = {
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }

        async with self.session.delete(f'{self.site_url}/nova-api/tags', params=params, headers=headers) as resp:
            resp.raise_for_status()

    async def update(self, updated_tag: schemas.Tag, is_lite: bool = False) -> schemas.Tag | None:
        """Update tag."""
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        if not updated_tag.ident:
            raise Exception('Tag id is required.')
        boundary = str(uuid.uuid4())
        if updated_tag.image and not updated_tag.image.ident:
            updated_tag.image = await image_tools.prepare_image(updated_tag.image, config.TAG_IMG_SIZE, config.TAG_IMG_SIZE)
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }
        if updated_tag.image and not updated_tag.image.ident:
            img_field = (
                updated_tag.image.file_name,
                updated_tag.image.data,
                updated_tag.image.mime_type
            )
        elif updated_tag.image and updated_tag.image.ident:
            img_field = str(updated_tag.image.ident)
        else:
            img_field = None

        fields = {
            'name': updated_tag.name,
            'title': updated_tag.title,
            'description': updated_tag.description,
            'meta_title': updated_tag.meta_title,
            'meta_description': updated_tag.meta_description,
            'no_index': '1' if updated_tag.no_index else '0',
            'tags': str(updated_tag.relevanted_tags_ids),
            'subtags': str(updated_tag.sub_tags_ids),
            '_method': 'PUT',
            '_retrieved_at': str(int(datetime.now().timestamp())),
        }
        if img_field:
            fields['__media__[meta_image][0]'] = img_field

        params = {'editing': 'true', 'editMode': 'update'}

        form = MultipartEncoder(fields, boundary=boundary)
        async with self.session.post(
            f'{self.site_url}/nova-api/tags/{updated_tag.ident}',
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


    async def get_all_tag_ids_in_category(self, category_ident: int) -> list[int]:
        """Get all tag ids in category."""
        tag_ids = []
        page_id = config.CATEGORY_PAGE_MAP.get(category_ident)
        if not page_id:
            raise Exception(f'Category id {category_ident} not found in config.')
        is_next_page = True
        params = {
            'search': '',
            'filters': 'W10=',
            'orderBy': '',
            'perPage': 100,
            'trashed': '',
            'page': 1,
            'viaResource': 'pages',
            'viaResourceId': str(page_id),
            'viaRelationship': 'tags',
            'relationshipType': 'morphToMany',
        }
        while is_next_page:
            async with self.session.get(
                f'{self.site_url}/nova-api/tags',
                params=params
            ) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()

                tag_ids.extend([row['id']['value'] for row in raw_page['resources']])

                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))
                else:
                    is_next_page = False
        return tag_ids


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
            'viaRelationship': 'tags',
        }

        form = MultipartEncoder(fields, boundary=boundary)

        params = {
            'editing': 'true',
            'editMode': 'attach',
        }
        async with self.session.post(
            f'{self.site_url}/nova-api/pages/{page_id}/attach-morphed/tags',
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

    async def remove_from_category(self, tag_ident: int, category_ident: int) -> None:
        """Remove tag from category."""
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        page_id = config.CATEGORY_PAGE_MAP.get(category_ident)
        if not page_id:
            raise Exception(f'Category id {category_ident} not found in config.')
        headers = {
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }

        params = {
            'search': '',
            'filters': 'W10=',
            'trashed': '',
            'viaResource': 'pages',
            'viaResourceId': str(page_id),
            'viaRelationship': 'tags',
            'resources[]': str(tag_ident),
        }
        async with self.session.delete(
            f'{self.site_url}/nova-api/tags/detach',
            params=params,
            headers=headers,
            allow_redirects=False
        ) as resp:
            text = await resp.text()
            resp.raise_for_status()

    @staticmethod
    def fill_scheme_by_policy(tag: schemas.Tag) -> schemas.Tag:
        title = tag.name.capitalize()
        return schemas.Tag(
            ident=tag.ident,
            name=tag.name.lower(),
            title=title,
            description=tag.description,
            meta_title=f'{title} - Free Download on Pixelbuddha',
            meta_description=f'Get The Best Free {title} on Pixelbuddha. ⬆️ 1000+ High-Quality Products ⬆️ Editable PSDs ⬆️ Exclusive Deals Today 💸',
            no_index=tag.no_index,
            relevanted_tags_ids=tag.relevanted_tags_ids,
            image=tag.image,
        )
