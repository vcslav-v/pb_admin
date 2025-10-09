from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
import uuid
from requests_toolbelt.multipart.encoder import MultipartEncoder
from datetime import datetime


class Banners():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get_list(self, search: str = '', limit: int | None = None) -> list[schemas.BannerLite]:
        banners = []
        is_next_page = True
        params = {
            'perPage': '100',
            'search': search,
        }
        while is_next_page and (limit is None or len(banners) < limit):
            async with self.session.get(f'{self.site_url}/nova-api/banners', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()
                for row in raw_page['resources']:
                    values = {}
                    for cell in row['fields']:
                        values[cell['attribute']] = cell['value']
                    images = []
                    images_retina = []
                    for cell in values['banner_images']:
                        images.append(schemas.Image(
                            ident=cell['id'],
                            file_name=cell['file_name'],
                            mime_type=cell['mime_type'],
                            original_url=cell['original_url'],
                        ))
                    for cell in values['banner_images_retina']:
                        images_retina.append(schemas.Image(
                            ident=cell['id'],
                            file_name=cell['file_name'],
                            mime_type=cell['mime_type'],
                            original_url=cell['original_url'],
                        ))
                    try:
                        banners.append(
                            schemas.BannerLite(
                                ident=values.get('id'),
                                banner_type=values.get('type'),
                                is_active=values.get('is_enabled'),
                                weight=values.get('order_index'),
                                images=images,
                                images_retina=images_retina,
                            )
                        )
                    except Exception as e:
                        print(f'Error in banner {values.get("id")}: {e}')
                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))
                else:
                    is_next_page = False
        return banners
    
    async def get(self, banner_id: int) -> schemas.Banner:
        async with self.session.get(f'{self.site_url}/nova-api/banners/{banner_id}') as resp:
            resp.raise_for_status()
            raw_banner = await resp.json()
            values = {}
            for cell in raw_banner['resource']['fields']:
                if not cell['attribute'] and cell.get('component') == 'nova-dependency-container' and cell.get('fields'):
                    for subcell in cell['fields']:
                        if subcell['attribute'] == 'link':
                            values['link'] = subcell['value']
                        elif subcell['attribute'] == 'link_blank':
                            values['link_blank'] = subcell['value']
                        elif subcell['attribute'] == 'options->height':
                            values['height'] = int(subcell['value']) if subcell['value'] else None
                        elif subcell['attribute'] == 'options->color':
                            values['color'] = subcell['value'] if subcell['value'] else None
                else:
                    values[cell['attribute']] = cell['value']
            images = []
            images_retina = []
            for cell in values['banner_images']:
                images.append(schemas.Image(
                    ident=cell['id'],
                    file_name=cell['file_name'],
                    mime_type=cell['mime_type'],
                    original_url=cell['original_url'],
                ))
            for cell in values['banner_images_retina']:
                images_retina.append(schemas.Image(
                    ident=cell['id'],
                    file_name=cell['file_name'],
                    mime_type=cell['mime_type'],
                    original_url=cell['original_url'],
                ))


        banner = schemas.Banner(
            ident=values.get('id'),
            banner_type=values.get('type'),
            is_active=values.get('is_enabled'),
            weight=values.get('order_index'),
            images=images,
            images_retina=images_retina,
            link=values.get('link'),
            open_in_new_tab=values.get('link_blank', False),
            color=values.get('color'),
            height=values.get('height'),
            assigned_group_ids=await self._get_groups(values.get('id')),
        )
        return banner

    async def update(self, banner: schemas.Banner, is_lite: bool = False) -> schemas.Banner | None:
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        if not banner.ident:
            raise Exception('Banner id is required.')
        boundary = str(uuid.uuid4())
        images = []
        images_retina = []
        for img in banner.images:
            if img.ident:
                images.append(str(img.ident))
                continue
            images.append((
                img.file_name,
                img.data,
                img.mime_type
            ))
        for img in banner.images_retina:
            if img.ident:
                images_retina.append(str(img.ident))
                continue
            images_retina.append((
                img.file_name,
                img.data,
                img.mime_type
            ))
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }

        fields = {
            'type': banner.banner_type.name,
            'is_enabled': '1' if banner.is_active else '0',
            'link': banner.link,
            'link_blank': '1' if banner.open_in_new_tab else '0',
            'order_index': str(banner.weight),
            '_method': 'PUT',
            '_retrieved_at': str(int(datetime.now().timestamp())),
        }
        for i, img in enumerate(images):
            fields[f'__media__[banner_images][{i}]'] = img
        for i, img in enumerate(images_retina):
            fields[f'__media__[banner_images_retina][{i}]'] = img
        
        if banner.color and banner.banner_type == schemas.BannerType.top:
            fields['options->color'] = banner.color
        elif banner.banner_type == schemas.BannerType.top:
            fields['options->color'] = '#FFFFFF'
        if banner.height and banner.banner_type == schemas.BannerType.top:
            fields['options->height'] = str(banner.height)
        elif banner.banner_type == schemas.BannerType.top:
            fields['options->height'] = '100'

        params = {'editing': 'true', 'editMode': 'update'}

        form = MultipartEncoder(fields, boundary=boundary)
        async with self.session.post(
            f'{self.site_url}/nova-api/banners/{banner.ident}',
            data=form.to_string(),
            headers=headers,
            allow_redirects=False,
            params=params
        ) as resp:
            resp.raise_for_status()

        banner_group_ids = await self._get_groups(banner.ident)
        group_ids_for_add = list(set(banner.assigned_group_ids) - set(banner_group_ids))
        group_ids_for_remove = list(set(banner_group_ids) - set(banner.assigned_group_ids))
        for group_id in group_ids_for_add:
            await self._add_to_group(banner.ident, group_id)
        for group_id in group_ids_for_remove:
            await self._remove_from_group(banner.ident, group_id)
        return None if is_lite else await self.get(banner.ident)
    
    async def create(self, banner: schemas.Banner, is_lite: bool = False) -> schemas.Banner | None:
        if not self.edit_mode:
            raise Exception('Edit mode is required.')
        boundary = str(uuid.uuid4())
        images = []
        images_retina = []
        for img in banner.images:
            images.append((
                img.file_name,
                img.data,
                img.mime_type
            ))
        for img in banner.images_retina:
            images_retina.append((
                img.file_name,
                img.data,
                img.mime_type
            ))
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }

        fields = {
            'type': banner.banner_type.name,
            'is_enabled': '1' if banner.is_active else '0',
            'link': banner.link,
            'link_blank': '1' if banner.open_in_new_tab else '0',
            'order_index': str(banner.weight),
            '_retrieved_at': str(int(datetime.now().timestamp())),
        }
        for i, img in enumerate(images):
            fields[f'__media__[banner_images][{i}]'] = img
        for i, img in enumerate(images_retina):
            fields[f'__media__[banner_images_retina][{i}]'] = img
        
        if banner.color and banner.banner_type == schemas.BannerType.top:
            fields['options->color'] = banner.color
        elif banner.banner_type == schemas.BannerType.top:
            fields['options->color'] = '#FFFFFF'
        if banner.height and banner.banner_type == schemas.BannerType.top:
            fields['options->height'] = str(banner.height)
        elif banner.banner_type == schemas.BannerType.top:
            fields['options->height'] = '100'

        params = {'editing': 'true', 'editMode': 'create'}

        form = MultipartEncoder(fields, boundary=boundary)
        async with self.session.post(
            f'{self.site_url}/nova-api/banners',
            data=form.to_string(),
            headers=headers,
            allow_redirects=False,
            params=params
        ) as resp:
            resp.raise_for_status()
            raw_banner = await resp.json()
            banner_id = raw_banner['resource']['id']

        for group_id in banner.assigned_group_ids:
            await self._add_to_group(banner_id, group_id)
        return None if is_lite else await self.get(banner_id)

    async def _get_groups(self, banner_id: int) -> list[int]:
        params = {
            'perPage': '100',
            'page': '1',
            'viaResource': 'banners',
            'viaResourceId': str(banner_id),
            'viaRelationship': 'groups',
            'relationshipType': 'morphToMany',
        }

        group_ids = []
        is_next_page = True
        while is_next_page:
            async with self.session.get(f'{self.site_url}/nova-api/user-groups?', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()
                for row in raw_page['resources']:
                    group_ids.append(row['id']['value'])
                is_next_page = bool(raw_page.get('next_page_url'))
                if is_next_page:
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))
        return group_ids
    
    async def _remove_from_group(self, banner_id: int, group_id: int) -> None:
        params = {
            'trashed': '',
            'viaResource': 'banners',
            'viaResourceId': str(banner_id),
            'viaRelationship': 'groups',
            'resources[]': str(group_id),
        }
        headers = {
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }
        async with self.session.delete(
            f'{self.site_url}/nova-api/user-groups/detach',
            params=params,
            headers=headers
        ) as resp:
            resp.raise_for_status()

    async def _add_to_group(self, banner_id: int, group_id: int) -> None:
        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }
        fields = {
            'user-groups': str(group_id),
            'user-groups_trashed': 'false',
            'viaRelationship': 'groups',
        }

        form = MultipartEncoder(fields, boundary=boundary)

        params = {
            'editing': 'true',
            'editMode': 'attach',
        }
        async with self.session.post(
            f'{self.site_url}/nova-api/banners/{banner_id}/attach-morphed/user-groups',
            params=params,
            data=form.to_string(),
            headers=headers,
            allow_redirects=False
        ) as resp:
            resp.raise_for_status()
