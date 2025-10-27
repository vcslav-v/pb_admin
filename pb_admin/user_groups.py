from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
import uuid
from requests_toolbelt.multipart.encoder import MultipartEncoder
from asyncio import sleep


class UserGroups():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get_list(self, search: str = '', limit: int | None = None) -> list[schemas.UserGroupLight]:
        user_groups = []
        is_next_page = True
        params = {
            'perPage': '100',
            'search': search,
        }
        while is_next_page and (limit is None or len(user_groups) < limit):
            async with self.session.get(f'{self.site_url}/nova-api/user-groups', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()
                for row in raw_page['resources']:
                    values = {}
                    for cell in row['fields']:
                        values[cell['attribute']] = cell['value']
                    try:
                        user_groups.append(
                            schemas.UserGroupLight(
                                ident=values.get('id'),
                                name=values.get('title'),
                            )
                        )
                    except Exception as e:
                        print(f'Error in user group {values.get("id")}: {e}')
                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))
                else:
                    is_next_page = False
        for ug in user_groups:
            async with self.session.get(f'{self.site_url}/nova-api/user-groups/{ug.ident}') as resp:
                resp.raise_for_status()
                raw_ug = await resp.json()
                raw_ug_fields = raw_ug['resource']['fields']
                for field in raw_ug_fields:
                    if field['attribute'] == 'options':
                        for item in field['fields']:
                            if item['attribute'] == 'segment_id':
                                ug.segment_id = int(item['value']) if item['value'] else None
        return user_groups
    
    async def get_users(self, user_group_light: schemas.UserGroupLight) -> schemas.UserGroup:
        is_next_page = True
        params = {
            'perPage': '5',
            'viaResource': 'user-groups',
            'viaResourceId': str(user_group_light.ident),
            'viaRelationship': 'users',
            'relationshipType': 'morphToMany',
        }
        user_ids = []
        while is_next_page:
            async with self.session.get(f'{self.site_url}/nova-api/users', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()
                for row in raw_page['resources']:
                   user_ids.append(row['id']['value'])
                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))
                else:
                    is_next_page = False
        return schemas.UserGroup(
            ident=user_group_light.ident,
            name=user_group_light.name,
            segment_id=user_group_light.segment_id,
            user_ids=user_ids
        )

    async def deattach_users(self, user_group_ident: int, user_ids: list[int]) -> bool:
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        batch_size = 100
        headers = {
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }
        for user_ids_batch in self._chunk_list(user_ids, batch_size):
            params = {
                'viaResource': 'user-groups',
                'viaResourceId': str(user_group_ident),
                'viaRelationship': 'users',
                'resources[]': user_ids_batch,
            }
            async with self.session.delete(f'{self.site_url}/nova-api/users/detach', params=params, headers=headers) as resp:
                resp.raise_for_status()
        return True


    async def attach_users(self, user_group_ident: int, user_ids: list[int]) -> bool:
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        headers = {
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }
        params = {'editing': 'true', 'editMode': 'attach'}
        
        for user_id in user_ids:
            boundary = str(uuid.uuid4())
            headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'

            fields = {
                'user-groups': str(user_group_ident),
                'user-groups_trashed': 'false',
                'viaRelationship': 'groups',
            }

            form = MultipartEncoder(fields, boundary=boundary)
            async with self.session.post(
                f'{self.site_url}/nova-api/users/{user_id}/attach-morphed/user-groups',
                data=form.to_string(),
                headers=headers,
                allow_redirects=False,
                params=params
            ) as resp:
                try:
                    resp.raise_for_status()
                except Exception as e:
                    text = await resp.text()
                    print(f'Error attaching user {user_id} to group {user_group_ident}: {e}\nResponse text: {text}')
            await sleep(0.1)  # To avoid overwhelming the server
        
        return True
    
    def _chunk_list(self, lst, size):
        for i in range(0, len(lst), size):
            yield lst[i:i + size]