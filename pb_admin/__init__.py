"""Main module pb_admin project."""

__version__ = '0.1.36'
__author__ = 'Vaclav_V'
__all__ = ['PbSession', 'schemas']


import requests
import os
from bs4 import BeautifulSoup

from pb_admin.tags import Tags
from pb_admin.categories import Categories
from pb_admin.products import Products
from pb_admin.tools import Tools
from pb_admin.formats import Formats
from pb_admin.compatibilities import Compatibilities
from pb_admin.subscriptions import Subscriptions
from pb_admin.users import Users
from pb_admin import schemas

SITE_URL = os.environ.get('SITE_URL', '')
PB_LOGIN = os.environ.get('PB_LOGIN', '')
PB_PASSWORD = os.environ.get('PB_PASSWORD', '')


class PbSession():
    def __init__(
            self,
            site_url: str = SITE_URL,
            login: str = PB_LOGIN,
            password: str = PB_PASSWORD,
            basic_auth_login: str = None,
            basic_auth_password: str = None,
    ) -> None:
        self.site_url = site_url
        self.login = login
        self.password = password
        self.basic_auth_login = basic_auth_login
        self.basic_auth_password = basic_auth_password

        self.session = requests.Session()
        self._login()

        self.tags = Tags(self.session, self.site_url)
        self.categories = Categories(self.session, self.site_url)
        self.products = Products(self.session, self.site_url)
        self.tools = Tools(self.session, self.site_url)
        self.formats = Formats(self.session, self.site_url)
        self.compatibilities = Compatibilities(self.session, self.site_url)
        self.subscriptions = Subscriptions(self.session, self.site_url)
        self.users = Users(self.session, self.site_url)

    def _login(self):
        if self.basic_auth_login and self.basic_auth_password:
            self.session.auth = (self.basic_auth_login, self.basic_auth_password)
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
