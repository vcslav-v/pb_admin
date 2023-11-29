from requests import Session
from urllib.parse import urlparse, parse_qs
from pb_admin import schemas, _image_tools as image_tools, _config as config
from loguru import logger
from requests_toolbelt import MultipartEncoder
import uuid
from datetime import datetime


class Tags():
    def __init__(self, session: Session, site_url: str) -> None:
        self.session = session
        self.site_url = site_url

    def get_list(self, search: str = None) -> list[schemas.Tag]:
        """Get list of all tags in short version id, name, title, description, meta_title, meta_description, no_index."""
        tags = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search or '',
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/tags', params=params)
            resp.raise_for_status()
            raw_page = resp.json()

            for row in raw_page['resources']:
                values = {cell['attribute']: cell['value'] for cell in row['fields']}
                tags.append(
                    schemas.Tag(
                        ident=values.get('id'),
                        name=values.get('name'),
                        title=values.get('title'),
                        description=values.get('description'),
                        meta_title=values.get('meta_title'),
                        meta_description=values.get('meta_description'),
                        no_index=values.get('no_index'),
                    )
                )

            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))

            else:
                is_next_page = False

        return tags

    def get(self, tag_ident: int) -> schemas.Tag:
        """Get tag by id."""
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
        tag_categories = list(set(raw_categoies['selected']))

        return schemas.Tag(
            ident=values['id'],
            name=values['name'],
            title=values['title'],
            description=values['description'],
            meta_title=values['meta_title'],
            meta_description=values['meta_description'],
            image=img,
            no_index=values['no_index'],
            category_ids=tag_categories,
        )

    def create(self, tag: schemas.Tag, is_lite: bool = False) -> schemas.Tag | None:
        """Create new tag."""
        boundary = str(uuid.uuid4())
        if tag.image:
            tag.image = image_tools.prepare_image(tag.image, config.TAG_IMG_SIZE, config.TAG_IMG_SIZE)
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-XSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-Requested-With': 'XMLHttpRequest',
        }

        fields = {
            'name': tag.name,
            'title': tag.title,
            'description': tag.description,
            'meta_title': tag.meta_title,
            'meta_description': tag.meta_description,
            'no_index': '1' if tag.no_index else '0',
            'categories': str(tag.category_ids),
        }
        if tag.image:
            fields['__media__[meta_image][0]'] = (
                tag.image.file_name,
                tag.image.data,
                tag.image.mime_type
            )
        form = MultipartEncoder(fields, boundary=boundary)
        resp = self.session.post(
            f'{self.site_url}/nova-api/tags?editing=true&editMode=create',
            data=form.to_string(),
            headers=headers,
            allow_redirects=False
        )
        resp.raise_for_status()
        if resp.status_code == 201:
            if is_lite:
                return
            return self.get(resp.json()['resource']['id'])
        else:
            logger.error(resp.text)
            raise Exception(resp.text)

    def delete(self, tag_ident: int) -> None:
        """Delete tag by id."""
        params = {'resources[]': tag_ident}
        headers = {
            'X-CSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-XSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-Requested-With': 'XMLHttpRequest',
        }
        resp = self.session.delete(f'{self.site_url}/nova-api/tags', params=params, headers=headers)
        resp.raise_for_status()

    def update(self, updated_tag: schemas.Tag, is_lite: bool = False) -> schemas.Tag | None:
        """Update tag."""
        if not updated_tag.ident:
            raise Exception('Tag id is required.')
        boundary = str(uuid.uuid4())
        if updated_tag.image and not updated_tag.image.ident:
            updated_tag.image = image_tools.prepare_image(updated_tag.image, config.TAG_IMG_SIZE, config.TAG_IMG_SIZE)
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-XSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-Requested-With': 'XMLHttpRequest',
        }
        if updated_tag.image and not updated_tag.image.ident:
            img_field = (
                updated_tag.image.file_name,
                updated_tag.image.data,
                updated_tag.image.mime_type
            )
        elif updated_tag.image and updated_tag.image.ident:
            img_field = str(updated_tag.image.ident)
        else:
            img_field = None

        fields = {
            'name': updated_tag.name,
            'title': updated_tag.title,
            'description': updated_tag.description,
            'meta_title': updated_tag.meta_title,
            'meta_description': updated_tag.meta_description,
            'no_index': '1' if updated_tag.no_index else '0',
            'categories': str(updated_tag.category_ids),
            '_method': 'PUT',
            '_retrieved_at': str(int(datetime.now().timestamp())),
        }
        if img_field:
            fields['__media__[meta_image][0]'] = img_field

        params = {'editing': 'true', 'editMode': 'update'}

        form = MultipartEncoder(fields, boundary=boundary)
        resp = self.session.post(
            f'{self.site_url}/nova-api/tags/{updated_tag.ident}',
            data=form.to_string(),
            headers=headers,
            allow_redirects=False,
            params=params
        )
        resp.raise_for_status()
        if resp.status_code == 200:
            if is_lite:
                return
            return self.get(resp.json()['resource']['id'])
        else:
            logger.error(resp.text)
            raise Exception(resp.text)

    def bulk_add(self, common_tag_id: int, tag_ids_to_combine: list[int]):
        headers = {
            'X-CSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
        }
        data = {
            'common_tag_id': common_tag_id,
            'tag_ids_to_combine[]': tag_ids_to_combine
        }
        response = self.session.post(f'{self.site_url}/api/bi/tag/combine', headers=headers, data=data)

    @staticmethod
    def get_filled_tag_scheme(name: str, description: str | None = None) -> schemas.Tag:
        title = name.capitalize()
        return schemas.Tag(
            name=name.lower(),
            title=title,
            description=description,
            meta_title=f'Download {title} on Pixelbuddha',
            meta_description=f'Download {title} for free on Pixelbuddha. Browse through our impressive selection of high quality products.',
        )
