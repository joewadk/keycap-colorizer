import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit


class IntakeError(ValueError):
    """A product page cannot be safely or reliably read."""


def normalize_url(value: str) -> str:
    try:
        parts = urlsplit(value.strip())
        port = parts.port
        host = (parts.hostname or "").rstrip(".").encode("idna").decode("ascii").lower()
    except (ValueError, UnicodeError) as error:
        raise IntakeError("Invalid product URL.") from error
    if parts.scheme.lower() not in {"http", "https"} or not host:
        raise IntakeError("Use an absolute HTTP or HTTPS product URL.")
    if parts.username is not None or parts.password is not None:
        raise IntakeError("Product URLs must not contain credentials.")
    if port not in {None, 80, 443}:
        raise IntakeError("Only standard HTTP and HTTPS ports are supported.")
    if host == "localhost" or host.endswith((".localhost", ".local")):
        raise IntakeError("Local network URLs are not supported.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise IntakeError("Private network URLs are not supported.")
    if any(character.isspace() or ord(character) < 32 for character in value.strip()):
        raise IntakeError("URLs must not contain whitespace or control characters.")
    host_part = f"[{host}]" if ":" in host else host
    scheme = parts.scheme.lower()
    if port and port != (443 if scheme == "https" else 80):
        host_part += f":{port}"
    return urlunsplit((scheme, host_part, parts.path or "/", parts.query, ""))


async def require_public_url(url: str) -> str:
    normalized = normalize_url(url)
    host = urlsplit(normalized).hostname
    try:
        records = await asyncio.to_thread(socket.getaddrinfo, host, None, type=socket.SOCK_STREAM)
    except OSError as error:
        raise IntakeError("Could not resolve the product host.") from error
    if not records or any(not ipaddress.ip_address(record[4][0]).is_global for record in records):
        raise IntakeError("Product hosts must resolve to public addresses.")
    return normalized
