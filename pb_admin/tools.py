from requests import Session
from pb_admin import schemas
import uuid
from requests_toolbelt import MultipartEncoder


class Tools():
    def __init__(self, session: Session, site_url: str) -> None:
        self.session = session
        self.site_url = site_url

    def make_push(self, product_ids: list[int], product_type: schemas.ProductType) -> None:
        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-XSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
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

        resp = self.session.post(
            _url,
            params=params,
            headers=headers,
            data=form.to_string(),
        )
        resp.raise_for_status()
