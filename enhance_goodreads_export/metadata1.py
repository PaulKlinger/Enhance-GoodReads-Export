# generate bot detection 'metadata1' field for login
# from https://github.com/mkb79/Audible/blob/master/src/audible/metadata.py
# with minor changes
import base64
import binascii
import json
import math
import struct
from datetime import datetime


# key used for encrypt/decrypt metadata1
METADATA_KEY: bytes = b"a\x03\x8fp4\x18\x97\x99:\xeb\xe7\x8b\x85\x97$4"


def raw_xxtea(v: list, n: int, k: list | tuple) -> int:
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


def _bytes_to_longs(data: str | bytes) -> list[int]:
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

    def __init__(self, key: str | bytes) -> None:
        """Initializes the inner class data with the given key.

        Note:
            The key must be 128-bit (16 characters) in length.
        """

        key = key.encode() if isinstance(key, str) else key
        if len(key) != 16:
            raise XXTEAException("Invalid key")
        self.key = struct.unpack("IIII", key)
        assert len(self.key) == 4

    def encrypt(self, data: str | bytes) -> bytes:
        """Encrypts and returns a block of data."""

        ldata = round(len(data) / 4)
        idata = _bytes_to_longs(data)
        if raw_xxtea(idata, ldata, self.key) != 0:
            raise XXTEAException("Cannot encrypt")
        return _longs_to_bytes(idata)

    def decrypt(self, data: str | bytes) -> bytes:
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
    m = METADATA1_TEMPLATE
    m = m.replace("{{USER_AGENT}}", user_agent)
    m = m.replace("{{TIME_NOW}}", str(now_to_unix_ms()))
    m = m.replace("{{LOCATION}}", oauth_url)
    return json.dumps(json.loads(m), separators=(",", ":"))


