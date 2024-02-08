from requests import Session
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas


class Compatibilities():
    def __init__(self, session: Session, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    def get_list(self, search: str = '') -> list[schemas.Compatibility]:
        compatibilities = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search,
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/compatibilities', params=params)
            resp.raise_for_status()
            raw_page = resp.json()
            for row in raw_page['resources']:
                values = {cell['attribute']: cell['value'] for cell in row['fields']}
                compatibilities.append(
                    schemas.Compatibility(
                        ident=values.get('id'),
                        title=values.get('title'),
                        alias=values.get('alias'),
                        color=values.get('color'),
                    )
                )
            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))
            else:
                is_next_page = False
        return compatibilities
