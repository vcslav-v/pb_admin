from requests import Session
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas


class Users():
    def __init__(self, session: Session, site_url: str) -> None:
        self.session = session
        self.site_url = site_url

    def get_list(self, search: str = '') -> list[schemas.Subscription]:
        users = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search,
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/users', params=params)
            resp.raise_for_status()
            raw_page = resp.json()
            for row in raw_page['resources']:
                values = {cell['attribute']: cell['value'] for cell in row['fields']}

                users.append(
                    schemas.PbUser(
                        ident=values.get('id'),
                        name=values.get('name'),
                        email=values.get('email'),
                    )
                )
            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))
            else:
                is_next_page = False
        return users
