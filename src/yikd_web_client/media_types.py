"""HTTP body 类型和常用 media type。"""

from enum import Enum


class BodyType(str, Enum):
    none = "none"
    formdata = "formdata"
    urlencoded = "urlencoded"
    raw = "raw"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

    # Java/C# 风格成员。
    Get = "GET"
    Post = "POST"
    Put = "PUT"
    Patch = "PATCH"
    Delete = "DELETE"
    Head = "HEAD"
    Options = "OPTIONS"


class CustomMediaTypeNames:
    class Application:
        FormUrlEncoded = "application/x-www-form-urlencoded"
        Json = "application/json"
        JsonPatch = "application/json-patch+json"
        JsonSequence = "application/json-seq"
        Manifest = "application/manifest+json"
        Octet = "application/octet-stream"
        Pdf = "application/pdf"
        ProblemJson = "application/problem+json"
        ProblemXml = "application/problem+xml"
        Rtf = "application/rtf"
        Soap = "application/soap+xml"
        Wasm = "application/wasm"
        Xml = "application/xml"
        XmlDtd = "application/xml-dtd"
        XmlPatch = "application/xml-patch+xml"
        Zip = "application/zip"

    class Font:
        Collection = "font/collection"
        Otf = "font/otf"
        Sfnt = "font/sfnt"
        Ttf = "font/ttf"
        Woff = "font/woff"
        Woff2 = "font/woff2"

    class Image:
        Avif = "image/avif"
        Bmp = "image/bmp"
        Gif = "image/gif"
        Icon = "image/x-icon"
        Jpeg = "image/jpeg"
        Png = "image/png"
        Svg = "image/svg+xml"
        Tiff = "image/tiff"
        Webp = "image/webp"

    class Multipart:
        ByteRanges = "multipart/byteranges"
        FormData = "multipart/form-data"

    class Text:
        Css = "text/css"
        Csv = "text/csv"
        Html = "text/html"
        JavaScript = "text/javascript"
        Markdown = "text/markdown"
        Plain = "text/plain"
        RichText = "text/richtext"
        Rtf = "text/rtf"
        Xml = "text/xml"


__all__ = ["BodyType", "CustomMediaTypeNames", "HttpMethod"]
