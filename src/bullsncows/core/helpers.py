from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from enum import Enum

S = TypeVar('S', bound=Enum)


class Stateful(ABC, Generic[S]):
    @property
    @abstractmethod
    def state(self) -> S:
        pass


def require_state(states: set[S]):
    states = {s.value for s in states}

    def decorator(func):
        def wrapper(self: Stateful[S], *args, **kwargs):
            if self.state.value not in states:
                raise RuntimeError(f"Cannot '{func.__name__}' since server is in {self.state}")
            func(self, *args, **kwargs)
        return wrapper
    return decorator


