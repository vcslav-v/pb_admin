from requests import Session
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas
from loguru import logger


class Tags():
    def __init__(self, session: Session, site_url: str) -> None:
        self.session = session
        self.site_url = site_url

    def get(self):
        tag_idents = []
        is_next_page = True
        params = {'perPage': 100}
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/tags', params=params)
            resp.raise_for_status()
            raw_page = resp.json()

            for row in raw_page['resources']:
                tag_idents.append(row['id']['value'])

            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))

            else:
                is_next_page = False

        tags = []
        for tag_ident in tag_idents:
            resp = self.session.get(f'{self.site_url}/nova-api/tags/{tag_ident}')
            resp.raise_for_status()
            raw_tag = resp.json()
            raw_tag_fields = raw_tag['resource']['fields']
            values = {raw_tag_field['attribute']: raw_tag_field['value'] for raw_tag_field in raw_tag_fields}
            if values['meta_image']:
                raw_img = values['meta_image'][0]
                img = schemas.Image(
                    ident=raw_img['id'],
                    mime_type=raw_img['mime_type'],
                    original_url=raw_img['original_url'],
                    file_name=raw_img['file_name']
                )
            else:
                img = None

            resp = self.session.get(
                f'{self.site_url}/nova-vendor/nova-attach-many/tags/{values["id"]}/attachable/categories'
            )
            raw_categoies = resp.json()
            tag_categories = raw_categoies['selected']

            tags.append(schemas.Tag(
                ident=values['id'],
                name=values['name'],
                title=values['title'],
                description=values['description'],
                meta_title=values['meta_title'],
                meta_description=values['meta_description'],
                image=img,
                no_index=values['no_index'],
                category_ids=tag_categories,
            ))
            logger.debug(len(tags))

        return tags
