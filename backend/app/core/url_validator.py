import socket
import ipaddress
from urllib.parse import urlparse
from typing import Optional

from app.config import settings

def validate_target_url(url: str, allowed_domain: Optional[str] = None) -> str:
    """
    Validates target URL against SSRF vulnerabilities:
    - Enforces http/https schemes.
    - If allowed_domain is specified, restricts access strictly to exact domain or subdomains.
    - Resolves IP and blocks loopback, private, link-local, multicast, or reserved ranges.
    - In DEMO mode, skips live DNS resolution to support offline/testing environments.
    """
    if not url:
        raise ValueError("URL cannot be empty")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("Only http and https schemes are permitted")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL format: missing hostname")

    clean_host = hostname.lower().strip()

    # Domain restriction check if competitor domain provided
    if allowed_domain:
        clean_allowed = allowed_domain.lower().strip()
        # Strict domain check: exact match or subdomain suffix only! (No substring bypass)
        is_exact = clean_host == clean_allowed
        is_subdomain = clean_host.endswith("." + clean_allowed)
        if not (is_exact or is_subdomain):
            raise ValueError(f"Target URL domain '{hostname}' does not match allowed competitor domain '{allowed_domain}'")

    # In DEMO scraper mode, skip live DNS resolution to support offline/fixtures execution
    if settings.SCRAPER_MODE.lower() == "demo":
        return url

    # IP resolution & SSRF check for live mode
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError(f"Could not resolve hostname '{hostname}': {e}")

    for addr in addr_info:
        ip_str = addr[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_multicast
                or ip_obj.is_reserved
                or ip_obj.is_unspecified
            ):
                raise ValueError(f"Target URL resolves to restricted private/internal IP ({ip_str})")
        except ValueError as err:
            if "restricted" in str(err):
                raise err
            raise ValueError(f"Invalid IP address resolved for hostname '{hostname}': {ip_str}")

    return url
