from dataclasses import dataclass
from typing import Generic, TypeVar
from typing import Iterable

T = TypeVar('T')

@dataclass
class Source(Generic[T]):
    iterable: Iterable[T]
    position: int=0

    def __iter__(self):
        len_iterable = len(self.iterable)

        while self.position < len_iterable:
            yield self.capture()
        
        return
    
    def capture(self, by=1) -> T | Iterable[T]:
        if by < 1:
            raise ValueError(f"argument 'by' must be greater than zero")

        elif self.position > len(self.iterable):
            self.position += 1
            return
        
        captured = self.iterable[self.position: self.position + by]
        self.position += by

        if by == 1:
            return captured[0] if captured else None
        
        return captured
    
    def release(self, by=1):
        self.position -= by

        if self.position < 0:
            self.position = 0
        
        return