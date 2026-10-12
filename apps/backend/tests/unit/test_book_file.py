from router.book import inline_disposition


def test_plain_ascii_name_is_quoted():
    assert inline_disposition("saltmere.pdf") == 'inline; filename="saltmere.pdf"'


def test_non_ascii_name_gets_an_ascii_fallback_and_rfc5987_name():
    header = inline_disposition("Café – Guide.pdf")
    assert header.startswith('inline; filename="Caf_ _ Guide.pdf"')
    assert "filename*=UTF-8''Caf%C3%A9%20%E2%80%93%20Guide.pdf" in header


def test_quotes_slashes_and_control_characters_are_removed():
    header = inline_disposition('a"b/c\\d\r\ne.pdf')
    assert header == 'inline; filename="abcde.pdf"'


def test_empty_name_falls_back():
    assert inline_disposition('"/') == 'inline; filename="document.pdf"'
