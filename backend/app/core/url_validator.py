import socket
import ipaddress
from urllib.parse import urlparse
from typing import Optional

def validate_target_url(url: str, allowed_domain: Optional[str] = None) -> str:
    """
    Validates target URL against SSRF vulnerabilities:
    - Enforces http/https schemes.
    - Resolves IP and blocks loopback, private, link-local, multicast, or reserved ranges.
    - If allowed_domain is specified, restricts access to that domain or its subdomains.
    """
    if not url:
        raise ValueError("URL cannot be empty")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("Only http and https schemes are permitted")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL format: missing hostname")

    # Domain restriction check if competitor domain provided
    if allowed_domain:
        clean_allowed = allowed_domain.lower().strip()
        clean_host = hostname.lower().strip()
        if not (clean_host == clean_allowed or clean_host.endswith("." + clean_allowed) or clean_allowed in clean_host):
            raise ValueError(f"Target URL domain '{hostname}' does not match allowed competitor domain '{allowed_domain}'")

    # IP resolution & SSRF check
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
            # If ipaddress fails to parse, treat as invalid
            raise ValueError(f"Invalid IP address resolved for hostname '{hostname}': {ip_str}")

    return url
