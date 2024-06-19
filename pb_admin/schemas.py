from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class ProductType(str, Enum):
    freebie = 'freebie'
    premium = 'premium'
    plus = 'plus'


class SubscriptionStatus(str, Enum):
    ACTIVE = 'Active'
    CANCEL = 'Cancel'
    EXPIRED = 'Expired'


class SubscriptionPeriod(str, Enum):
    LIFETIME = 'Lifetime'
    YEAR = 'Year'
    MONTH = 'Month'


class Format(BaseModel):
    ident: int
    title: str = None


class Compatibility(BaseModel):
    ident: int
    title: str
    alias: Optional[str] = None
    color: Optional[str] = None


class Subscription(BaseModel):
    ident: int
    subscription_id: Optional[str] = None
    status: SubscriptionStatus
    period: Optional[SubscriptionPeriod] = None
    resubscribe: bool
    user_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Image(BaseModel):
    ident: Optional[int] = None
    mime_type: Optional[str] = None
    original_url: Optional[str] = None
    file_name: Optional[str] = None
    data: Optional[bytes] = None
    alt: Optional[str] = None


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
    relevanted_tags_ids: list[int] = []
    sub_tags_ids: list[int] = []
    is_group: bool = False


class FeatureShort(BaseModel):
    title: str
    value: str


class Feature(FeatureShort):
    link: Optional[str] = None


class Product(BaseModel):
    ident: Optional[int] = None
    product_type: ProductType
    url: Optional[str] = None
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
    tags_ids: Optional[list[int]] = []
    extended_price: Optional[int] = None
    standard_price: Optional[int] = None
    extended_price_old: Optional[int] = None
    standard_price_old: Optional[int] = None
    compatibilities_ids: Optional[list[int]] = []
    inner_short_description: Optional[str] = None

    free_sample_link_url: Optional[str] = None
    free_sample_link_text: Optional[str] = None
    free_sample_description: Optional[str] = None

    live_preview_type: Optional[str] = 'link'
    card_title: Optional[str] = None
    card_button_link: Optional[str] = None
    card_button_text: Optional[str] = None
    card_description: Optional[str] = None
    live_preview_link: Optional[str] = None
    live_preview_text: Optional[str] = None
    button_text: Optional[str] = None

    custom_url_title: Optional[str] = None
    custom_url: Optional[str] = None

    old_img: Optional[Image] = None
    old_img_retina: Optional[Image] = None

    download_link_text: Optional[str] = None
    download_link_url: Optional[str] = None

    author_id: Optional[int] = None

    features_short: Optional[list[FeatureShort]] = []


class PbUser(BaseModel):
    ident: int
    name: str
    email: str


class Order(BaseModel):
    ident: int
    is_payed: bool
    count: int
    price: float
    discounted_price: float
    user_id: Optional[int] = None
    created_at: datetime
    product_id: Optional[int] = None
    user_subscription_id: Optional[int] = None
    coupon: Optional[str] = None
    is_extended_license: bool


class ArticleType(str, Enum):
    text = 'text'
    card = 'card'
    video = 'video'
    quote = 'quote'
    image = 'image'


class ArticleText(BaseModel):
    layout: ArticleType
    key: str
    value: str = ''


class ArticleCard(BaseModel):
    layout: ArticleType
    key: str
    title: str = ''
    description: str = ''
    button_text: str = ''
    link_url: str = ''
    link_text: str = ''


class ArticleVideo(BaseModel):
    layout: ArticleType
    key: str
    title: str = ''
    link: str = ''


class ArticleQuote(BaseModel):
    layout: ArticleType
    key: str
    text: str = ''
    link_text: str = ''
    author_link: str = ''
    author_job: str = ''


class ArticleImage(BaseModel):
    layout: ArticleType
    key: str
    image_link: str = ''
    in_new_tab: bool = False
    nofollow: bool = False
    image_alt: str = ''
    image_title: str = ''


class Article(BaseModel):
    ident: Optional[int] = None
    created_at: Optional[datetime] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    is_live: Optional[bool] = None
    is_sponsored: Optional[bool] = None
    show_statistic: Optional[bool] = None
    count_views: Optional[int] = None
    author_id: Optional[int] = None

    short_description: Optional[str] = None
    thumbnail: Optional[Image] = None
    thumbnail_retina: Optional[Image] = None
    push_image: Optional[Image] = None
    main_image: Optional[Image] = None
    main_image_retina: Optional[Image] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    category_ids: list[int] = []

    content: list[ArticleText | ArticleCard | ArticleVideo | ArticleQuote | ArticleImage] = []


class ProductLayoutImg(BaseModel):
    ident: str | None = None
    img_id: int | None = None
    img_n: int | None = None


class ProductLayoutVideo(BaseModel):
    ident: str | None = None
    title: str
    link: str


class NewProductType(int, Enum):
    freebie = 0
    plus = 1
    premium = 2


class CreatorLite(BaseModel):
    ident: int
    name: str
    link: str | None = None


class Creator(CreatorLite):
    ident: int | None = None
    description: str
    avatar: Image | None = None


class NewProductLite(BaseModel):
    ident: int
    title: str
    slug: str
    created_at: datetime
    is_live: bool
    product_type: NewProductType
    only_registered_download: bool = False
    creator_id: int | None
    size: str
    category_id: int


class NewProduct(NewProductLite):
    ident: int | None = None
    slug: str | None
    excerpt: str
    description: str
    price_commercial_cent: int | None
    price_extended_cent: int | None
    price_commercial_sale_cent: int | None
    price_extended_sale_cent: int | None
    thumbnail: Image | None
    push_image: Image | None
    images: list[Image] = []
    presentation: list[list[ProductLayoutImg | ProductLayoutVideo]] = []
    vps_path: str | None
    s3_path: str | None
    tags_ids: list[int] = []
    font_ids: list[int] = []
    formats: str | None
    custom_btn_text: str | None = None
    custom_btn_url: str | None = None
    meta_title: str | None
    meta_description: str | None
    meta_keywords: str | None