METADATA1_TEMPLATE = """{"metrics":{"el":1,"script":0,"h":0,"batt":0,"perf":0,"auto":0,"tz":0,"fp2":0,"lsubid":0,"browser":0,"capabilities":0,"gpu":0,"dnt":0,"math":0,"tts":0,"input":0,"canvas":0,"captchainput":0,"pow":0},"start":{{TIME_NOW}},"interaction":{"clicks":1,"touches":0,"keyPresses":3,"cuts":0,"copies":0,"pastes":0,"keyPressTimeIntervals":[3,1041],"mouseClickPositions":["1218,339"],"keyCycles":[2,1,78],"mouseCycles":[119],"touchCycles":[]},"scripts":{"dynamicUrls":["https://images-na.ssl-images-amazon.com/images/I/61XKxrBtDVL._RC|11Y+5x+kkTL.js,01rpauTep4L.js,71OZREKEvmL.js_.js?AUIClients/GoodreadsDefaultDesktopSkin","https://images-na.ssl-images-amazon.com/images/I/21G215oqvfL._RC|21OJDARBhQL.js,218GJg15I8L.js,31lucpmF4CL.js,2119M3Ks9rL.js,51ZYBg5mMxL.js_.js?AUIClients/AuthenticationPortalAssets","https://images-na.ssl-images-amazon.com/images/I/01wGDSlxwdL.js?AUIClients/AuthenticationPortalInlineAssets","https://images-na.ssl-images-amazon.com/images/I/310RLw6gUhL.js?AUIClients/CVFAssets","https://images-na.ssl-images-amazon.com/images/I/81gLkT0N6tL.js?AUIClients/SiegeClientSideEncryptionAUI","https://images-na.ssl-images-amazon.com/images/I/31jdfgcsPAL.js?AUIClients/AmazonUIFormControlsJS","https://images-na.ssl-images-amazon.com/images/I/81dZoozqaGL.js?AUIClients/FWCIMAssets","https://static.siege-amazon.com/prod/profiles/AuthenticationPortalSigninNA.js"],"inlineHashes":[-1746719145,-1820168084,2127743224,-314038750,-962645732,216868775,1424856663,158743496,318224283,-1286394465,585973559,4606827,-1611905557,1800521327,2118020403,1532181211,1718863342,-1978974697],"elapsed":8,"dynamicUrlCount":8,"inlineHashesCount":18},"history":{"length":5},"battery":{},"performance":{"timing":{"connectStart":1652298815320,"navigationStart":1652298815317,"loadEventEnd":1652298815661,"domLoading":1652298815423,"secureConnectionStart":0,"fetchStart":1652298815320,"domContentLoadedEventStart":1652298815652,"responseStart":1652298815418,"responseEnd":1652298815645,"domInteractive":1652298815652,"domainLookupEnd":1652298815320,"redirectStart":0,"requestStart":1652298815323,"unloadEventEnd":1652298815421,"unloadEventStart":1652298815421,"domComplete":1652298815656,"domainLookupStart":1652298815320,"loadEventStart":1652298815657,"domContentLoadedEventEnd":1652298815656,"redirectEnd":0,"connectEnd":1652298815320}},"automation":{"wd":{"properties":{"document":[],"window":[],"navigator":[]}},"phantom":{"properties":{"window":[]}}},"end":1652298836092,"timeZone":0,"flashVersion":null,"plugins":"PDFViewerChromePDFViewerChromiumPDFViewerMicrosoftEdgePDFViewerWebKitbuilt-inPDF||1920-1080-1040-24-*-*-*","dupedPlugins":"PDFViewerChromePDFViewerChromiumPDFViewerMicrosoftEdgePDFViewerWebKitbuilt-inPDF||1920-1080-1040-24-*-*-*","screenInfo":"1920-1080-1040-24-*-*-*","lsUbid":"X03-1953597-7259949:1652297255","referrer":"https://www.goodreads.com/user/sign_in","userAgent":"{{USER_AGENT}}","location":"{{LOCATION}}","webDriver":false,"capabilities":{"css":{"textShadow":1,"WebkitTextStroke":1,"boxShadow":1,"borderRadius":1,"borderImage":1,"opacity":1,"transform":1,"transition":1},"js":{"audio":true,"geolocation":true,"localStorage":"supported","touch":false,"video":true,"webWorker":true},"elapsed":0},"gpu":{"vendor":"GoogleInc.(NVIDIA)","model":"ANGLE(NVIDIA,NVIDIAGeForceGTX1080Direct3D11vs_5_0ps_5_0,D3D11)","extensions":["ANGLE_instanced_arrays","EXT_blend_minmax","EXT_color_buffer_half_float","EXT_disjoint_timer_query","EXT_float_blend","EXT_frag_depth","EXT_shader_texture_lod","EXT_texture_compression_bptc","EXT_texture_compression_rgtc","EXT_texture_filter_anisotropic","WEBKIT_EXT_texture_filter_anisotropic","EXT_sRGB","KHR_parallel_shader_compile","OES_element_index_uint","OES_fbo_render_mipmap","OES_standard_derivatives","OES_texture_float","OES_texture_float_linear","OES_texture_half_float","OES_texture_half_float_linear","OES_vertex_array_object","WEBGL_color_buffer_float","WEBGL_compressed_texture_s3tc","WEBKIT_WEBGL_compressed_texture_s3tc","WEBGL_compressed_texture_s3tc_srgb","WEBGL_debug_renderer_info","WEBGL_debug_shaders","WEBGL_depth_texture","WEBKIT_WEBGL_depth_texture","WEBGL_draw_buffers","WEBGL_lose_context","WEBKIT_WEBGL_lose_context","WEBGL_multi_draw"]},"dnt":null,"math":{"tan":"-1.4214488238747245","sin":"0.8178819121159085","cos":"-0.5753861119575491"},"form":{"email":{"clicks":0,"touches":0,"keyPresses":1,"cuts":0,"copies":0,"pastes":0,"keyPressTimeIntervals":[],"mouseClickPositions":[],"keyCycles":[2],"mouseCycles":[],"touchCycles":[],"width":350,"height":36,"totalFocusTime":0,"prefilled":false},"password":{"clicks":0,"touches":0,"keyPresses":1,"cuts":0,"copies":0,"pastes":0,"keyPressTimeIntervals":[],"mouseClickPositions":[],"keyCycles":[0],"mouseCycles":[],"touchCycles":[],"width":350,"height":36,"totalFocusTime":1,"prefilled":false}},"canvas":{"hash":369257991,"emailHash":-1932815233,"histogramBins":[14000,20,20,25,62,43,16,33,28,125,43,25,23,30,61,23,17,22,138,34,35,26,14,26,55,11,22,29,49,17,40,23,39,17,18,90,44,22,13,32,28,17,21,63,42,18,10,47,24,29,50,44,17,17,7,39,22,24,19,76,39,18,33,15,27,23,37,28,24,18,28,22,126,19,43,12,24,19,21,46,23,16,14,29,29,17,50,63,23,31,18,39,66,17,12,16,34,19,64,88,53,33,526,45,156,35,21,14,18,21,51,20,18,16,37,17,38,18,23,21,23,21,32,19,14,41,66,66,77,85,37,17,43,16,17,16,21,54,22,27,22,21,15,16,25,31,73,21,24,9,57,73,10,102,14,20,18,12,17,13,12,26,16,21,58,10,4,13,25,55,13,21,47,9,14,16,47,12,45,15,7,13,17,121,38,12,11,13,12,51,8,20,15,11,14,56,25,12,64,7,49,11,37,15,54,32,47,39,58,36,13,50,77,13,19,13,14,23,14,31,54,17,18,45,28,22,25,108,56,33,16,49,44,13,29,27,60,27,35,14,42,126,36,25,52,20,113,37,82,34,32,97,29,32,31,13039]},"token":{"isCompatible":true,"pageHasCaptcha":0},"auth":{"form":{"method":"post"}},"errors":[],"version":"4.0.0"}"""
