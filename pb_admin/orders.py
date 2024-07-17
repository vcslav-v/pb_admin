from requests import Session
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
from datetime import datetime


class Orders():
    def __init__(self, session: Session, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    def get_list(self, search: str = None) -> list[schemas.Order]:
        orders = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search or '',
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/orders', params=params)
            resp.raise_for_status()
            raw_page = resp.json()

            for row in raw_page['resources']:
                values = {}
                for cell in row['fields']:
                    if cell['attribute'] == 'user':
                        values['user_id'] = cell['belongsToId']
                    elif cell['attribute'] == 'Orderable':
                        if cell['resourceName'] == 'products':
                            values['product_id'] = cell['morphToId']
                        elif cell['resourceName'] == 'subscriptions':
                            values['user_subscription_id'] = cell['morphToId']
                    else:
                        values[cell['attribute']] = cell['value']
                orders.append(
                    schemas.Order(
                        ident=values.get('id'),
                        is_payed=True if values.get('payed') == 'Payed' else False,
                        count=values.get('count'),
                        price=values.get('price'),
                        discounted_price=values.get('discounted_price'),
                        user_id=values.get('user_id'),
                        created_at=datetime.fromisoformat(values.get('created_at')) if values.get('created_at') else None,
                        product_id=values.get('product_id'),
                        user_subscription_id=values.get('user_subscription_id'),
                        coupon=values.get('coupon'),
                        is_extended_license=False if values.get('extended') == 'Standard' else True,
                    )
                )

            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))

            else:
                is_next_page = False

        return orders
