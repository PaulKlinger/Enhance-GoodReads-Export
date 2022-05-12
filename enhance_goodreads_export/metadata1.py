# generate bot detection 'metadata1' field for login
# from https://github.com/mkb79/Audible/blob/master/src/audible/metadata.py
# with minor changes
import base64
import binascii
import json
import math
import os
import struct
from datetime import datetime
from typing import Union


# key used for encrypt/decrypt metadata1
METADATA_KEY: bytes = b"a\x03\x8fp4\x18\x97\x99:\xeb\xe7\x8b\x85\x97$4"


def raw_xxtea(v: list, n: int, k: Union[list, tuple]) -> int:
    assert isinstance(v, list)
    assert isinstance(k, (list, tuple))
    assert isinstance(n, int)

    def mx():
        return ((z >> 5) ^ (y << 2)) + ((y >> 3) ^ (z << 4)) ^ (sum_ ^ y) + (
            k[(p & 3) ^ e] ^ z
        )

    def u32(x):
        return x % 2**32

    y = v[0]
    sum_ = 0
    delta = 2654435769
    if n > 1:  # Encoding
        z = v[n - 1]
        q = int(6 + (52 / n // 1))
        while q > 0:
            q -= 1
            sum_ = u32(sum_ + delta)
            e = u32(sum_ >> 2) & 3
            p = 0
            while p < n - 1:
                y = v[p + 1]
                z = v[p] = u32(v[p] + mx())
                p += 1
            y = v[0]
            z = v[n - 1] = u32(v[n - 1] + mx())
        return 0

    if n < -1:  # Decoding
        n = -n
        q = int(6 + (52 / n // 1))
        sum_ = u32(q * delta)
        while sum_ != 0:
            e = u32(sum_ >> 2) & 3
            p = n - 1
            while p > 0:
                z = v[p - 1]
                y = v[p] = u32(v[p] - mx())
                p -= 1
            z = v[n - 1]
            y = v[0] = u32(v[0] - mx())
            sum_ = u32(sum_ - delta)
        return 0
    return 1


def _bytes_to_longs(data: Union[str, bytes]) -> list[int]:
    data_bytes = data.encode() if isinstance(data, str) else data

    return [
        int.from_bytes(data_bytes[i : i + 4], "little")
        for i in range(0, len(data_bytes), 4)
    ]


def _longs_to_bytes(data: list[int]) -> bytes:
    return b"".join([i.to_bytes(4, "little") for i in data])


def _generate_hex_checksum(data: str) -> str:
    checksum = binascii.crc32(data.encode()) % 2**32
    checksum_str = format(checksum, "X")

    if len(checksum_str) < 8:
        pad = (8 - len(checksum_str)) * "0"
        checksum_str = pad + checksum_str

    return checksum_str


class XXTEAException(Exception):
    pass


class XXTEA:
    """XXTEA wrapper class.

    Easy to use and compatible (by duck typing) with the Blowfish class.

    Note:
        Partial copied from https://github.com/andersekbom/prycut and ported
        from PY2 to PY3
    """

    def __init__(self, key: Union[str, bytes]) -> None:
        """Initializes the inner class data with the given key.

        Note:
            The key must be 128-bit (16 characters) in length.
        """

        key = key.encode() if isinstance(key, str) else key
        if len(key) != 16:
            raise XXTEAException("Invalid key")
        self.key = struct.unpack("IIII", key)
        assert len(self.key) == 4

    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """Encrypts and returns a block of data."""

        ldata = round(len(data) / 4)
        idata = _bytes_to_longs(data)
        if raw_xxtea(idata, ldata, self.key) != 0:
            raise XXTEAException("Cannot encrypt")
        return _longs_to_bytes(idata)

    def decrypt(self, data: Union[str, bytes]) -> bytes:
        """Decrypts and returns a block of data."""

        ldata = round(len(data) / 4)
        idata = _bytes_to_longs(data)
        if raw_xxtea(idata, -ldata, self.key) != 0:
            raise XXTEAException("Cannot decrypt")
        return _longs_to_bytes(idata).rstrip(b"\0")


metadata_crypter = XXTEA(METADATA_KEY)


def encrypt_metadata(metadata: str) -> str:
    """Encrypts metadata to be used to log in to Amazon"""

    checksum = _generate_hex_checksum(metadata)
    object_str = f"{checksum}#{metadata}"
    object_enc = metadata_crypter.encrypt(object_str)
    object_base64 = base64.b64encode(object_enc).decode()

    return f"ECdITeCs:{object_base64}"


def decrypt_metadata(metadata: str) -> str:
    """Decrypts metadata for testing purposes only."""

    object_base64 = metadata.lstrip("ECdITeCs:")
    object_bytes = base64.b64decode(object_base64)
    object_dec = metadata_crypter.decrypt(object_bytes)
    object_str = object_dec.decode()
    checksum, metadata = object_str.split("#", 1)
    assert _generate_hex_checksum(metadata) == checksum

    return metadata


def now_to_unix_ms() -> int:
    return math.floor(datetime.now().timestamp() * 1000)


def meta_goodreads_desktop(user_agent: str, oauth_url: str) -> str:
    """
    Returns json-formatted metadata to simulate sign-in from goodreads desktop
    """
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(cur_dir, "login_metadata.json")) as f:
        m = f.read()
    m = m.replace("{{USER_AGENT}}", user_agent)
    m = m.replace("{{TIME_NOW}}", str(now_to_unix_ms()))
    m = m.replace("{{LOCATION}}", oauth_url)
    return json.dumps(json.loads(m), separators=(",", ":"))
