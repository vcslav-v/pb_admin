from requests import Session
from pb_admin import schemas
from urllib.parse import urlparse, parse_qs


class Products():
    def __init__(self, session: Session, site_url: str) -> None:
        self.session = session
        self.site_url = site_url

    def get_list(self, search: str = None, category_id: int = None) -> list[schemas.Product]:
        all_products = []
        all_products.extend(self.get_freebie_list(search, category_id))
        all_products.extend(self.get_premium_list(search, category_id))
        all_products.extend(self.get_plus_list(search, category_id))
        return all_products

    def get_freebie_list(self, search: str = None, category_id: int = None) -> list[schemas.Product]:
        products = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search
        }
        if category_id:
            params.update(
                {
                    'viaResource': 'categories',
                    'viaResourceId': category_id,
                    'viaRelationship': 'freebies',
                    'relationshipType': 'morphToMany'
                }
            )
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/freebies', params=params)
            resp.raise_for_status()
            raw_page = resp.json()

            for row in raw_page['resources']:
                values = {cell['attribute']: cell['value'] for cell in row['fields']}
                products.append(
                    schemas.Product(
                        ident=values.get('id'),
                        product_type=schemas.ProductType.freebie,
                        title=values.get('title'),
                        created_at=values.get('created_at'),
                        slug=values.get('slug'),
                        is_live=True if values.get('status') == 'Live' else False,
                        size=values.get('size'),
                        show_statistic=values.get('show_statistic'),
                        email_download=values.get('email_download'),
                        count_downloads=values.get('count_downloads'),
                        author=values.get('author'),
                    )
                )
            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))
            else:
                is_next_page = False
        return products

    def get_premium_list(self, search: str = None, category_id: int = None) -> list[schemas.Product]:
        products = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search
        }
        if category_id:
            params.update(
                {
                    'viaResource': 'categories',
                    'viaResourceId': category_id,
                    'viaRelationship': 'premiums',
                    'relationshipType': 'morphToMany'
                }
            )
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/premia', params=params)
            resp.raise_for_status()
            raw_page = resp.json()

            for row in raw_page['resources']:
                values = {cell['attribute']: cell['value'] for cell in row['fields']}
                products.append(
                    schemas.Product(
                        ident=values.get('id'),
                        product_type=schemas.ProductType.premium,
                        title=values.get('title'),
                        created_at=values.get('created_at'),
                        slug=values.get('slug'),
                        is_live=True if values.get('status') == 'Live' else False,
                        extended_price=values.get('price_extended'),
                        standard_price=values.get('price_standard'),
                        extended_price_old=values.get('price_extended_old'),
                        standard_price_old=values.get('price_standard_old'),
                    )
                )
            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))
            else:
                is_next_page = False
        return products

    def get_plus_list(self, search: str = None, category_id: int = None) -> list[schemas.Product]:
        products = []
        is_next_page = True
        params = {
            'perPage': 100,
            'search': search
        }
        if category_id:
            params.update(
                {
                    'viaResource': 'categories',
                    'viaResourceId': category_id,
                    'viaRelationship': 'pluses',
                    'relationshipType': 'morphToMany'
                }
            )
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/pluses', params=params)
            resp.raise_for_status()
            raw_page = resp.json()

            for row in raw_page['resources']:
                values = {cell['attribute']: cell['value'] for cell in row['fields']}
                products.append(
                    schemas.Product(
                        ident=values.get('id'),
                        product_type=schemas.ProductType.plus,
                        title=values.get('title'),
                        created_at=values.get('created_at'),
                        slug=values.get('slug'),
                        is_live=True if values.get('status') == 'Live' else False,
                        size=values.get('size'),
                        show_statistic=values.get('show_statistic'),
                        count_downloads=values.get('count_downloads'),
                        author=values.get('author'),
                    )
                )
            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))
            else:
                is_next_page = False
        return products

    def get(self, product_ident: int, product_type: schemas.ProductType, is_lite: bool = False) -> schemas.Product:
        #TODO: check work for old products
        """Get product by id."""
        if product_type == schemas.ProductType.freebie:
            resp = self.session.get(f'{self.site_url}/nova-api/freebies/{product_ident}')
        elif product_type == schemas.ProductType.premium:
            resp = self.session.get(f'{self.site_url}/nova-api/premia/{product_ident}')
        elif product_type == schemas.ProductType.plus:
            resp = self.session.get(f'{self.site_url}/nova-api/pluses/{product_ident}')
        else:
            raise ValueError(f'Unknown product type: {product_type}')
        resp.raise_for_status()
        raw_product = resp.json()
        raw_product_fields = raw_product['resource']['fields']
        values = {
            raw_product_field['attribute']: raw_product_field['value'] for raw_product_field in raw_product_fields if raw_product_field.get('attribute')
        }

        if product_type == schemas.ProductType.freebie:
            if values.get('options'):
                meta_title = values['options'].get('meta_title')
                meta_description = values['options'].get('meta_description')
                meta_keywords = values['options'].get('meta_keywords')
                author_name = values['options'].get('author_name')
                author_url = values['options'].get('author_link')
            else:
                meta_title = None
                meta_description = None
                meta_keywords = None
                author_name = None
                author_url = None

            if not is_lite:
                categories_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/freebies/{values["id"]}/attachable/categories'
                )
                raw_categoies = categories_resp.json()
                categories_ids = list(set(raw_categoies['selected']))

                formats_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/freebies/{values["id"]}/attachable/formats'
                )
                raw_formats = formats_resp.json()
                formats_ids = list(set(raw_formats['selected']))

                fonts_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/freebies/{values["id"]}/attachable/fonts'
                )
                raw_fonts = fonts_resp.json()
                fonts_ids = list(set(raw_fonts['selected']))

                tags_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/freebies/{values["id"]}/attachable/tags'
                )
                raw_tags = tags_resp.json()
                tags_ids = list(set(raw_tags['selected']))
            else:
                categories_ids = []
                formats_ids = []
                fonts_ids = []
                tags_ids = []

            product = schemas.Product(
                ident=values['id'],
                product_type=schemas.ProductType.freebie,
                title=values['title'],
                created_at=values['created_at'],
                slug=values['slug'],
                is_live=True if values.get('status') == 'Live' else False,
                size=values.get('size'),
                show_statistic=values.get('show_stats'),
                email_download=values.get('email_download'),
                count_downloads=values.get('count_downloads'),
                short_description=values.get('short_description'),
                description=values.get('description'),
                vps_path=values.get('vps_path'),
                s3_path=values.get('s3_path'),
                meta_title=meta_title,
                meta_description=meta_description,
                meta_keywords=meta_keywords,
                author_name=author_name,
                author_url=author_url,
                thumbnail=schemas.Image(
                    ident=values['material_image'][0]['id'],
                    mime_type=values['material_image'][0]['mime_type'],
                    original_url=values['material_image'][0]['original_url'],
                    file_name=values['material_image'][0]['file_name'],
                ) if values.get('material_image') else None,
                thumbnail_retina=schemas.Image(
                    ident=values['material_image_retina'][0]['id'],
                    mime_type=values['material_image_retina'][0]['mime_type'],
                    original_url=values['material_image_retina'][0]['original_url'],
                    file_name=values['material_image_retina'][0]['file_name'],
                ) if values.get('material_image_retina') else None,
                push_image=schemas.Image(
                    ident=values['push_image'][0]['id'],
                    mime_type=values['push_image'][0]['mime_type'],
                    original_url=values['push_image'][0]['original_url'],
                    file_name=values['push_image'][0]['file_name'],
                ) if values.get('push_image') else None,
                main_image=schemas.Image(
                    ident=values['single_image'][0]['id'],
                    mime_type=values['single_image'][0]['mime_type'],
                    original_url=values['single_image'][0]['original_url'],
                    file_name=values['single_image'][0]['file_name'],
                ) if values.get('single_image') else None,
                main_image_retina=schemas.Image(
                    ident=values['single_image_retina'][0]['id'],
                    mime_type=values['single_image_retina'][0]['mime_type'],
                    original_url=values['single_image_retina'][0]['original_url'],
                    file_name=values['single_image_retina'][0]['file_name'],
                ) if values.get('single_image_retina') else None,
                gallery_images=[
                    schemas.Image(
                        ident=raw_img['id'],
                        mime_type=raw_img['mime_type'],
                        original_url=raw_img['original_url'],
                        file_name=raw_img['file_name'],
                    ) for raw_img in values['photo_gallery_2']
                ] if values.get('photo_gallery_2') else [],
                gallery_images_retina=[
                    schemas.Image(
                        ident=raw_img['id'],
                        mime_type=raw_img['mime_type'],
                        original_url=raw_img['original_url'],
                        file_name=raw_img['file_name'],
                    ) for raw_img in values['photo_gallery_2_retina']
                ] if values.get('photo_gallery_2_retina') else [],
                formats_ids=formats_ids,
                fonts_ids=fonts_ids,
                tags_ids=tags_ids,
                category_ids=categories_ids,
            )
        elif product_type == schemas.ProductType.premium:
            if values.get('options'):
                meta_title = values['options'].get('meta_title')
                meta_description = values['options'].get('meta_description')
                meta_keywords = values['options'].get('meta_keywords')
                description = values['options'].get('description')
                short_description = values['options'].get('short_description')
                features = [schemas.Feature(title=feature['title'], value=feature['value']) for feature in values['options'].get('features')] if values['options'].get('features') else []
            else:
                meta_title = None
                meta_description = None
                meta_keywords = None
                description = None
                short_description = None

            if not is_lite:
                categories_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/premia/{values["id"]}/attachable/categories'
                )
                raw_categoies = categories_resp.json()
                categories_ids = list(set(raw_categoies['selected']))

                tags_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/premia/{values["id"]}/attachable/tags'
                )
                raw_tags = tags_resp.json()
                tags_ids = list(set(raw_tags['selected']))

                compatibilities_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/premia/{values["id"]}/attachable/compatibilities'
                )
                raw_compatibilities = compatibilities_resp.json()
                compatibilities_ids = list(set(raw_compatibilities['selected']))
            else:
                categories_ids = []
                tags_ids = []
                compatibilities_ids = []

            product = schemas.Product(
                ident=values['id'],
                product_type=schemas.ProductType.premium,
                title=values['title'],
                created_at=values['created_at'],
                slug=values['slug'],
                is_live=True if values.get('status') == 'Live' else False,
                extended_price=values.get('price_extended'),
                standard_price=values.get('price_standard'),
                extended_price_old=values.get('price_extended_old'),
                standard_price_old=values.get('price_standard_old'),
                short_description=short_description,
                description=description,
                inner_description=values.get('short_description'),
                vps_path=values.get('vps_path'),
                s3_path=values.get('s3_path'),
                meta_title=meta_title,
                meta_description=meta_description,
                meta_keywords=meta_keywords,
                thumbnail=schemas.Image(
                    ident=values['material_image'][0]['id'],
                    mime_type=values['material_image'][0]['mime_type'],
                    original_url=values['material_image'][0]['original_url'],
                    file_name=values['material_image'][0]['file_name'],
                ) if values.get('material_image') else None,
                thumbnail_retina=schemas.Image(
                    ident=values['material_image_retina'][0]['id'],
                    mime_type=values['material_image_retina'][0]['mime_type'],
                    original_url=values['material_image_retina'][0]['original_url'],
                    file_name=values['material_image_retina'][0]['file_name'],
                ) if values.get('material_image_retina') else None,
                premium_thumbnail=schemas.Image(
                    ident=values['material_image_for_catalog'][0]['id'],
                    mime_type=values['material_image_for_catalog'][0]['mime_type'],
                    original_url=values['material_image_for_catalog'][0]['original_url'],
                    file_name=values['material_image_for_catalog'][0]['file_name'],
                ) if values.get('material_image_for_catalog') else None,
                premium_thumbnail_retina=schemas.Image(
                    ident=values['material_image_retina_for_catalog'][0]['id'],
                    mime_type=values['material_image_retina_for_catalog'][0]['mime_type'],
                    original_url=values['material_image_retina_for_catalog'][0]['original_url'],
                    file_name=values['material_image_retina_for_catalog'][0]['file_name'],
                ) if values.get('material_image_retina_for_catalog') else None,
                push_image=schemas.Image(
                    ident=values['push_image'][0]['id'],
                    mime_type=values['push_image'][0]['mime_type'],
                    original_url=values['push_image'][0]['original_url'],
                    file_name=values['push_image'][0]['file_name'],
                ) if values.get('push_image') else None,
                main_image=schemas.Image(
                    ident=values['premium_main'][0]['id'],
                    mime_type=values['premium_main'][0]['mime_type'],
                    original_url=values['premium_main'][0]['original_url'],
                    file_name=values['premium_main'][0]['file_name'],
                ) if values.get('premium_main') else None,
                main_image_retina=schemas.Image(
                    ident=values['premium_main_retina'][0]['id'],
                    mime_type=values['premium_main_retina'][0]['mime_type'],
                    original_url=values['premium_main_retina'][0]['original_url'],
                    file_name=values['premium_main_retina'][0]['file_name'],
                ) if values.get('premium_main_retina') else None,
                gallery_images=[
                    schemas.Image(
                        ident=raw_img['id'],
                        mime_type=raw_img['mime_type'],
                        original_url=raw_img['original_url'],
                        file_name=raw_img['file_name'],
                    ) for raw_img in values['premium_slider']
                ] if values.get('premium_slider') else [],
                gallery_images_retina=[
                    schemas.Image(
                        ident=raw_img['id'],
                        mime_type=raw_img['mime_type'],
                        original_url=raw_img['original_url'],
                        file_name=raw_img['file_name'],
                    ) for raw_img in values['premium_slider_retina']
                ] if values.get('premium_slider_retina') else [],
                tags_ids=tags_ids,
                category_ids=categories_ids,
                compatibilities_ids=compatibilities_ids,
                features=features,
            )
        elif product_type == schemas.ProductType.plus:
            if values.get('options'):
                meta_title = values['options'].get('meta_title')
                meta_description = values['options'].get('meta_description')
                meta_keywords = values['options'].get('meta_keywords')
                author_name = values['options'].get('author_name')
                author_url = values['options'].get('author_link')
            else:
                meta_title = None
                meta_description = None
                meta_keywords = None
                author_name = None
                author_url = None

            if not is_lite:
                categories_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/pluses/{values["id"]}/attachable/categories'
                )
                raw_categoies = categories_resp.json()
                categories_ids = list(set(raw_categoies['selected']))

                formats_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/pluses/{values["id"]}/attachable/formats'
                )
                raw_formats = formats_resp.json()
                formats_ids = list(set(raw_formats['selected']))

                fonts_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/pluses/{values["id"]}/attachable/fonts'
                )
                raw_fonts = fonts_resp.json()
                fonts_ids = list(set(raw_fonts['selected']))

                tags_resp = self.session.get(
                    f'{self.site_url}/nova-vendor/nova-attach-many/pluses/{values["id"]}/attachable/tags'
                )
                raw_tags = tags_resp.json()
                tags_ids = list(set(raw_tags['selected']))
            else:
                categories_ids = []
                formats_ids = []
                fonts_ids = []
                tags_ids = []

            product = schemas.Product(
                ident=values['id'],
                product_type=schemas.ProductType.plus,
                title=values['title'],
                created_at=values['created_at'],
                slug=values['slug'],
                is_live=True if values.get('status') == 'Live' else False,
                size=values.get('size'),
                show_statistic=values.get('show_stats'),
                count_downloads=values.get('count_downloads'),
                short_description=values.get('short_description'),
                description=values.get('description'),
                vps_path=values.get('vps_path'),
                s3_path=values.get('s3_path'),
                thumbnail=schemas.Image(
                    ident=values['material_image'][0]['id'],
                    mime_type=values['material_image'][0]['mime_type'],
                    original_url=values['material_image'][0]['original_url'],
                    file_name=values['material_image'][0]['file_name'],
                ) if values.get('material_image') else None,
                thumbnail_retina=schemas.Image(
                    ident=values['material_image_retina'][0]['id'],
                    mime_type=values['material_image_retina'][0]['mime_type'],
                    original_url=values['material_image_retina'][0]['original_url'],
                    file_name=values['material_image_retina'][0]['file_name'],
                ) if values.get('material_image_retina') else None,
                push_image=schemas.Image(
                    ident=values['push_image'][0]['id'],
                    mime_type=values['push_image'][0]['mime_type'],
                    original_url=values['push_image'][0]['original_url'],
                    file_name=values['push_image'][0]['file_name'],
                ) if values.get('push_image') else None,
                main_image=schemas.Image(
                    ident=values['single_image'][0]['id'],
                    mime_type=values['single_image'][0]['mime_type'],
                    original_url=values['single_image'][0]['original_url'],
                    file_name=values['single_image'][0]['file_name'],
                ) if values.get('single_image') else None,
                main_image_retina=schemas.Image(
                    ident=values['single_image_retina'][0]['id'],
                    mime_type=values['single_image_retina'][0]['mime_type'],
                    original_url=values['single_image_retina'][0]['file_name'],
                    file_name=values['single_image_retina'][0]['file_name'],
                ) if values.get('single_image_retina') else None,
                gallery_images=[
                    schemas.Image(
                        ident=raw_img['id'],
                        mime_type=raw_img['mime_type'],
                        original_url=raw_img['original_url'],
                        file_name=raw_img['file_name'],
                    ) for raw_img in values['photo_gallery_2']
                ] if values.get('photo_gallery_2') else [],
                gallery_images_retina=[
                    schemas.Image(
                        ident=raw_img['id'],
                        mime_type=raw_img['mime_type'],
                        original_url=raw_img['original_url'],
                        file_name=raw_img['file_name'],
                    ) for raw_img in values['photo_gallery_2_retina']
                ] if values.get('photo_gallery_2_retina') else [],
                meta_title=meta_title,
                meta_description=meta_description,
                meta_keywords=meta_keywords,
                author_name=author_name,
                author_url=author_url,
                formats_ids=formats_ids,
                fonts_ids=fonts_ids,
                tags_ids=tags_ids,
                category_ids=categories_ids,
            )

        return product