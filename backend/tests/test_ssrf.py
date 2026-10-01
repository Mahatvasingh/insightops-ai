import pytest
import socket
from app.core.url_validator import validate_target_url

def test_ssrf_allowed_exact_and_subdomain():
    assert validate_target_url("https://saasify.cloud/pricing", allowed_domain="saasify.cloud") == "https://saasify.cloud/pricing"
    assert validate_target_url("https://app.saasify.cloud/pricing", allowed_domain="saasify.cloud") == "https://app.saasify.cloud/pricing"

def test_ssrf_substring_domain_bypass_rejected():
    with pytest.raises(ValueError) as exc:
        validate_target_url("https://evil-saasify.cloud.attacker.com/pricing", allowed_domain="saasify.cloud")
    assert "does not match allowed competitor domain" in str(exc.value)

def test_ssrf_private_ip_resolution(monkeypatch):
    # Force live mode for test
    from app.config import settings
    monkeypatch.setattr(settings, "SCRAPER_MODE", "live")

    def mock_getaddrinfo(host, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 80))]

    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)

    with pytest.raises(ValueError) as exc:
        validate_target_url("https://saasify.cloud/internal")
    assert "restricted private/internal IP" in str(exc.value)
