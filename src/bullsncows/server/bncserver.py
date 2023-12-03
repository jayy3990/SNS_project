import random
import socketserver
import threading
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from typing import Optional, Tuple

from src.bullsncows.core.helpers import require_state, Stateful
from src.bullsncows.core.models import Server, Client
from src.bullsncows.core.packets import AuthRequestPacket, AuthResponsePacket, Packet, ChoicePacket, ChoiceResultPacket, \
    BeginGamePacket, EndGamePacket, BeginRoundPacket


class BNCServer(Server, Stateful['BNCServer.State']):
    class RoundTimer(threading.Timer):
        def __init__(self, interval, bnc_server: 'BNCServer'):
            super().__init__(interval, BNCServer.proceed, [bnc_server])

    class TCPRequestHandler(socketserver.BaseRequestHandler):
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

    class TCPServer(socketserver.TCPServer, socketserver.ThreadingMixIn):
        allow_reuse_address = True

        def __init__(self, server_address, RequestHandlerClass, bnc_server: 'BNCServer', bind_and_activate):
            super().__init__(server_address, RequestHandlerClass, bind_and_activate=bind_and_activate)
            self.__queues: dict[tuple[str, int] | str, Queue] = {}
            self.__addresses: dict[Client, tuple[str, int] | str] = {}
            self.__bnc_server = bnc_server

        def finish_request(self, request, client_address):
            if client_address not in self.__queues:
                self.__queues[client_address] = Queue()
            player = FakeClient()
            self.__addresses[player] = client_address
            self.RequestHandlerClass(request, client_address, self,
                                     bnc_server=self.__bnc_server, player=player,
                                     queue=self.__queues[client_address])

        def handle_error(self, request, client_address):
            self.__bnc_server.player_leave(self.get_client(client_address))

        def queue(self, player, packet):
            if (client_address := self.get_client_address(player)) not in self.__queues:
                self.__queues[client_address] = Queue()
            self.__queues[client_address].put(packet)

        def get_client_address(self, player: Client):
            return self.__addresses[player]

        def get_client(self, client_address):
            return next((k for k, v in self.__addresses.items() if k == client_address), None)

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

    SERVER_IP = "localhost"
    SERVER_PORT = 8080

    def __init__(self, name: str = "", config: Config = None, ip=None, port=None):
        super().__init__()
        self.__name: str = name
        self.__state: "BNCServer.State" = BNCServer.State.SETUP
        self.__config: "BNCServer.Config" = config if config else BNCServer.Config()
        self.__server_ip = ip if ip is not None else BNCServer.SERVER_IP
        self.__server_port = port if ip is not None else BNCServer.SERVER_PORT
        self.__round: int = 0

        self.__tcp_server = BNCServer.TCPServer((self.__server_ip, self.__server_port),
                                                BNCServer.TCPRequestHandler, self,
                                                bind_and_activate=False)
        self.__tcp_server_thread = None
        self.__timer: Optional[BNCServer.RoundTimer] = None
        self.__players: Optional[list[Client]] = None
        self.__answers: Optional[Tuple[int]] = None
        self.__choices: Optional[dict[Client, Tuple[int]]] = None

    @require_state({State.SETUP})
    def open(self):
        self.__tcp_server.__enter__()
        self.__tcp_server_thread = threading.Thread(target=self.__tcp_server.serve_forever)
        self.__tcp_server_thread.daemon = True
        self.__tcp_server_thread.start()
        print(self.__tcp_server_thread)
        self.__players = []
        self.__timer = BNCServer.RoundTimer(self.time_per_round, self)
        self.__state = BNCServer.State.IDLE

    @require_state({State.IDLE})
    def close(self):
        self.__tcp_server.shutdown()
        self.__state = BNCServer.State.SETUP

    @require_state({State.IDLE})
    def start(self):
        self.__answers = [random.randint(1, self.range + 1) for _ in range(4)]
        packet = BeginGamePacket(self.range, self.max_rounds, self.time_per_round, len(self.__players))
        for p in self.__players:
            self.__tcp_server.queue(p, packet)

        self.__timer.start()

    @require_state({State.GAME})
    def end(self):
        self.__timer.cancel()
        winner = next((
            p for p, c in self.__choices.items() if BNCServer.score(c, self.__answers)[0] == len(self.__answers)), None)
        packet = EndGamePacket(self.round, winner.name if winner else "", *self.__choices[winner])
        for p in self.__players:
            self.__tcp_server.queue(p, packet)

    @require_state({State.GAME})
    def proceed(self):
        self.advance_round()
        game_over = (any((True
                          for p, c in self.__choices.items()
                          if BNCServer.score(c, self.__answers)[0] == len(self.__answers))) or
                     (self.max_rounds != 0 and self.__round > self.max_rounds))
        if game_over:
            self.end()
        else:
            packet = BeginRoundPacket(self.round)
            for p in self.__players:
                self.answer_guess(p)
                self.__tcp_server.queue(p, packet)

    @require_state({State.IDLE})
    def player_join(self, player: Client):
        self.__players.append(player)

    @require_state({State.IDLE, State.GAME})
    def player_leave(self, player: Client):
        self.__players.remove(player)

    @require_state({State.GAME})
    def guess(self, player, choices):
        self.__choices[player] = choices

    @require_state({State.GAME})
    def answer_guess(self, player: Client):
        bulls, cows = BNCServer.score(self.__choices[player], self.__answers)
        packet = ChoiceResultPacket(player.name, *self.__choices[player], bulls, cows)
        self.__tcp_server.queue(player, packet)

    @staticmethod
    def score(choices, answers):
        bulls = sum(1 for c, a in zip(choices, answers) if c == a)
        cows = sum(1 for c in choices if c in answers)
        return bulls, cows

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

    def advance_round(self):
        self.__round += 1

    def reset_round(self):
        self.__round = 0


class FakeClient(Client):
    server: BNCServer
    __name: str = ''

    def __init__(self, name: str = None):
        super().__init__()
        if name is not None:
            self.__name = name

    def connect(self, server):
        pass

    def disconnect(self):
        pass

    def guess(self, choices):
        self.server.answer_guess(choices)

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value: str):
        self.__name = value


if __name__ == "__main__":
    config = BNCServer.Config(max_rounds=2, time_per_round=100.0)
    bnc_server = BNCServer("myserver", config=BNCServer.Config(is_private=False))

    bnc_server.open()


    def client(ip, port):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip, port))
            sock.settimeout(None)
            received = AuthRequestPacket.from_bytes(sock.recv(1024))
            print("=>", received)
            if received.is_private:
                sock.send(AuthResponsePacket("name", "1234").to_bytes())
            bnc_server.start()

            received = BeginGamePacket.from_bytes(sock.recv(1024))
            print("=>", received)
            for _ in range(2):
                received = BeginRoundPacket.from_bytes(sock.recv(1024))
                print("=>", received)
                sock.send(ChoicePacket(1, 1, 2, 3, 4))
                print("=>", received)
                received = ChoiceResultPacket.from_bytes(sock.recv(1024))
                print("=>", received)

        sock.close()


    client(BNCServer.SERVER_IP, BNCServer.SERVER_PORT)
