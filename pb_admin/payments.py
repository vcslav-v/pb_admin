from aiohttp import ClientSession
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
from datetime import datetime


class Payments():
    def __init__(self, session: ClientSession, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    async def get_list(self, search: str = None) -> list[schemas.Payment]:
        payments = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search or '',
        }
        while is_next_page:
            async with self.session.get(f'{self.site_url}/nova-api/payments', params=params) as resp:
                resp.raise_for_status()
                raw_page = await resp.json()

                for row in raw_page['resources']:
                    values = {}
                    for cell in row['fields']:
                        values[cell['attribute']] = cell['value']

                    payments.append(
                        schemas.Payment(
                            ident=values.get('id'),
                            order_id=int(values.get('order')) if values.get('order') else None,
                            price_cent=int(values.get('price'))*100,
                            status=schemas.PaymentStatus(values.get('status')),
                            created_at=datetime.fromisoformat(values.get('created_at'))
                        )
                    )

                if raw_page.get('next_page_url'):
                    parsed_url = urlparse(raw_page.get('next_page_url'))
                    params.update(parse_qs(parsed_url.query))
                else:
                    is_next_page = False

        return payments
