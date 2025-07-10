from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
import uuid
from requests_toolbelt.multipart.encoder import MultipartEncoder


class Fonts():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get(self, ident: int) -> schemas.Font:
        params = {
            'editing': 'true',
            'editMode': 'update',
            'viaResource': '',
            'viaResourceId': '',
            'viaRelationship': '',
        }
        async with self.session.get(
            f'{self.site_url}/nova-api/fonts/{ident}/update-fields',
            params=params
        ) as resp:
            resp.raise_for_status()
            raw_data = await resp.json()
            values = {cell['attribute']: cell['value'] for cell in raw_data['fields'].values()}
            return schemas.Font(
                ident=ident,
                title=values.get('title', ''),
                size=values.get('size', 40),
                top_indent=values.get('indent', 0),
                data=None,
                file_name=values.get('file'),
                mime_type=None,
            )

    async def create(self, font: schemas.Font, is_lite: bool = True) -> schemas.Font | None:
        if not self.edit_mode:
            raise ValueError('Edit mode is required')
        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }
        params = {'editing': 'true', 'editMode': 'create'}
        fields = {
            'title': font.title,
            'size': str(font.size),
            'indent': str(font.top_indent),
            'file': (font.file_name, font.data, font.mime_type),
            'viaResource': '',
            'viaResourceId': '',
            'viaRelationship': '',
        }
        form = MultipartEncoder(fields, boundary=boundary)
        async with self.session.post(
            f'{self.site_url}/nova-api/fonts',
            headers=headers,
            data=form.to_string(),
            params=params,
            allow_redirects=False,
        ) as resp:
            resp.raise_for_status()
            if is_lite:
                return
            raw_data = await resp.json()
            new_font = await self.get(raw_data['id'])
            return new_font
        