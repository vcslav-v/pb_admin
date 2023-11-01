"""Main module pb_admin project."""

__version__ = '0.1.10'
__author__ = 'Vaclav_V'

import requests
import os
from bs4 import BeautifulSoup

from pb_admin.tags import Tags

SITE_URL = os.environ.get('SITE_URL', '')
PB_LOGIN = os.environ.get('PB_LOGIN', '')
PB_PASSWORD = os.environ.get('PB_PASSWORD', '')


class PbSession():
    def __init__(
            self,
            site_url: str = SITE_URL,
            login: str = PB_LOGIN,
            password: str = PB_PASSWORD,
    ) -> None:
        self.site_url = site_url
        self.login = login
        self.password = password

        self.session = requests.Session()
        self._login()

        self.tags = Tags(self.session, self.site_url)

    def _login(self):
        resp = self.session.get(f'{self.site_url}/admin/login')
        soup = BeautifulSoup(resp.text, 'html.parser')
        token = soup.find('input', {'name': '_token'}).get('value')
        payload = {
            'email': self.login,
            'password': self.password,
            'remember': 'on',
            '_token': token
        }
        resp = self.session.post(f'{self.site_url}/admin/login', data=payload)
        resp.raise_for_status()
