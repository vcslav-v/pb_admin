from requests import Session


class Tags():
    def __init__(self, session: Session, site_url: str) -> None:
        self.session = session
        self.site_url = site_url

    def get(self):
        resp = self.session.get(f'{self.site_url}/admin/tags')
        resp.raise_for_status()
        return resp.json()
