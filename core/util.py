from typing import Any, TypeVar


_T = TypeVar('_T')
def cast(name: str, value: Any, to: type[_T]) -> _T:
    if isinstance(value, to):
        return value
    raise TypeError(f'expected {name} to be a {to.__name__}')

def jsonget(json: dict[str, Any], key: str, to: type[_T], default: _T | ellipsis = ...) -> _T:
    if not isinstance(default, ellipsis) and key not in json:
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
