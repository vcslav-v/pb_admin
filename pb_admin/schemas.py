from pydantic import BaseModel
from typing import Optional


class Image(BaseModel):
    ident: int
    mime_type: str
    original_url: str
    file_name: str


class Cattegory(BaseModel):
    ident: int
    title: str
    is_display: bool
    headline: Optional[str]
    weight: Optional[int]
    is_shown_in_filter: bool
    image: Optional[Image]
    image_retina: Optional[Image]


class Tag(BaseModel):
    ident: int
    name: Optional[str]
    title: Optional[str]
    description: Optional[str]
    meta_title: Optional[str]
    meta_description: Optional[str]
    image: Optional[Image]
    no_index: bool
    category_ids: list[int]
