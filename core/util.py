from datetime import datetime
from socket import AF_INET, AF_INET6, SOCK_DGRAM, socket
import sys
from types import EllipsisType
from typing import Any, TypeVar


_T = TypeVar('_T')
def cast(name: str, value: Any, to: type[_T]) -> _T:
    if isinstance(value, to):
        return value
    raise TypeError(f'expected {name} to be a {to.__name__}')

def jsonget(json: dict[str, Any], key: str, to: type[_T], default: _T | EllipsisType = ...) -> _T:
    if default is not ... and key not in json:
        return default
    return cast(key, json[key], to)

def parse_interval(interval: str) -> float:
    h, m, s, ms = None, None, None, None
    if 'h' in interval:
        h, interval = interval.split('h')
    if 'm' in interval:
        m, interval = interval.split('m')
    if 's' in interval:
        s, ms = interval.split('s')
    h = int(h) if h else 0
    m = int(m) if m else 0
    s = int(s) if s else 0
    ms = int(ms) if ms else 0
    return (h * 60 + m) * 60 + s + (ms / 1000)

def format_time(time: datetime) -> str:
    return time.isoformat().replace('+00:00', 'Z')

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def get_ip_addr(ipv6: bool = False) -> str | None:
    """
    Get the local ip address

    Parameters:
        ip6: Whether to request IPv6 address

    Returns:
        IP address or None if an error occured
    """
    try:
        family = AF_INET6 if ipv6 else AF_INET
        target = '2606:4700:4700::1001' if ipv6 else '1.1.1.1'
        # Create a socket in UDP mode so no packets will be sent
        with socket(family, SOCK_DGRAM) as sock:
            sock.connect((target, 80))
            return sock.getsockname()[0]
    except:
        return None
