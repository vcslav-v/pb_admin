from requests import Session
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
from datetime import datetime


class Subscriptions():
    def __init__(self, session: Session, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    def get_list(self, search: str = '') -> list[schemas.Subscription]:
        subscriptions = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search,
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/subscriptions', params=params)
            resp.raise_for_status()
            raw_page = resp.json()
            for row in raw_page['resources']:
                values = {}
                for cell in row['fields']:
                    if cell['attribute'] == 'user':
                        values['user_id'] = cell['belongsToId']
                    else:
                        values[cell['attribute']] = cell['value']
                try:
                    subscriptions.append(
                        schemas.Subscription(
                            ident=values.get('id'),
                            subscription_id=values.get('subscription_id'),
                            status=values.get('status'),
                            period=values.get('period'),
                            billing_plan=values.get('billingPlan'),
                            resubscribe=values.get('resubscribe'),
                            user_id=values.get('user_id'),
                            start_date=datetime.fromisoformat(values.get('start_date')) if values.get('start_date') else None,
                            end_date=datetime.fromisoformat(values.get('end_date')) if values.get('end_date') else None,
                            updated_at=datetime.fromisoformat(values.get('updated_at')) if values.get('updated_at') else None,
                        )
                    )
                except Exception as e:
                    print(f'Error in subscription {values.get("id")}: {e}')
            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))
            else:
                is_next_page = False
        return subscriptions
