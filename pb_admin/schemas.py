from pydantic import BaseModel
from typing import Optional


class Image(BaseModel):
    ident: Optional[int] = None
    mime_type: Optional[str] = None
    original_url: Optional[str] = None
    file_name: Optional[str] = None
    data: Optional[bytes] = None


class Cattegory(BaseModel):
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
