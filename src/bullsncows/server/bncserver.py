import socketserver
from dataclasses import dataclass
from enum import Enum
from queue import Queue

from src.bullsncows.core.helpers import require_state, Stateful
from src.bullsncows.core.models import Server, Client


class BNCServer(Server, Stateful['BNCServer.State']):
    class BNCTCPRequestHandler(socketserver.BaseRequestHandler):
        def __init__(self, request, client_address, server, bnc_server=None, player=None, queue=None):
            self.__bnc_server = bnc_server
            self.__player = player
            self.__queue = queue
            super().__init__(request, client_address, server)

        def handle(self):
            self.request.send(AuthRequestPacket(self.__bnc_server.name, self.__bnc_server.is_private).to_bytes())
            response = AuthResponsePacket.from_bytes(self.request.recv(1024))

            if self.__bnc_server.is_private and response.password != response.password:
                self.request.close()

            self.__player.name = response.nickname
            self.__bnc_server.player_join(self.__player)

            while True:
                send_packet = self.__queue.get()
                print(send_packet)
                self.request.send(send_packet.to_bytes())
                recv_packet = Packet.from_bytes(self.request.recv(1024))
                if isinstance(recv_packet, ChoicePacket):
                    self.__player.guess(
                        [recv_packet.choice_1, recv_packet.choice_2, recv_packet.choice_3, recv_packet.choice_4])

    class BNCTCPServer(socketserver.TCPServer, socketserver.ThreadingMixIn):
        allow_reuse_address = True

        def __init__(self, server_address, RequestHandlerClass, bnc_server: 'BNCServer'):
            super().__init__(server_address, RequestHandlerClass)
            self.__queues: dict[tuple[str, int] | str, Queue] = {}
            self.__players: dict[tuple[str, int] | str, VirtualClient] = {}
            self.__bnc_server = bnc_server

        def finish_request(self, request, client_address):
            if client_address not in self.__queues:
                self.__queues[client_address] = Queue()
            self.__players[client_address] = VirtualClient()
            self.RequestHandlerClass(request, client_address, self,
                                     bnc_server=self.__bnc_server, player=self.__players[client_address],
                                     queue=self.__queues[client_address])

        def handle_error(self, request, client_address):
            self.__bnc_server.player_leave(self.__players[client_address])

        def queue(self, client_address, packet):
            if client_address not in self.__queues:
                self.__queues[client_address] = Queue()
            self.__queues[client_address].put(packet)

    class State(Enum):
        SETUP = 0,
        IDLE = 1,
        GAME = 2

    @dataclass
    class Config:
        is_private: bool = False
        password: str = ''
        max_player: int = 4
        max_rounds: int = 0
        range: int = 9
        time_per_round: float = 0.0

    def __init__(self, name: str = "", config: Config = None):
        super().__init__()
        self.__name: str = ""
        self.__state: "BNCServer.State" = BNCServer.State.SETUP
        self.__config: "BNCServer.Config" = config if config else BNCServer.Config()
        self.__round: int = 0

    @require_state({State.SETUP})
    def open(self):
        self.__state = BNCServer.State.IDLE

    @require_state({State.GAME, State.IDLE})
    def close(self):
        pass

    @require_state({State.IDLE})
    def start(self):
        pass

    @require_state({State.GAME})
    def end(self):
        pass

    @require_state({State.GAME})
    def proceed(self):
        pass

    @require_state({State.IDLE})
    def player_join(self, player):
        pass

    @require_state({State.IDLE, State.GAME})
    def player_leave(self, player):
        pass

    @require_state({State.GAME})
    def answer_guess(self, player, choices):
        pass

    @property
    def state(self):
        return self.__state

    @property
    def config(self):
        return self.__config

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, name: str):
        self.__name = name

    @property
    def is_private(self) -> bool:
        return self.config.is_private

    @is_private.setter
    def is_private(self, value: bool):
        self.config.is_private = value

    @property
    def password(self) -> str:
        return self.config.password

    @password.setter
    def password(self, value: str):
        self.config.password = value

    @property
    def max_rounds(self) -> int:
        return self.config.max_rounds

    @max_rounds.setter
    def max_rounds(self, value: int):
        self.config.max_rounds = value

    @property
    def range(self) -> int:
        return self.config.range

    @range.setter
    def range(self, value: int):
        self.config.range = value

    @property
    def time_per_round(self) -> float:
        return self.config.time_per_round

    @time_per_round.setter
    def time_per_round(self, value: float):
        self.config.time_per_round = value

    @property
    def round(self) -> int:
        return self.__round


class VirtualClient(Client):
    server: BNCServer
    __name: str = ''

    def __init__(self, name: str = None):
        super().__init__()
        if name is not None:
            self.__name = name

    def connect(self, server):
        server.player_join(self)
        self.server = server

    def disconnect(self):
        server.player_leave(self)
        del self.server

    def guess(self, choices):
        self.server.answer_guess(choices)

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value: str):
        self.__name = value


if __name__ == "__main__":
    server = BNCServer()
    client = VirtualClient("client")

    server.open()
    client.connect(server)
    # some proc
    server.player_join(client)

    server.start()
    for _ in range(server.max_rounds):
        server.proceed()

    server.end()

    server.close()
