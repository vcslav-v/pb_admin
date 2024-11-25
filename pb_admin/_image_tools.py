from PIL import Image
from aiohttp import ClientSession
import uuid
import io

from pb_admin import schemas


async def prepare_image(
    image: schemas.Image,
    min_size: tuple[int, int] = [-1, -1],
    max_size: tuple[int, int] = [-1, -1],
    session: ClientSession = None
) -> schemas.Image:
    """Prepare image for upload to Pixelbuddha."""
    if not image.original_url and not image.data:
        raise ValueError('Either original_url or data must be provided.')
    elif image.original_url and not image.data:
        async with session.get(image.original_url) as raw_img:
            raw_img.raise_for_status()
            image.data = await raw_img.read()
            img_file = io.BytesIO(image.data)
    else:
        img_file = io.BytesIO(image.data)
    img = Image.open(img_file)

    # If min_size is provided, check if image is big enough
    if min_size[0] != -1 and img.width < min_size[0]:
        raise ValueError(f'Image width must be at least {min_size[0]}px.')
    if min_size[1] != -1 and img.height < min_size[1]:
        raise ValueError(f'Image height must be at least {min_size[1]}px.')

    # If max_size is provided, check if image is small enough, if not, resize it keeping aspect ratio
    if max_size[0] != -1 and img.width > max_size[0]:
        img.thumbnail((max_size[0], img.height))
    if max_size[1] != -1 and img.height > max_size[1]:
        img.thumbnail((img.width, max_size[1]))

    # Return image in jpeg format, with original filename or random uuid as filename
    img = img.convert('RGB')
    img.save(img_file, format='jpeg')
    image.data = img_file.getvalue()
    img_file.close()
    image.mime_type = 'image/jpeg'
    image.file_name = image.file_name or f'{uuid.uuid4()}.jpg'
    return image


def make_img_field(img: schemas.Image) -> schemas.Image | None:
    if not img:
        return
    if not img.ident:
        return (
            img.file_name,
            img.data,
            img.mime_type
        )
    else:
        return str(img.ident)
