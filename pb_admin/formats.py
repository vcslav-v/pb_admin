from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas


class Formats():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get_list(self, search: str = '') -> list[schemas.Format]:
        tags = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search,
        }
        while is_next_page:
            async with self.session.get(f'{self.site_url}/nova-api/formats', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()
                for row in raw_page['resources']:
                    values = {cell['attribute']: cell['value'] for cell in row['fields']}
                    tags.append(
                        schemas.Format(
                            ident=values.get('id'),
                            title=values.get('title'),
                        )
                    )
                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))
                else:
                    is_next_page = False
        return tags
