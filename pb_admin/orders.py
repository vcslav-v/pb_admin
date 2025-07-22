from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
from datetime import datetime, timezone
import uuid
from requests_toolbelt import MultipartEncoder


class Orders():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get_list(self, search: str | None = None, limit: int | None = None) -> list[schemas.Order]:
        orders = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search or '',
        }
        while is_next_page and (limit is None or len(orders) < limit):
            async with self.session.get(f'{self.site_url}/nova-api/orders', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()

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

    async def get(self, order_id: int) -> schemas.Order:
        async with self.session.get(
            f'{self.site_url}/nova-api/orders/{order_id}',
        ) as resp:
            resp.raise_for_status()
            raw_page = await resp.json()

            values = {}
            for cell in raw_page['resource']['fields']:
                if cell['attribute'] == 'user':
                    values['user_id'] = cell['belongsToId']
                elif cell['attribute'] == 'Orderable':
                    if cell['resourceName'] == 'products':
                        values['product_id'] = cell['morphToId']
                    elif cell['resourceName'] == 'subscriptions':
                        values['user_subscription_id'] = cell['morphToId']
                elif cell['attribute'] == 'coupon':
                    values['coupon'] = cell['value']
                    values['coupon_id'] = cell['belongsToId']
                else:
                    values[cell['attribute']] = cell['value']

            return schemas.Order(
                ident=order_id,
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
                payments_sum=float(values.get('payments_sum', 0.0)),
                coupon_id=values.get('coupon_id'),
            )

    async def update(self, order: schemas.Order, is_lite: bool = False) -> schemas.Order | None:
        if not self.edit_mode:
            raise ValueError('Edit mode is required')
        if not order.ident:
            raise ValueError('Order id is required')

        old_order = await self.get(order.ident)

        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-XSRF-TOKEN': self.session.cookie_jar.filter_cookies(self.site_url).get('XSRF-TOKEN').value,
            'X-Requested-With': 'XMLHttpRequest',
        }
        params = {'editing': 'true', 'editMode': 'update'}

        order_product_type = None
        if order.product_id:
            order_product_type = 'products'
        elif order.user_subscription_id:
            order_product_type = 'subscriptions'

        order_product_trashed = 'false'
        if old_order.product_id or old_order.user_subscription_id:
            if not (order.product_id or order.user_subscription_id):
                order_product_trashed = 'true'

        order_product_id = ''
        if order.product_id:
            order_product_id = str(order.product_id)
        elif order.user_subscription_id:
            order_product_id = str(order.user_subscription_id)

        coupon = ''
        if order.coupon_id:
            coupon = str(order.coupon_id)

        fields = {
            'payed': '1' if order.is_payed else '0',
            'count': str(order.count),
            'price': str(order.price),
            'discounted_price': str(order.discounted_price),
            'payments_sum': str(order.payments_sum),
            'user': str(order.user_id) if order.user_id else '',
            'user_trashed': 'true' if old_order.user_id and not order.user_id  else 'false',
            'created_at': order.created_at.strftime("%Y-%m-%d") if order.created_at else '',
            'Orderable': order_product_id,
            'Orderable_type': order_product_type,
            'Orderable_trashed': order_product_trashed,
            'coupon': coupon,
            'coupon_trashed': 'true' if old_order.coupon and not order.coupon else 'false',
            'extended': '1' if order.is_extended_license else '0',
            '_method': 'PUT',
            '_retrieved_at': str(int(datetime.now(tz=timezone.utc).timestamp())),
        }

        form = MultipartEncoder(fields, boundary=boundary)
        async with self.session.post(
            f'{self.site_url}/nova-api/orders/{order.ident}',
            headers=headers,
            data=form.to_string(),
            params=params,
            allow_redirects=False,
        ) as resp:
            resp.raise_for_status()
            if is_lite:
                return
        return await self.get(order.ident)

    def _cents_to_price(self, price: int | None) -> str | None:
        if price is None:
            return price
        return str(price // 100)
