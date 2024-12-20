from aiohttp import ClientSession
from pb_admin import schemas
import uuid
from requests_toolbelt import MultipartEncoder


class Tools():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def make_push(self, product_ids: list[int], product_type: schemas.ProductType) -> None:
        if not self.edit_mode:
            raise ValueError('Edit mode is requared.')
        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }
        params = {
            'action': 'send-push',
            'pivotAction': 'false',
            'search': '',
            'filters': 'W10=',
            'trashed': '',
        }
        fields = {
            'resources': ','.join([str(i) for i in product_ids]),
        }
        form = MultipartEncoder(fields, boundary=boundary)

        if product_type == schemas.ProductType.freebie:
            _url = f'{self.site_url}/nova-api/freebies/action'
        elif product_type == schemas.ProductType.premium:
            _url = f'{self.site_url}/nova-api/premia/action'
        elif product_type == schemas.ProductType.plus:
            _url = f'{self.site_url}/nova-api/pluses/action'
        else:
            raise ValueError('Unknown product type.')

        async with self.session.post(
            _url,
            params=params,
            headers=headers,
            data=form.to_string(),
        ) as resp:
            resp.raise_for_status()
