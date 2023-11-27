from struct import pack, unpack
from dataclasses import dataclass, fields

from typing import ClassVar


@dataclass(order=True)
class Packet:
    pformat: ClassVar[str] = ''

    def __init_subclass__(cls, pformat: str = None, **kwargs):
        if cls == Packet:
            super().__init_subclass__()
        else:
            super().__init_subclass__(**kwargs)
        if pformat is not None:
            cls.pformat = pformat

    @classmethod
    def from_bytes(cls, b: bytes):
        unpacked = unpack(cls.pformat, b)
        return cls(*unpacked)

    def to_bytes(self) -> bytes:
        return pack(self.__class__.pformat, *[self.__getattribute__(f.name) for f in fields(self)])


if __name__ == "__main__":
    @dataclass
    class ExamplePacket(Packet, pformat="<ii"):
        a: int
        b: int

    # extended new attributes are appended at the back
    @dataclass
    class ExampleExtendedPacket(ExamplePacket, pformat=ExamplePacket.pformat + 'd'):
        c: float


    print(ExamplePacket(1, 2).to_bytes())
    print(ExamplePacket.from_bytes(pack('<ii', 255, 254)))
    print(ExampleExtendedPacket(1, 2, 3.1).to_bytes())
    print(ExampleExtendedPacket.from_bytes(pack('<iid', 255, 254, 1.1)))
