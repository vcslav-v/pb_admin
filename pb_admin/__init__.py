"""Main module pb_admin project."""

__version__ = '0.1.41'
__author__ = 'Vaclav_V'
__all__ = ['PbSession', 'schemas']


import aiohttp
import os
from bs4 import BeautifulSoup

from pb_admin.tags import Tags
from pb_admin.categories import Categories
from pb_admin.products import Products
from pb_admin.tools import Tools
from pb_admin.formats import Formats
from pb_admin.subscriptions import Subscriptions
from pb_admin.users import Users
from pb_admin.orders import Orders
from pb_admin.articles import Articles
from pb_admin.creators import Creators
from pb_admin.payments import Payments
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
            edit_mode: bool = False
    ) -> None:
        self.site_url = site_url
        self.login = login
        self.password = password
        self.basic_auth_login = basic_auth_login
        self.basic_auth_password = basic_auth_password

        self.session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(
                basic_auth_login,
                basic_auth_password
            ) if basic_auth_login and basic_auth_password else None,
        )

        self.tags = Tags(self.session, self.site_url, edit_mode)
        self.categories = Categories(self.session, self.site_url, edit_mode)
        self.products = Products(self.session, self.site_url, edit_mode)
        self.tools = Tools(self.session, self.site_url, edit_mode)
        self.formats = Formats(self.session, self.site_url, edit_mode)
        self.subscriptions = Subscriptions(self.session, self.site_url, edit_mode)
        self.users = Users(self.session, self.site_url, edit_mode)
        self.orders = Orders(self.session, self.site_url, edit_mode)
        self.articles = Articles(self.session, self.site_url, edit_mode)
        self.creators = Creators(self.session, self.site_url, edit_mode)
        self.payments = Payments(self.session, self.site_url, edit_mode)

    async def connect(self):
        async with self.session.get(f'{self.site_url}/admin/login') as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(await resp.text(), 'html.parser')
            token = soup.find('input', {'name': '_token'}).get('value')

        payload = {
            'email': self.login,
            'password': self.password,
            'remember': 'on',
            '_token': token
        }
        async with self.session.post(f'{self.site_url}/admin/login', data=payload) as resp:
            resp.raise_for_status()

    async def close(self):
        await self.session.close()

    async def __aenter__(self) -> 'PbSession':
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()
