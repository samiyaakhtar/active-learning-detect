from enum import Enum, unique


@unique
class ImageFileType(Enum):
    GIF = ".gif"
    PNG = ".png"
    JPG = ".jpg"
    JPEG = ".jpeg"

    @classmethod
    def is_supported_filetype(cls, value):
        return any(value.lower() == item.value.lower() for item in cls)
