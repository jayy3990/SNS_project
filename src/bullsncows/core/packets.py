from struct import pack, unpack_from, calcsize
from dataclasses import dataclass, fields

from typing import ClassVar


@dataclass(order=True)
class Packet:
    PID_LENGTH: ClassVar[int] = 2

    pformat: ClassVar[str] = ''
    pid: ClassVar[int] = -1

    registry: ClassVar[dict[int, list[type['Packet']]]] = {}

    def __init_subclass__(cls, pformat: str = None, pid: int = -1, **kwargs):
        if cls == Packet:
            super().__init_subclass__()
        else:
            super().__init_subclass__(**kwargs)
        if pformat is not None:
            cls.pformat = pformat
        if pid != -1:
            cls.pid = pid
        Packet.register(pid, cls)

    def __repr__(self):
        return f"<{super().__repr__()};{self.to_bytes()}>"

    @staticmethod
    def register(pid: int, cls: type['Packet']):
        if pid not in Packet.registry:
            Packet.registry[pid] = []
        prev = Packet.registry[pid]
        index = next((calcsize(cls.pformat) > calcsize(p.pformat) for i, p in enumerate(prev)), len(prev))
        Packet.registry[pid] = [*prev[:index], cls, *prev[index:]]

    @staticmethod
    def encode(b: bytes):
        pid, _ = Packet.parse(b)
        p = next((p for p in Packet.registry[pid] if len(b) > calcsize(p.pformat)), None)
        if not p:
            raise ValueError(f"Packet not found for ID {pid}")
        return p.from_bytes(b)

    @staticmethod
    def parse(b: bytes):
        return int.from_bytes(b[:Packet.PID_LENGTH], 'little', signed=False), b[Packet.PID_LENGTH:]

    @staticmethod
    def compose(pid: int, b: bytes):
        return pid.to_bytes(Packet.PID_LENGTH, 'little', signed=False) + b

    @classmethod
    def from_bytes(cls, b: bytes):
        pid, body = Packet.parse(b)
        if pid != cls.pid:
            raise ValueError(f"Packet ID does not match with class {cls}")
        return cls(*unpack_from(cls.pformat, body))

    def to_bytes(self) -> bytes:

        body = pack(self.__class__.pformat, *[self.__getattribute__(f.name).encode('utf-8')
                                              if f.type == str else self.__getattribute__(f.name) for
                                              f in fields(self)])
        return Packet.compose(self.__class__.pid, body)


# server-side packets
@dataclass
class AuthRequestPacket(Packet, pid=0, pformat='<16p?'):
    server_name: str
    is_private: bool


@dataclass
class BeginGamePacket(Packet, pid=1, pformat='<IIfI'):
    range: int
    rounds: int
    time_per_round: float
    participants: int


@dataclass
class EndGamePacket(Packet, pid=3, pformat='<I16p4I'):
    total_round: int
    winner: str
    answer_1: int
    answer_2: int
    answer_3: int
    answer_4: int


@dataclass
class BeginRoundPacket(Packet, pid=2, pformat="<I"):
    round: int


@dataclass
class EndRoundPacket(Packet, pid=3, pformat='<I'):
    round: int


@dataclass
class ChoiceResultPacket(Packet, pid=4, pformat='<16p4IHH'):
    user: str
    choice_1: int
    choice_2: int
    choice_3: int
    choice_4: int
    cows: int
    bools: int


@dataclass
class AuthResponsePacket(Packet, pid=128, pformat='<16p16p'):
    nickname: str
    password: str


@dataclass
class ChoicePacket(Packet, pid=129, pformat='<I4I'):
    round: int
    choice_1: int
    choice_2: int
    choice_3: int
    choice_4: int


if __name__ == "__main__":
    @dataclass
    class ExamplePacket(Packet, pid=256, pformat="<ii"):
        a: int
        b: int


    # extended new attributes are appended at the back
    @dataclass
    class ExampleExtendedPacket(ExamplePacket, pformat=ExamplePacket.pformat + 'd'):
        c: float


    # # default example
    # packets = [ExamplePacket(1, 0), ExamplePacket(1, 1), ExampleExtendedPacket(1, 2, 1.3), ExamplePacket(1, 3)]
    # packets_bytes = [p.to_bytes() for p in packets]
    # restored_specific = [ExamplePacket.from_bytes(b) for b in packets_bytes]
    # restored_auto = [Packet.encode(b) for b in packets_bytes]
    #
    # print(packets, restored_specific, restored_auto)

    # packets
    packets = []
    packets.append(AuthRequestPacket("server_name", False))
    packets.append(BeginGamePacket(16, 0, 20.0, 2))
    packets.append(EndGamePacket(35, "winner", 1, 2, 3, 4))
    packets.append(BeginRoundPacket(2))
    packets.append(EndRoundPacket(2))
    packets.append(ChoiceResultPacket("user", 1, 2, 3, 4, 0, 2))

    packets.append(AuthResponsePacket("nickname", "1q2w3e4r"))
    packets.append(ChoicePacket(12, 1, 2, 3, 4))

    print(*[(p, p.to_bytes())for p in packets], sep='\n')
