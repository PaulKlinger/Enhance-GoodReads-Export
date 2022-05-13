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
    "Author l-f",
    "Additional Authors",
    "ISBN",
    "ISBN13",
    "My Rating",
    "Average Rating",
    "Publisher",
    "Binding",
    "Number of Pages",
    "Year Published",
    "Original Publication Year",
    "Date Read",
    "Date Added",
    "Bookshelves",
    "Bookshelves with positions",
    "Exclusive Shelf",
    "My Review",
    "Spoiler",
    "Private Notes",
    "Read Count",
    "Recommended For",
    "Recommended By",
    "Owned Copies",
    "Original Purchase Date",
    "Original Purchase Location",
    "Condition",
    "Condition Description",
    "BCID",
]
