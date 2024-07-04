from requests import Session
from pb_admin import schemas
from urllib.parse import urlparse, parse_qs


class Categories():
    def __init__(self, session: Session, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    def get_list(self, search: str = '', is_lite: bool = True) -> list[schemas.Category]:
        """Get list of all categories in short version id, title, is_display, headline, weight, is_shown_in_filter."""
        categories = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search,
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/categories', params=params)
            resp.raise_for_status()
            raw_page = resp.json()
            for row in raw_page['resources']:
                values = {cell['attribute']: cell['value'] for cell in row['fields']}
                categories.append(
                    schemas.Category(
                        ident=values.get('id'),
                        title=values.get('title'),
                        is_display=values.get('display_menu'),
                        headline=values.get('headline'),
                        weight=values.get('sort'),
                        is_shown_in_filter=values.get('show_in_filter'),
                        image=schemas.Image(
                            ident=values['category_image'][0]['id'],
                            mime_type=values['category_image'][0]['mime_type'],
                            original_url=values['category_image'][0]['original_url'],
                            file_name=values['category_image'][0]['file_name'],
                        ) if values.get('category_image') else None,
                        image_retina=schemas.Image(
                            ident=values['category_image_retina'][0]['id'],
                            mime_type=values['category_image_retina'][0]['mime_type'],
                            original_url=values['category_image_retina'][0]['original_url'],
                            file_name=values['category_image_retina'][0]['file_name'],
                        ) if values.get('category_image_retina') else None,
                        )
                    )

            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))
            else:
                is_next_page = False
        if is_lite:
            return categories

        for category in categories:
            params = {
                'editing': True,
                'editMode': 'update',
                'viaResource': '',
                'viaResourceId': '',
                'viaRelationship': '',
            }
            resp = self.session.get(f'{self.site_url}/nova-api/categories/{category.ident}/update-fields', params=params)
            resp.raise_for_status()
            raw_data = resp.json()
            values = {cell['attribute']: cell['value'] for cell in raw_data['fields'][0]['fields']}
            category.slug = values.get('slug')
        return categories
