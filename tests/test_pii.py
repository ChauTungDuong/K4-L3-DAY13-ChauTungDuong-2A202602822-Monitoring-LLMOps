from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    """Test Vietnamese CCCD (Căn cước công dân) - 12 digit national ID."""
    cccd_numbers = (
        "001099012345",
        "079200012345",
        "058304056789",
    )
    for cccd in cccd_numbers:
        out = scrub_text(f"CCCD: {cccd}")
        assert cccd not in out
        assert "REDACTED_CCCD" in out


def test_scrub_credit_card() -> None:
    """Test credit card number scrubbing in various formats."""
    cards = (
        "4111 1111 1111 1111",
        "4111-1111-1111-1111",
        "4111111111111111",
        "5500 0000 0000 0004",
    )
    for card in cards:
        out = scrub_text(f"Card: {card}")
        assert card not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_scrub_multiple_pii_in_one_string() -> None:
    """Test that multiple PII types are all redacted from one string."""
    text = "Email a@b.vn phone 0912345678 CCCD 001099012345 card 4111 1111 1111 1111"
    out = scrub_text(text)
    assert "a@b.vn" not in out
    assert "0912345678" not in out
    assert "001099012345" not in out
    assert "4111 1111 1111 1111" not in out
    assert "REDACTED_EMAIL" in out
    assert "REDACTED_PHONE_VN" in out
    assert "REDACTED_CCCD" in out
    assert "REDACTED_CREDIT_CARD" in out
