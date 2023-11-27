from requests import Session
from pb_admin import schemas, _image_tools as image_tools
from urllib.parse import urlparse, parse_qs
import uuid
from datetime import datetime
from loguru import logger
from requests_toolbelt import MultipartEncoder


class Products():
    def __init__(self, session: Session, site_url: str) -> None:
        self.session = session
        self.site_url = site_url

    def get_list(
        self,
        search: str = None,
        category_id: int = None,
    ) -> list[schemas.Product]:
        all_products = []
        all_products.extend(self.get_freebie_list(search, category_id))
        all_products.extend(self.get_premium_list(search, category_id))
        all_products.extend(self.get_plus_list(search, category_id))
        return all_products

    def get_freebie_list(
        self,
        search: str = None,
        category_id: int = None,
        per_page: int = 100,
    ) -> list[schemas.Product]:
        products = []
        is_next_page = True
        params = {
            'perPage': per_page,
            'search': search,
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

    def get_premium_list(
        self,
        search: str = None,
        category_id: int = None,
        per_page: int = 100,
    ) -> list[schemas.Product]:
        products = []
        is_next_page = True
        params = {
            'perPage': per_page,
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

    def get_plus_list(
        self,
        search: str = None,
        category_id: int = None,
        per_page: int = 100,
    ) -> list[schemas.Product]:
        products = []
        is_next_page = True
        params = {
            'perPage': per_page,
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
                card_title = values['options'].get('card_title')
                card_button_link = values['options'].get('card_button_link')
                card_button_text = values['options'].get('card_button_text')
                card_description = values['options'].get('card_description')
                live_preview_link = values['options'].get('live_preview_link')
                live_preview_text = values['options'].get('live_preview_text')
                button_text = values['options'].get('button_text')
                custom_url_title = values['options'].get('custom_url_title')
                custom_url = values['options'].get('custom_url')
                features = [schemas.Feature(
                    title=feature['title'], value=feature['value'], link=feature.get('link')
                ) for feature in values['options'].get('features')] if values['options'].get('features') else []
            else:
                meta_title = None
                meta_description = None
                meta_keywords = None
                author_name = None
                author_url = None
                card_title = None
                card_button_link = None
                card_button_text = None
                card_description = None
                live_preview_link = None
                live_preview_text = None
                button_text = None
                custom_url_title = None
                custom_url = None
                features = []

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
                format_ids=formats_ids,
                font_ids=fonts_ids,
                tags_ids=tags_ids,
                category_ids=categories_ids,
                live_preview_type=values.get('live_preview_type'),
                card_title=card_title,
                card_button_link=card_button_link,
                card_button_text=card_button_text,
                card_description=card_description,
                live_preview_link=live_preview_link,
                live_preview_text=live_preview_text,
                button_text=button_text,
                custom_url_title=custom_url_title,
                custom_url=custom_url,
                old_img=schemas.Image(
                    ident=values['photo_gallery'][0]['id'],
                    mime_type=values['photo_gallery'][0]['mime_type'],
                    original_url=values['photo_gallery'][0]['original_url'],
                    file_name=values['photo_gallery'][0]['file_name'],
                ) if values.get('photo_gallery') else None,
                old_img_retina=schemas.Image(
                    ident=values['photo_gallery_retina'][0]['id'],
                    mime_type=values['photo_gallery_retina'][0]['mime_type'],
                    original_url=values['photo_gallery_retina'][0]['original_url'],
                    file_name=values['photo_gallery_retina'][0]['file_name'],
                ) if values.get('photo_gallery_retina') else None,
                author_id=values.get('author'),
                features=features,
            )
        elif product_type == schemas.ProductType.premium:
            if values.get('options'):
                meta_title = values['options'].get('meta_title')
                meta_description = values['options'].get('meta_description')
                meta_keywords = values['options'].get('meta_keywords')
                description = values['options'].get('description')
                short_description = values['options'].get('short_description')
                features_short = [schemas.FeatureShort(title=feature['title'], value=feature['value']) for feature in values['options'].get('features') if feature.get('title') and feature.get('value')] if values['options'].get('features') else []
                free_sample_link_url = values['options'].get('free_sample_link_url')
                free_sample_link_text = values['options'].get('free_sample_link_text')
                free_sample_description = values['options'].get('free_sample_description')
                download_link_text = values['options'].get('download_link_text')
                download_link_url = values['options'].get('download_link_url')
            else:
                meta_title = None
                meta_description = None
                meta_keywords = None
                description = None
                short_description = None
                features_short = []
                free_sample_link_url = None
                free_sample_link_text = None
                free_sample_description = None
                download_link_text = None
                download_link_url = None

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
                inner_short_description=short_description,
                description=description,
                short_description=values.get('short_description'),
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
                features_short=features_short,
                free_sample_link_url=free_sample_link_url,
                free_sample_link_text=free_sample_link_text,
                free_sample_description=free_sample_description,
                download_link_text=download_link_text,
                download_link_url=download_link_url,
            )
        elif product_type == schemas.ProductType.plus:
            if values.get('options'):
                meta_title = values['options'].get('meta_title')
                meta_description = values['options'].get('meta_description')
                meta_keywords = values['options'].get('meta_keywords')
                author_name = values['options'].get('author_name')
                author_url = values['options'].get('author_link')
                card_title = values['options'].get('card_title')
                card_button_link = values['options'].get('card_button_link')
                card_button_text = values['options'].get('card_button_text')
                card_description = values['options'].get('card_description')
                live_preview_link = values['options'].get('live_preview_link')
                live_preview_text = values['options'].get('live_preview_text')
                button_text = values['options'].get('button_text')
                features = [schemas.Feature(title=feature['title'], value=feature['value'], link=feature.get('link')) for feature in values['options'].get('features')] if values['options'].get('features') else []
            else:
                meta_title = None
                meta_description = None
                meta_keywords = None
                author_name = None
                author_url = None
                card_title = None
                card_button_link = None
                card_button_text = None
                card_description = None
                live_preview_link = None
                live_preview_text = None
                button_text = None
                features = []

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
                format_ids=formats_ids,
                font_ids=fonts_ids,
                tags_ids=tags_ids,
                category_ids=categories_ids,
                card_title=card_title,
                card_button_link=card_button_link,
                card_button_text=card_button_text,
                card_description=card_description,
                live_preview_link=live_preview_link,
                live_preview_text=live_preview_text,
                button_text=button_text,
                old_img=schemas.Image(
                    ident=values['photo_gallery'][0]['id'],
                    mime_type=values['photo_gallery'][0]['mime_type'],
                    original_url=values['photo_gallery'][0]['original_url'],
                    file_name=values['photo_gallery'][0]['file_name'],
                ) if values.get('photo_gallery') else None,
                old_img_retina=schemas.Image(
                    ident=values['photo_gallery_retina'][0]['id'],
                    mime_type=values['photo_gallery_retina'][0]['mime_type'],
                    original_url=values['photo_gallery_retina'][0]['original_url'],
                    file_name=values['photo_gallery_retina'][0]['file_name'],
                ) if values.get('photo_gallery_retina') else None,
                author_id=values.get('author'),
                features=features,
            )

        if not is_lite and product.category_ids:
            if product.product_type == schemas.ProductType.premium:
                product.url = f'{self.site_url}/premium/{product.slug}'
            else:
                main_category_id = min(product.category_ids)
                category_resp = self.session.get(
                    f'{self.site_url}/nova-api/categories/{main_category_id}'
                )
                raw_category = category_resp.json()
                raw_category_name = raw_category['resource']['title'].lower()
                product.url = f'{self.site_url}/{raw_category_name}/{product.slug}'

        return product

    def update(self, product: schemas.Product, is_lite: bool = False) -> schemas.Product | None:
        """Update product."""
        if not product.ident:
            raise ValueError('Product id is required')
        boundary = str(uuid.uuid4())
        product = self._preapre_imgs(product)
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-XSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-Requested-With': 'XMLHttpRequest',
        }
        params = {'editing': 'true', 'editMode': 'update'}
        if product.product_type == schemas.ProductType.freebie:
            fields = {
                'title': product.title,
                'created_at': product.created_at.strftime("%Y-%m-%d %H:%M:%S.%f") if product.created_at else None,
                'slug': product.slug,
                'status': '1' if product.is_live else '0',
                'size': product.size,
                'short_description': product.short_description,
                'description': product.description,
                'show_stats': '1' if product.show_statistic else '0',
                'email_download': '1' if product.email_download else '0',
                'count_downloads': str(product.count_downloads) if product.count_downloads else None,
                'vps_path': product.vps_path,
                's3_path': product.s3_path,
                'options[custom_url]': product.custom_url,
                'options[custom_url_title]': product.custom_url_title,
                'options[author_name]': product.author_name,
                'options[author_link]': product.author_url,
                'options[card_title]': product.card_title,
                'options[card_button_link]': product.card_button_link,
                'options[card_button_text]': product.card_button_text,
                'options[card_description]': product.card_description,
                'options[button_text]': product.button_text,
                'live_preview_type': product.live_preview_type,
                'options[live_preview_text]': product.live_preview_text,
                'options[live_preview_link]': product.live_preview_link,
                'options[features]': f"[{', '.join([f.model_dump_json() for f in product.features])}]",
                'categories': str(product.category_ids),
                'formats': str(product.format_ids),
                'fonts': str(product.font_ids),
                'options[meta_title]': product.meta_title,
                'options[meta_description]': product.meta_description,
                'options[meta_keywords]': product.meta_keywords,
                'tags': str(product.tags_ids),
                'author': str(product.author_id) if product.author_id else None,
                'author_trashed': 'false',
                'options[download_text]': None,
                '_method': 'PUT',
                '_retrieved_at': str(int(datetime.now().timestamp())),
            }
            for i, img in enumerate(product.gallery_images):
                fields[f'__media__[photo_gallery_2][{i}]'] = image_tools.make_img_field(img)
            for i, img in enumerate(product.gallery_images_retina):
                fields[f'__media__[photo_gallery_2_retina][{i}]'] = image_tools.make_img_field(img)
            if product.old_img:
                fields['__media__[photo_gallery][0]'] = image_tools.make_img_field(product.old_img)
            if product.old_img_retina:
                fields['__media__[photo_gallery_retina][0]'] = image_tools.make_img_field(product.old_img_retina)
            if product.main_image:
                fields['__media__[single_image][0]'] = image_tools.make_img_field(product.main_image)
            if product.main_image_retina:
                fields['__media__[single_image_retina][0]'] = image_tools.make_img_field(product.main_image_retina)
            if product.thumbnail:
                fields['__media__[material_image][0]'] = image_tools.make_img_field(product.thumbnail)
            if product.thumbnail_retina:
                fields['__media__[material_image_retina][0]'] = image_tools.make_img_field(product.thumbnail_retina)
            if product.push_image:
                fields['__media__[push_image][0]'] = image_tools.make_img_field(product.push_image)

            form = MultipartEncoder(fields, boundary=boundary)
            resp = self.session.post(
                f'{self.site_url}/nova-api/freebies/{product.ident}',
                headers=headers,
                data=form.to_string(),
                params=params,
                allow_redirects=False,
            )
            resp.raise_for_status()
            if is_lite:
                return
            return self.get(product.ident, schemas.ProductType.freebie)
        elif product.product_type == schemas.ProductType.plus:
            fields = {
                'title': product.title,
                'created_at': product.created_at.strftime("%Y-%m-%d %H:%M:%S.%f") if product.created_at else None,
                'slug': product.slug,
                'status': '1' if product.is_live else '0',
                'short_description': product.short_description,
                'description': product.description,
                'size': product.size,
                'show_stats': '1' if product.show_statistic else '0',
                'count_downloads': str(product.count_downloads) if product.count_downloads else None,
                'author': str(product.author_id) if product.author_id else None,
                'author_trashed': 'false',
                'options[download_text]': None,
                'vps_path': product.vps_path,
                's3_path': product.s3_path,
                'options[author_name]': product.author_name,
                'options[author_link]': product.author_url,
                'options[card_title]': product.card_title,
                'options[card_description]': product.card_description,
                'options[card_button_text]': product.card_button_text,
                'options[card_button_link]': product.card_button_link,
                'options[button_text]': product.button_text,
                'live_preview_type': product.live_preview_type,
                'options[live_preview_text]': product.live_preview_text,
                'options[live_preview_link]': product.live_preview_link,
                'options[features]': f"[{', '.join([f.model_dump_json() for f in product.features])}]",
                'categories': str(product.category_ids),
                'formats': str(product.format_ids),
                'fonts': str(product.font_ids),
                'options[meta_title]': product.meta_title,
                'options[meta_description]': product.meta_description,
                'options[meta_keywords]': product.meta_keywords,
                'tags': str(product.tags_ids),
                '_method': 'PUT',
                '_retrieved_at': str(int(datetime.now().timestamp())),
            }
            if product.main_image:
                fields['__media__[single_image][0]'] = image_tools.make_img_field(product.main_image)
            if product.main_image_retina:
                fields['__media__[single_image_retina][0]'] = image_tools.make_img_field(product.main_image_retina)
            for i, img in enumerate(product.gallery_images):
                fields[f'__media__[photo_gallery_2][{i}]'] = image_tools.make_img_field(img)
            for i, img in enumerate(product.gallery_images_retina):
                fields[f'__media__[photo_gallery_2_retina][{i}]'] = image_tools.make_img_field(img)
            if product.old_img:
                fields['__media__[photo_gallery][0]'] = image_tools.make_img_field(product.old_img)
            if product.old_img_retina:
                fields['__media__[photo_gallery_retina][0]'] = image_tools.make_img_field(product.old_img_retina)
            if product.thumbnail:
                fields['__media__[material_image][0]'] = image_tools.make_img_field(product.thumbnail)
            if product.thumbnail_retina:
                fields['__media__[material_image_retina][0]'] = image_tools.make_img_field(product.thumbnail_retina)
            if product.push_image:
                fields['__media__[push_image][0]'] = image_tools.make_img_field(product.push_image)

            form = MultipartEncoder(fields, boundary=boundary)
            resp = self.session.post(
                f'{self.site_url}/nova-api/pluses/{product.ident}',
                headers=headers,
                data=form.to_string(),
                params=params,
                allow_redirects=False,
            )
            resp.raise_for_status()
            if is_lite:
                return
            return self.get(product.ident, schemas.ProductType.plus)        
        elif product.product_type == schemas.ProductType.premium:
            fields = {
                'title': product.title,
                'created_at': product.created_at.strftime("%Y-%m-%d %H:%M:%S.%f") if product.created_at else None,
                'slug': product.slug,
                'status': '1' if product.is_live else '0',
                'short_description': product.short_description,
                'price_extended': str(product.extended_price) if product.extended_price else None,
                'price_standard': str(product.standard_price) if product.standard_price else None,
                'price_extended_old': str(product.extended_price_old) if product.extended_price_old else None,
                'price_standard_old': str(product.standard_price_old) if product.standard_price_old else None,
                'options[download_text]': None,
                'vps_path': product.vps_path,
                's3_path': product.s3_path,                
                'options[short_description]': product.inner_short_description,
                'options[description]': product.description,
                'options[free_sample_link_text]': product.free_sample_link_text,
                'options[free_sample_link_url]': product.free_sample_link_url,
                'options[free_sample_description]': product.free_sample_description,
                'options[download_link_text]': product.download_link_text,
                'options[download_link_url]': product.download_link_url,
                'categories': str(product.category_ids),
                'compatibilities': str(product.compatibilities_ids),
                'tags': str(product.tags_ids),
                'options[meta_title]': product.meta_title,
                'options[meta_description]': product.meta_description,
                'options[meta_keywords]': product.meta_keywords,
                'options[features]': f"[{', '.join([f.model_dump_json() for f in product.features_short])}]",
                '_method': 'PUT',
                '_retrieved_at': str(int(datetime.now().timestamp())),
            }
            if product.thumbnail:
                fields['__media__[material_image][0]'] = image_tools.make_img_field(product.thumbnail)
            if product.thumbnail_retina:
                fields['__media__[material_image_retina][0]'] = image_tools.make_img_field(product.thumbnail_retina)
            if product.premium_thumbnail:
                fields['__media__[material_image_for_catalog][0]'] = image_tools.make_img_field(product.premium_thumbnail)
            if product.premium_thumbnail_retina:
                fields['__media__[material_image_retina_for_catalog][0]'] = image_tools.make_img_field(product.premium_thumbnail_retina)
            if product.push_image:
                fields['__media__[push_image][0]'] = image_tools.make_img_field(product.push_image)
            if product.main_image:
                fields['__media__[premium_main][0]'] = image_tools.make_img_field(product.main_image)
            if product.main_image_retina:
                fields['__media__[premium_main_retina][0]'] = image_tools.make_img_field(product.main_image_retina)
            for i, img in enumerate(product.gallery_images):
                fields[f'__media__[premium_slider][{i}]'] = image_tools.make_img_field(img)
            for i, img in enumerate(product.gallery_images_retina):
                fields[f'__media__[premium_slider_retina][{i}]'] = image_tools.make_img_field(img)

            form = MultipartEncoder(fields, boundary=boundary)
            resp = self.session.post(
                f'{self.site_url}/nova-api/premia/{product.ident}',
                headers=headers,
                data=form.to_string(),
                params=params,
                allow_redirects=False,
            )
            resp.raise_for_status()
            if is_lite:
                return
            return self.get(product.ident, schemas.ProductType.premium)


    def _preapre_imgs(self, product: schemas.Product) -> schemas.Product:
        product.thumbnail = image_tools.prepare_image(product.thumbnail) if product.thumbnail and not product.thumbnail.ident else product.thumbnail
        product.thumbnail_retina = image_tools.prepare_image(product.thumbnail_retina) if product.thumbnail_retina and not product.thumbnail_retina.ident else product.thumbnail_retina
        product.premium_thumbnail = image_tools.prepare_image(product.premium_thumbnail) if product.premium_thumbnail and not product.premium_thumbnail.ident else product.premium_thumbnail
        product.premium_thumbnail_retina = image_tools.prepare_image(product.premium_thumbnail_retina) if product.premium_thumbnail_retina and not product.premium_thumbnail_retina.ident else product.premium_thumbnail_retina
        product.push_image = image_tools.prepare_image(product.push_image) if product.push_image and not product.push_image.ident else product.push_image
        product.main_image = image_tools.prepare_image(product.main_image) if product.main_image and not product.main_image.ident else product.main_image
        product.main_image_retina = image_tools.prepare_image(product.main_image_retina) if product.main_image_retina and not product.main_image_retina.ident else product.main_image_retina
        product.old_img = image_tools.prepare_image(product.old_img) if product.old_img and not product.old_img.ident else product.old_img
        product.old_img_retina = image_tools.prepare_image(product.old_img_retina) if product.old_img_retina and not product.old_img_retina.ident else product.old_img_retina
        product.gallery_images = [image_tools.prepare_image(img) if img and not img.ident else img for img in product.gallery_images]
        product.gallery_images_retina = [image_tools.prepare_image(img) if img and not img.ident else img for img in product.gallery_images_retina]
        return product
