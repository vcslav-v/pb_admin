from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas


class Users():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get_list(self, search: str = '', limit: int | None = None) -> list[schemas.PbUser]:
        users = []
        is_next_page = True
        params = {
            'perPage': '100',
            'search': search,
        }
        while is_next_page and (limit is None or len(users) < limit):
            async with self.session.get(f'{self.site_url}/nova-api/users', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()
                values = {}
                for row in raw_page['resources']:
                    for cell in row['fields']: 
                        if cell['attribute'] == 'email' and cell.get('thumbnailUrl'):
                            values['userpic'] = cell['thumbnailUrl']
                        values[cell['attribute']] = cell['value']

                    users.append(
                        schemas.PbUser(
                            ident=values.get('id'),
                            name=values.get('name'),
                            email=values.get('email'),
                            userpic=values.get('userpic')
                        )
                    )
                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))
                else:
                    is_next_page = False
        return users

    async def get(self, user_id: int) -> schemas.PbUser:
        async with self.session.get(f'{self.site_url}/nova-api/users/{user_id}') as resp:
            resp.raise_for_status()
            raw_user = await resp.json()
            values = {}
            for cell in raw_user['resource']['fields']:
                if cell['attribute'] == 'email' and cell.get('thumbnailUrl'):
                    values['userpic'] = cell['thumbnailUrl']
                elif cell['attribute'] == 'options' and cell.get('fields'):
                    for opt in cell.get('fields'):
                        if opt['attribute'] == 'survey_type':
                            values['survey_type'] = opt['value']
                        elif opt['attribute'] == 'survey_areas':
                            values['activity'] = [item['area'] for item in json.loads(opt['value'])]
                values[cell['attribute']] = cell['value']
            if values.get('survey_type') or values.get('activity'):
                survey = schemas.UserSurvey(
                    user_type=values.get('survey_type'),
                    activity=values.get('activity', [])
                )
            else:
                survey = None
            return schemas.PbUser(
                ident=values.get('id'),
                name=values.get('name'),
                email=values.get('email'),
                userpic=values.get('userpic'),
                survey=survey
            )