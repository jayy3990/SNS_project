import socket
import threading
import socketserver
from queue import Queue

from src.bullsncows.core.packets import AuthRequestPacket, AuthResponsePacket, Packet, ChoicePacket, BeginGamePacket, \
    BeginRoundPacket, EndRoundPacket, ChoiceResultPacket
from src.bullsncows.server.bncserver import VirtualClient, BNCServer



if __name__ == "__main__":
    bnc_server = BNCServer()
    bnc_server.is_private = True
    bnc_server.name = "name"
    bnc_server.password = "1234"
    bnc_server.open()

    with BNCTCPServer(("127.0.0.1", 8080), BNCTCPRequestHandler, bnc_server) as server:
        def client(ip, port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((ip, port))
                sock.settimeout(None)
                received = AuthRequestPacket.from_bytes(sock.recv(1024))
                print("=>", received)
                if received.is_private:
                    sock.send(AuthResponsePacket("name", "1234").to_bytes())
                server.queue(sock.getsockname(), BeginGamePacket(9, 0, 10.0, 3))
                received = BeginGamePacket.from_bytes(sock.recv(1024))
                print("=>", received)
                server.
                received = BeginRoundPacket.from_bytes(sock.recv(1024))
                print("=>", received)
                sock.send(ChoicePacket(1, 1, 2, 3, 4))
                received = EndRoundPacket.from_bytes(sock.recv(1024))
                print("=>", received)
                received = ChoiceResultPacket.from_bytes(sock.recv(1024))
                print("=>", received)

            sock.close()


        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        client(*server.server_address)
