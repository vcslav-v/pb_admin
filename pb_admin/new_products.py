from requests import Session
from pb_admin import schemas, _image_tools as image_tools
from urllib.parse import urlparse, parse_qs
import uuid
from datetime import datetime, timezone
from loguru import logger
from requests_toolbelt import MultipartEncoder
import re
import json


def get_id_form_options(value: str, options: list[dict]) -> int:
    for option in options:
        if option['value'] == int(value):
            return option['value']
    return None


class Products():
    def __init__(self, session: Session, site_url: str, edit_mode: bool) -> None:
        self.session = session
        self.site_url = site_url
        self.edit_mode = edit_mode

    def get_list(
        self,
        search: str = None,
        per_page: int = 100,
    ) -> list[schemas.NewProductLite]:
        products = []
        is_next_page = True
        params = {
            'perPage': per_page,
            'search': search,
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/products', params=params)
            resp.raise_for_status()
            raw_page = resp.json()

            for row in raw_page['resources']:
                values = {}
                for cell in row['fields']:
                    if cell.get('attribute') == 'creator':
                        values['creator_id'] = cell['belongsToId']
                    elif cell.get('attribute') == 'category':
                        values['category_id'] = cell['belongsToId']
                    elif cell.get('attribute') == 'type':
                        values['product_type'] = schemas.NewProductType(
                            [o['value'] for o in cell['options'] if o['label'] == cell['value']][0]
                        )
                    else:
                        values[cell['attribute']] = cell['value']
                products.append(
                    schemas.NewProductLite(
                        ident=values.get('id'),
                        title=values.get('title'),
                        product_type=values.get('product_type'),
                        created_at=values.get('created_at'),
                        is_live=values.get('status'),
                        creator_id=values.get('creator_id'),
                        category_id=values.get('category_id'),
                        is_special=values.get('special'),
                    )
                )
            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))
            else:
                is_next_page = False
        return products

    def get(self, product_ident: int) -> schemas.NewProduct:
        """Get product by id."""
        params = {
            'editing': 'true',
            'editMode': 'update',
            'viaResource': None,
            'viaResourceId': None,
            'viaRelationship': None,
        }
        resp = self.session.get(
            f'{self.site_url}/nova-api/products/{product_ident}/update-fields',
            params=params
        )
        resp.raise_for_status()
        raw_product = resp.json()
        raw_product_fields = raw_product['fields'][0]['fields']
        values = {}
        for cell in raw_product_fields:
            if cell.get('attribute') == 'creator':
                values['creator_id'] = cell['belongsToId']
            elif cell.get('attribute') == 'category':
                values['category_id'] = cell['belongsToId']
            elif cell.get('attribute') == 'type':
                values['product_type'] = schemas.NewProductType(cell['value'])
            elif cell.get('attribute') in ['thumbnail', 'push_image']:
                if not cell['value']:
                    values[cell['attribute']] = None
                    continue
                values[cell['attribute']] = schemas.Image(
                    ident=cell['value'][0]['id'],
                    mime_type=cell['value'][0]['mime_type'],
                    original_url=cell['value'][0]['original_url'],
                    file_name=cell['value'][0]['file_name'],
                    alt=cell['value'][0]['custom_properties'].get('alt') if cell['value'][0]['custom_properties'] else None,
                )
            elif cell.get('attribute') == 'images':
                values['images'] = [schemas.Image(
                    ident=c['id'],
                    mime_type=c['mime_type'],
                    original_url=c['original_url'],
                    file_name=c['file_name'],
                    alt=c['custom_properties'].get('alt') if c['custom_properties'] else None,
                ) for c in cell['value']]
            elif cell.get('attribute') == 'presentation':
                values['presentation'] = []
                for i, placeholder in enumerate(cell['value']):
                    placeholder_values = {}
                    for placeholder_value in placeholder['attributes']:
                        if placeholder_value.get('attribute') == 'image':
                            placeholder_values['image_id'] = get_id_form_options(
                                placeholder_value['value'],
                                placeholder_value['options']
                            )
                        else:
                            placeholder_values[placeholder_value['attribute']] = placeholder_value['value']
                    if i == 0 or placeholder_values['new_row'] is True:
                        values['presentation'].append([])
                    if placeholder.get('layout') == 'image':
                        values['presentation'][-1].append(
                            schemas.ProductLayoutImg(
                                ident=str(placeholder['key']),
                                img_id=placeholder_values['image_id'],
                            )
                        )
                    elif placeholder.get('layout') == 'video':
                        values['presentation'][-1].append(
                            schemas.ProductLayoutVideo(
                                ident=placeholder['key'],
                                title=placeholder_values['title'],
                                link=placeholder_values['link'],
                            )
                        )

            elif cell.get('attribute') in ['s3_path', 'vps_path']:
                if cell.get('component') != 'file-field':
                    continue
                values[cell['attribute']] = cell['value']
            elif cell.get('attribute') == 'options':
                for opt_field in cell['fields']:
                    values[opt_field['attribute']] = opt_field['value']
            else:
                values[cell['attribute']] = cell['value']

        values['tag_ids'] = self._get_tag_ids(product_ident)
        values['font_ids'] = self._get_fonts(product_ident)
        product = schemas.NewProduct(
            ident=str(product_ident),
            title=values.get('title'),
            slug=values.get('slug'),
            created_at=values.get('created_at'),
            is_special=values.get('special'),
            is_live=values.get('status'),
            product_type=values.get('product_type'),
            only_registered_download=values.get('only_registered_download'),
            creator_id=values.get('creator_id'),
            size=values.get('size'),
            category_id=values.get('category_id'),
            excerpt=values.get('excerpt'),
            description=values.get('description'),
            price_commercial_cent=self._price_to_cents(values.get('price_commercial')),
            price_extended_cent=self._price_to_cents(values.get('price_extended')),
            price_commercial_sale_cent=self._price_to_cents(values.get('price_commercial_sale')),
            price_extended_sale_cent=self._price_to_cents(values.get('price_extended_sale')),
            thumbnail=values.get('thumbnail'),
            push_image=values.get('push_image'),
            images=values.get('images'),
            presentation=values.get('presentation'),
            vps_path=values.get('vps_path'),
            s3_path=values.get('s3_path'),
            formats=values.get('formats'),
            tags_ids=values.get('tag_ids'),
            font_ids=values.get('font_ids'),
            custom_btn_text=values.get('custom_btn_text'),
            custom_btn_url=values.get('custom_btn_url'),
            meta_title=values.get('meta_title'),
            meta_description=values.get('meta_description'),
            meta_keywords=values.get('meta_keywords'),
        )
        return product

    def update(self, product: schemas.NewProduct, is_lite: bool = False) -> schemas.NewProduct | None:
        """Update product."""
        if not self.edit_mode:
            raise ValueError('Edit mode is required')
        if not product.ident:
            raise ValueError('Product id is required')
        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-XSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-Requested-With': 'XMLHttpRequest',
        }
        params = {'editing': 'true', 'editMode': 'update'}
        fields = {
            'title': product.title,
            'created_at': product.created_at.strftime("%Y-%m-%d %H:%M:%S.%f") if product.created_at else datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"),
            'slug': self._get_slug(product.title, product.slug),
            'status': '1' if product.is_live else '0',
            'type': str(product.product_type.value),
            'only_registered_download': '1' if product.only_registered_download else '0',
            'creator': str(product.creator_id),
            'creator_trashed': 'false',
            'special': '1' if product.is_special else '0',
            'excerpt': product.excerpt,
            'description': product.description,
            'size': product.size,
            'price_commercial': self._cents_to_price(product.price_commercial_cent),
            'price_extended': self._cents_to_price(product.price_extended_cent),
            'price_commercial_sale': self._cents_to_price(product.price_commercial_sale_cent),
            'price_extended_sale': self._cents_to_price(product.price_extended_sale_cent),
            '___nova_flexible_content_fields': '["presentation"]',
            'presentation': self._get_presentation(product.presentation, product.images),
            'vps_path': product.vps_path,
            's3_path': product.s3_path,
            'category': str(product.category_id),
            'category_trashed': 'false',
            'tags': str(product.tags_ids),
            'options[formats]': product.formats,
            'options[custom_btn_text]': product.custom_btn_text,
            'options[custom_btn_url]': product.custom_btn_url,
            'fonts': str(product.font_ids) if product.font_ids else None,
            'options[meta_title]': product.meta_title,
            'options[meta_description]': product.meta_description,
            'options[meta_keywords]': product.meta_keywords,
            '_method': 'PUT',
            '_retrieved_at': str(int(datetime.now(tz=timezone.utc).timestamp()))
        }
        if product.thumbnail:
            fields['__media__[thumbnail][0]'] = image_tools.make_img_field(product.thumbnail)
            if product.thumbnail.alt:
                fields['__media-custom-properties__[thumbnail][0][alt]'] = product.thumbnail.alt
        if product.push_image:
            fields['__media__[push_image][0]'] = image_tools.make_img_field(product.push_image)
            if product.push_image.alt:
                fields['__media-custom-properties__[push_image][0][alt]'] = product.push_image.alt
        for i, img in enumerate(product.images):
            fields[f'__media__[images][{i}]'] = image_tools.make_img_field(img)
            if img.alt:
                fields[f'__media-custom-properties__[images][{i}][alt]'] = img.alt
        form = MultipartEncoder(fields, boundary=boundary)
        resp = self.session.post(
            f'{self.site_url}/nova-api/products/{product.ident}',
            headers=headers,
            data=form.to_string(),
            params=params,
            allow_redirects=False,
        )
        resp.raise_for_status()
        if is_lite:
            return
        return self.get(product.ident)

    def create(self, product: schemas.NewProduct, is_lite: bool = False) -> schemas.NewProduct | None:
        """Create product."""
        if not self.edit_mode:
            raise ValueError('Edit mode is required')
        if product.ident:
            raise ValueError('Product id is not required')
        boundary = str(uuid.uuid4())
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-CSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-XSRF-TOKEN': self.session.cookies.get('XSRF-TOKEN'),
            'X-Requested-With': 'XMLHttpRequest',
        }
        params = {'editing': 'true', 'editMode': 'create'}
        fields = {
            'title': product.title,
            'created_at': product.created_at.strftime("%Y-%m-%d %H:%M:%S") if product.created_at else datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            'slug': self._get_slug(product.title, product.slug),
            'status': '1' if product.is_live else '0',
            'type': str(product.product_type.value),
            'only_registered_download': '1' if product.only_registered_download else '0',
            'creator': str(product.creator_id),
            'creator_trashed': 'false',
            'excerpt': product.excerpt,
            'description': product.description,
            'size': product.size,
            'price_commercial': self._cents_to_price(product.price_commercial_cent),
            'price_extended': self._cents_to_price(product.price_extended_cent),
            'price_commercial_sale': self._cents_to_price(product.price_commercial_sale_cent),
            'price_extended_sale': self._cents_to_price(product.price_extended_sale_cent),
            '___nova_flexible_content_fields': '["presentation"]',
            'presentation': None,
            'vps_path': product.vps_path,
            's3_path': product.s3_path,
            'category': str(product.category_id),
            'category_trashed': 'false',
            'tags': str(product.tags_ids),
            'options[formats]': product.formats,
            'options[custom_btn_text]': product.custom_btn_text,
            'options[custom_btn_url]': product.custom_btn_url,
            'fonts': str(product.font_ids) if product.font_ids else None,
            'options[meta_title]': product.meta_title,
            'options[meta_description]': product.meta_description,
            'options[meta_keywords]': product.meta_keywords,
            'viaResource': None,
            'viaResourceId': None,
            'viaRelationship': None,
        }
        if product.thumbnail:
            fields['__media__[thumbnail][0]'] = image_tools.make_img_field(product.thumbnail)
            if product.thumbnail.alt:
                fields['__media-custom-properties__[thumbnail][0][alt]'] = product.thumbnail.alt
        if product.push_image:
            fields['__media__[push_image][0]'] = image_tools.make_img_field(product.push_image)
            if product.push_image.alt:
                fields['__media-custom-properties__[push_image][0][alt]'] = product.push_image.alt
        for i, img in enumerate(product.images):
            fields[f'__media__[images][{i}]'] = image_tools.make_img_field(img)
            if img.alt:
                fields[f'__media-custom-properties__[images][{i}][alt]'] = img.alt
        form = MultipartEncoder(fields, boundary=boundary)
        resp = self.session.post(
            f'{self.site_url}/nova-api/products',
            headers=headers,
            data=form.to_string(),
            params=params,
            allow_redirects=False,
        )
        resp.raise_for_status()
        new_product = self.get(resp.json()['id'])
        new_product.presentation = product.presentation
        return self.update(new_product, is_lite=is_lite)

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

    def _get_tag_ids(self, product_ident: int) -> list[int]:
        tag_ids = []
        is_next_page = True
        params = {
            'perPage': 100,
            'viaResource': 'products',
            'viaResourceId': product_ident,
            'viaRelationship': 'tags',
            'relationshipType': 'morphToMany'
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/tags', params=params)
            resp.raise_for_status()
            raw_page = resp.json()
            for row in raw_page['resources']:
                tag_ids.append(row['id']['value'])
            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))
            else:
                is_next_page = False
        return tag_ids

    def _get_fonts(self, product_ident: int) -> list[int]:
        font_ids = []
        is_next_page = True
        params = {
            'perPage': 100,
            'viaResource': 'products',
            'viaResourceId': product_ident,
            'viaRelationship': 'fonts',
            'relationshipType': 'morphToMany'
        }
        while is_next_page:
            resp = self.session.get(f'{self.site_url}/nova-api/fonts', params=params)
            resp.raise_for_status()
            raw_page = resp.json()
            for row in raw_page['resources']:
                font_ids.append(row['id']['value'])
            if raw_page.get('next_page_url'):
                parsed_url = urlparse(raw_page.get('next_page_url'))
                params.update(parse_qs(parsed_url.query))
            else:
                is_next_page = False
        return font_ids

    def _price_to_cents(self, price: int | None) -> int | None:
        if price is None:
            return price
        return price * 100

    def _cents_to_price(self, price: int | None) -> int | None:
        if price is None:
            return price
        return str(price // 100)

    def _get_slug(self, title: str, slug: str | None = None) -> str:
        raw_slug = slug or title
        raw_slug = raw_slug.strip().lower()
        raw_slug = re.sub(r'[^a-z0-9 -]', '-', raw_slug)
        raw_slug = re.sub(r'\s+', '-', raw_slug)
        raw_slug = re.sub(r'-+', '-', raw_slug)
        return raw_slug

    def _get_presentation(self, presentation: list, images: list[schemas.Image]) -> str:
        result = []
        is_first_row = True
        for row in presentation:

            if not is_first_row:
                new_row = '1'
            else:
                new_row = '0'
                is_first_row = False

            for placeholder in row:
                if isinstance(placeholder, schemas.ProductLayoutImg):
                    key = placeholder.ident or f'{str(uuid.uuid4()).replace("-", "")}-image'
                    result.append({
                        'layout': 'image',
                        'key': key,
                        'attributes': {
                            f'{key}__image': placeholder.img_id or images[placeholder.img_n].ident,
                            f'{key}__new_row': new_row,
                        }
                    })
                elif isinstance(placeholder, schemas.ProductLayoutVideo):
                    key = placeholder.ident or f'{str(uuid.uuid4()).replace("-", "")}-video'
                    result.append({
                        'layout': 'video',
                        'key': key,
                        'attributes': {
                            f'{key}__title': placeholder.title,
                            f'{key}__link': placeholder.link,
                            f'{key}__new_row': new_row,
                        }
                    })
                new_row = '0'
        return json.dumps(result)
