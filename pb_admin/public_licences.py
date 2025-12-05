from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas, _image_tools as image_tools, _config as config
from loguru import logger
from requests_toolbelt import MultipartEncoder
import uuid
from datetime import datetime


class PublicLicences():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get_list(self, search: str = None, limit: int | None = None) -> list[schemas.Tag]:
        """"""
        licenses = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search or '',
        }
        while is_next_page and (limit is None or len(licenses) < limit):
            async with self.session.get(f'{self.site_url}/nova-api/licenses', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()

                for row in raw_page['resources']:
                    values = {cell['attribute']: cell['value'] for cell in row['fields']}
                    licenses.append(
                        schemas.PublicLicense(
                            ident=values.get('id'),
                            name=values.get('name'),
                            url=values.get('url'),
                        )
                    )

                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))

                else:
                    is_next_page = False

        return licenses
