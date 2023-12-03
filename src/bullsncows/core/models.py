from abc import ABC, abstractmethod


class Server(ABC):
    """
    Abstract class for Bulls n Cows server.
    """

    @abstractmethod
    def open(self):
        """
        Opens the server for client to join.
        :return: None
        """
        pass

    @abstractmethod
    def close(self):
        """
        Closes the server.
        :return: None
        """
        pass

    @abstractmethod
    def start(self):
        """
        Starts a game.
        :return: None
        """
        pass

    @abstractmethod
    def end(self):
        """
        Ends a game.
        :return: None
        """
        pass

    @abstractmethod
    def proceed(self):
        """
        Make the game proceed to the next round.
        :return:
        """
        pass

    @abstractmethod
    def player_join(self, player):
        """
        Player joins the server.
        :param player: Client
        :return: None
        """
        pass

    @abstractmethod
    def player_leave(self, player):
        """
        Player leaves the server.
        :param player: Client
        :return: None
        """
        pass

    @abstractmethod
    def guess(self, player, choices):
        """
        Player gives a guess to the server
        :param player: Client
        :param choice: 4-sized tuple
        :return: None
        """

    @abstractmethod
    def answer_guess(self, player):
        """
        Replies to the guess.
        :param player: Client
        :return: None
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @name.setter
    @abstractmethod
    def name(self, value: str):
        pass

    @property
    @abstractmethod
    def is_private(self) -> bool:
        pass

    @is_private.setter
    @abstractmethod
    def is_private(self, value: bool):
        pass

    @property
    @abstractmethod
    def password(self) -> str:
        pass

    @password.setter
    @abstractmethod
    def password(self, value: str):
        pass

    @property
    @abstractmethod
    def max_rounds(self) -> int:
        pass

    @max_rounds.setter
    @abstractmethod
    def max_rounds(self, value: int):
        pass

    @property
    @abstractmethod
    def range(self) -> int:
        pass

    @range.setter
    @abstractmethod
    def range(self, value):
        pass

    @property
    @abstractmethod
    def time_per_round(self) -> float:
        pass

    @time_per_round.setter
    @abstractmethod
    def time_per_round(self, value: float):
        pass

    @property
    @abstractmethod
    def round(self) -> int:
        pass


class Client(ABC):
    """
    Abstract class for Bulls n Cows client
    """

    @abstractmethod
    def connect(self, server):
        """
        Connects to the server.
        :param server: Server
        :return: None
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Disconnects from the server.
        :return: None
        """
        pass

    @abstractmethod
    def guess(self, choices):
        """
        Gives a guess to the server.
        :param choices: 4-sized tuple
        :return: None
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @name.setter
    @abstractmethod
    def name(self, value: str):
        pass
