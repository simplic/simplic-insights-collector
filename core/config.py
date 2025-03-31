"""
Simple configuration parser. Supports json data structures (null, bool, number, string, list, object)
"""

from __future__ import annotations

import json
from typing import IO, Any, Callable, Iterator, Mapping, Sequence, TypeVar, overload

_D = TypeVar('_D')
_T = TypeVar('_T')
_R = TypeVar('_R')

_default = object()

ConfigData = None | bool | int | float | str | list['ConfigData'] | dict[str, 'ConfigData']

class ConfigValue:
    """
    Base value, can be casted using as_* methods
    """

    def __init__(self, data: ConfigData, path: str) -> None:
        self._data = data
        self._path = path

    def _as_type(self, fn: Callable[[_T], _R], default: _D = _default, *tys: type[_T]) -> _R | _D:
        if default is not _default and self._data is None:
            return default
        if not isinstance(self._data, tys):
            names = [ty.__name__ for ty in tys]
            raise TypeError(f'Expected {self._path} to be one of {names}, but got {type(self._data).__name__}')
        return fn(self._data)
    
    def is_none(self) -> bool: return self._data is None
    def is_bool(self) -> bool: return isinstance(self._data, bool)
    def is_int(self) -> bool: return isinstance(self._data, int)
    def is_float(self) -> bool: return isinstance(self._data, (int, float))
    def is_str(self) -> bool: return isinstance(self._data, str)
    def is_list(self) -> bool: return isinstance(self._data, list)
    def is_dict(self) -> bool: return isinstance(self._data, dict)

    @overload
    def as_type(self, *tys: type[_T]) -> _T: ...
    @overload
    def as_type(self, *tys: type[_T], default: _D) -> _T | _D: ...
    def as_type(self, *tys: type[_T], default: _D = _default) -> _T | _D:
        if default is not _default and self._data is None:
            return default
        if not isinstance(self._data, tys):
            names = [ty.__name__ for ty in tys]
            raise TypeError(f'Expected {self._path} to be one of {names}')
        return self._data

    @overload
    def as_bool(self) -> bool: ...
    @overload
    def as_bool(self, default: _D) -> bool | _D: ...
    def as_bool(self, default: _D = _default) -> bool | _D: return self.as_type(bool, default=default)

    @overload
    def as_int(self) -> int: ...
    @overload
    def as_int(self, default: _D) -> int | _D: ...
    def as_int(self, default: _D = _default) -> int | _D: return self.as_type(int, default=default)

    @overload
    def as_float(self) -> float: ...
    @overload
    def as_float(self, default: _D) -> float | _D: ...
    def as_float(self, default: _D = _default) -> float | _D: return self._as_type(float, default, int, float)

    @overload
    def as_str(self) -> str: ...
    @overload
    def as_str(self, default: _D) -> str | _D: ...
    def as_str(self, default: _D = _default) -> str | _D: return self.as_type(str, default=default)

    @overload
    def as_list(self) -> ConfigList: ...
    @overload
    def as_list(self, default: _D) -> ConfigList | _D: ...
    def as_list(self, default: _D = _default) -> ConfigList | _D:
        return self._as_type(lambda v: ConfigList(v, self._path), default, Sequence) # type: ignore
    
    @overload
    def as_dict(self) -> ConfigDict: ...
    @overload
    def as_dict(self, default: _D) -> ConfigDict | _D: ...
    def as_dict(self, default: _D = _default) -> ConfigDict | _D:
        return self._as_type(lambda v: ConfigDict(v, self._path), default, dict) # type: ignore

class ConfigList(Sequence[ConfigValue]):
    """
    List accessor
    """

    def __init__(self, value: list[ConfigData], path: str) -> None:
        self.value = value
        self.path = path

    @overload
    def __getitem__(self, index: int) -> ConfigValue: ...
    @overload
    def __getitem__(self, index: slice[int | None, int | None, int | None]) -> Sequence[ConfigValue]: ...
    def __getitem__(self, index: int | slice[int | None, int | None, int | None]) -> ConfigValue | Sequence[ConfigValue]:
        count = len(self.value)
        
        if isinstance(index, int):
            item = self.value[index] if index in range(-count, count) else None
            return ConfigValue(item, f'{self.path}[{index}]')
        
        start = index.start if index.start is not None else 0
        stop = index.stop if index.stop is not None else -1
        step = index.step if index.step is not None else 1

        if start < 0:
            start += count
        if stop < 0:
            stop += count

        items = []
        for i in range(start, stop, step):
            item = self.value[i] if i in range(-count, count) else None
            items.append(ConfigValue(item, f'{self.path}[{index}]'))

        return items

    def __iter__(self) -> Iterator[ConfigValue]:
        for i, item in enumerate(self.value):
            yield ConfigValue(item, f'{self.path}[{i}]')

    def __len__(self) -> int:
        return len(self.value)
    
    def __contains__(self, value: object) -> bool:
        if isinstance(value, ConfigValue):
            return value._data in self.value
        return value in self.value
    
    def __reversed__(self) -> Iterator[ConfigValue]:
        for i, item in enumerate(reversed(self.value)):
            yield ConfigValue(item, f'{self.path}[{i}]')

    def iter_bool(self) -> Iterator[bool]: return map(ConfigValue.as_bool, self)
    def iter_int(self) -> Iterator[int]: return map(ConfigValue.as_int, self)
    def iter_float(self) -> Iterator[float]: return map(ConfigValue.as_float, self)
    def iter_str(self) -> Iterator[str]: return map(ConfigValue.as_str, self)
    def iter_list(self) -> Iterator[ConfigList]: return map(ConfigValue.as_list, self)
    def iter_dict(self) -> Iterator[ConfigDict]: return map(ConfigValue.as_dict, self)

class ConfigDict(Mapping[str, ConfigValue]):
    """
    Dictionary accessor
    """

    def __init__(self, value: dict[str, ConfigData], path: str) -> None:
        self.value = value
        self.path = path

    def __getitem__(self, key: str) -> ConfigValue:
        return ConfigValue(self.value.get(key, None), f'{self.path}.{key}')
    
    def __iter__(self) -> Iterator[str]:
        return iter(self.value)
    
    def __len__(self) -> int:
        return len(self.value)
    
    def __contains__(self, key: object) -> bool:
        return key in self.value

def parse_config(file: IO[str]) -> ConfigValue:
    return ConfigValue(json.load(file), '$')

def parse_config_file(path: str) -> ConfigValue:
    with open(path, 'rt') as f:
        return parse_config(f)
    
