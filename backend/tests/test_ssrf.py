import pytest
from app.core.url_validator import validate_target_url

def test_ssrf_blocks_private_and_loopback_ips():
    """Verify SSRF validator blocks private, loopback, and non-http schemes."""
    with pytest.raises(ValueError, match="Only http and https schemes are permitted"):
        validate_target_url("file:///etc/passwd")

    with pytest.raises(ValueError, match="Only http and https schemes are permitted"):
        validate_target_url("ftp://127.0.0.1/test")

    with pytest.raises(ValueError, match="restricted private/internal IP"):
        validate_target_url("http://127.0.0.1/admin")

    with pytest.raises(ValueError, match="restricted private/internal IP"):
        validate_target_url("http://10.0.0.1/internal")

    with pytest.raises(ValueError, match="restricted private/internal IP"):
        validate_target_url("http://192.168.1.5/config")

def test_ssrf_domain_restriction():
    """Verify SSRF validator enforces allowed competitor domain."""
    with pytest.raises(ValueError, match="does not match allowed competitor domain"):
        validate_target_url("https://malicious-site.com/pricing", allowed_domain="saasify.cloud")

    # Matching domain succeeds
    valid_url = validate_target_url("https://saasify.cloud/pricing", allowed_domain="saasify.cloud")
    assert valid_url == "https://saasify.cloud/pricing"
