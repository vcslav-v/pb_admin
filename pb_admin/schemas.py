from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class ProductType(str, Enum):
    freebie = 'freebie'
    premium = 'premium'
    plus = 'plus'


class Image(BaseModel):
    ident: Optional[int] = None
    mime_type: Optional[str] = None
    original_url: Optional[str] = None
    file_name: Optional[str] = None
    data: Optional[bytes] = None


class Category(BaseModel):
    ident: int
    title: str
    is_display: bool
    headline: Optional[str] = None
    weight: Optional[int] = None
    is_shown_in_filter: bool
    image: Optional[Image] = None
    image_retina: Optional[Image] = None


class Tag(BaseModel):
    ident: Optional[int] = None
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    image: Optional[Image] = None
    no_index: bool = True
    category_ids: list[int] = []


class Feature(BaseModel):
    title: str
    value: str


class Product(BaseModel):
    ident: Optional[int] = None
    product_type: ProductType
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    slug: Optional[str] = None
    is_live: Optional[bool] = False
    size: Optional[str] = None
    show_statistic: Optional[bool] = True
    email_download: Optional[bool] = False
    count_downloads: Optional[int] = 0
    short_description: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[Image] = None
    thumbnail_retina: Optional[Image] = None
    premium_thumbnail: Optional[Image] = None
    premium_thumbnail_retina: Optional[Image] = None
    push_image: Optional[Image] = None
    vps_path: Optional[str] = None
    s3_path: Optional[str] = None
    main_image: Optional[Image] = None
    gallery_images: list[Image] = []
    main_image_retina: Optional[Image] = None
    gallery_images_retina: list[Image] = []
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    features: Optional[list[Feature]] = []
    category_ids: list[int] = []
    format_ids: list[int] = []
    font_ids: list[int] = []
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    tags: Optional[list[int]] = []
    extended_price: Optional[int] = None
    standard_price: Optional[int] = None
    extended_price_old: Optional[int] = None
    standard_price_old: Optional[int] = None
    compatibilities_ids: Optional[list[int]] = []
    inner_description: Optional[str] = None
