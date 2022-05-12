from collections.abc import Callable
from typing import NewType

AbsoluteUrl = NewType("AbsoluteUrl", str)
RelativeUrl = NewType("RelativeUrl", str)
IsoDateStr = NewType("IsoDateStr", str)
Path = NewType("Path", str)

CaptchaSolver = Callable[[bytes], str]


class EnhanceExportException(Exception):
    def __init__(self, message):
        self.message = message
