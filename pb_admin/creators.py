from requests import Session
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
import uuid
from requests_toolbelt import MultipartEncoder


class Creators():
    def __init__(self, session: Session, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    def get_list(self, search: str = '') -> list[schemas.CreatorLite]:
        creators = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search,
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/creators', params=params)
            resp.raise_for_status()
            raw_page = resp.json()
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

    def get(self, ident: int) -> schemas.Creator:
        resp = self.session.get(f'{self.site_url}/nova-api/creators/{ident}')
        resp.raise_for_status()
        raw_data = resp.json()
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
                alt=values['avatar'][0]['custom_properties'].get('alt'),
            ) if values.get('avatar') else None,
        )
        return creator

    def create(self, creator: schemas.Creator) -> schemas.Creator:
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-XSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-Requested-With': 'XMLHttpRequest',
        }

        fields = {
            'name': creator.name,
            'description': creator.description,
            'link': creator.link,
            'viaResource': None,
            'viaResourceId': None,
        }
        if creator.avatar:
            fields['__media__[avatar][0]'] = (
                creator.avatar.file_name,
                creator.avatar.data,
                creator.avatar.mime_type
            )
        form = MultipartEncoder(fields, boundary=boundary)
        resp = self.session.post(
            f'{self.site_url}/nova-api/creators?editing=true&editMode=create',
            data=form.to_string(),
            headers=headers,
            allow_redirects=False
        )
        resp.raise_for_status()
        return self.get(resp.json()['resource']['id'])
