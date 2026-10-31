"""Tests for the official Paytm checksum integration."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.routes_payment import _generate_checksum, _verify_checksum

KEY = "1234567890123456"
PARAMS = {"MID": "TESTMID", "ORDER_ID": "DS_TEST123", "TXN_AMOUNT": "299.00"}


def test_checksum_matches_official_library():
    from paytmchecksum import PaytmChecksum

    # Paytm checksums use a random salt, so verify interoperability instead of equality.
    ours = _generate_checksum(PARAMS, KEY)
    assert PaytmChecksum.verifySignature(PARAMS, KEY, ours) is True
    assert _verify_checksum(PARAMS, KEY, PaytmChecksum.generateSignature(PARAMS, KEY)) is True


def test_checksum_round_trip():
    checksum = _generate_checksum(PARAMS, KEY)
    assert checksum
    assert _verify_checksum(PARAMS, KEY, checksum) is True


def test_checksum_rejects_tampering():
    checksum = _generate_checksum(PARAMS, KEY)
    tampered = dict(PARAMS, TXN_AMOUNT="1.00")
    assert _verify_checksum(tampered, KEY, checksum) is False
    assert _verify_checksum(PARAMS, KEY, "") is False
