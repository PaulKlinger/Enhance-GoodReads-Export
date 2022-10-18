from .entities import AbsoluteUrl


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    " Chrome/101.0.4951.54 Safari/537.36"
)
BOOK_URL = AbsoluteUrl("https://www.goodreads.com/book/show/")
BASE_URL = AbsoluteUrl("https://www.goodreads.com")
SIGNIN_URL = AbsoluteUrl("https://www.goodreads.com/user/sign_in")
SIGNIN_POST_URL = AbsoluteUrl("https://www.goodreads.com/ap/signin")


STANDARD_FIELDNAMES = [
    "Book Id",
    "Title",
    "Author",
    "Date Read",
    "Exclusive Shelf",
]
