from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
import uuid
from requests_toolbelt import MultipartEncoder
from datetime import datetime


class Creators():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get_list(self, search: str = '') -> list[schemas.CreatorLite]:
        creators = []
        is_next_page = True
        params = {
            'perPage': '100',
            'search': search,
        }
        while is_next_page:
            async with self.session.get(f'{self.site_url}/nova-api/creators', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()
                for row in raw_page['resources']:
                    values = {cell['attribute']: cell['value'] for cell in row['fields']}
                    creators.append(
                        schemas.CreatorLite(
                            ident=values.get('id'),
                            name=values.get('name'),
                            link=values.get('link'),
                        )
                    )
                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))
                else:
                    is_next_page = False
        return creators

    async def get(self, ident: int) -> schemas.Creator:
        async with self.session.get(f'{self.site_url}/nova-api/creators/{ident}') as resp:
            resp.raise_for_status()
            raw_data = await resp.json()
            values = {cell['attribute']: cell['value'] for cell in raw_data['resource']['fields']}
            creator = schemas.Creator(
                ident=values.get('id'),
                name=values.get('name'),
                link=values.get('link'),
                description=values.get('description'),
                avatar=schemas.Image(
                    ident=values['avatar'][0]['id'],
                    mime_type=values['avatar'][0]['mime_type'],
                    original_url=values['avatar'][0]['original_url'],
                    file_name=values['avatar'][0]['file_name'],
                ) if values.get('avatar') else None,
            )
        return creator

    async def create(self, creator: schemas.Creator) -> schemas.Creator:
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
            'name': creator.name,
            'description': creator.description,
            'link': creator.link,
            'viaResource': '',
            'viaResourceId': '',
        }
        if creator.avatar:
            fields['__media__[avatar][0]'] = (
                creator.avatar.file_name,
                creator.avatar.data,
                creator.avatar.mime_type
            )
        form = MultipartEncoder(fields, boundary=boundary)
        async with self.session.post(
            f'{self.site_url}/nova-api/creators?editing=true&editMode=create',
            data=form.to_string(),
            headers=headers,
            allow_redirects=False
        ) as resp:
            resp.raise_for_status()
            raw_creator = await resp.json()
        return await self.get(raw_creator['resource']['id'])

    async def update(self, creator: schemas.Creator) -> schemas.Creator:
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
            'name': creator.name,
            'description': creator.description,
            'link': creator.link if creator.link else '',
            '_method': 'PUT',
            '_retrieved_at': str(int(datetime.now().timestamp())),
        }
        if creator.avatar and creator.avatar.ident:
            fields['__media__[avatar][0]'] = str(creator.avatar.ident)
        elif creator.avatar:
            fields['__media__[avatar][0]'] = (
                creator.avatar.file_name,
                creator.avatar.data,
                creator.avatar.mime_type
            )
        form = MultipartEncoder(fields, boundary=boundary)
        async with self.session.post(
            f'{self.site_url}/nova-api/creators/{creator.ident}??viaResource=&viaResourceId=&viaRelationship=&editing=true&editMode=update',
            data=form.to_string(),
            headers=headers,
            allow_redirects=False
        ) as resp:
            resp.raise_for_status()
            raw_creator = await resp.json()
        return await self.get(raw_creator['resource']['id'])