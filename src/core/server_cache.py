from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UserHeatData:
    heat_value: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    violations: list[str] = field(default_factory=list)
    spam_count: int = 0
    phishing_attempt_count: int = 0
    honeypot_trigger_count: int = 0


@dataclass
class UserSchema:
    """
    discord user schema
    """

    id: str
    heat_data: UserHeatData = field(default_factory=UserHeatData)


@dataclass
class ServerSchema:
    """
    discord server schema
    """

    id: str
    users: list[UserSchema]


class ServerCache:
    def __init__(self):
        self.servers: list[ServerSchema] = []

    def get_server(self, server_id: str) -> ServerSchema | None:
        for server in self.servers:
            if server.id == server_id:
                return server
        return None

    def get_user(self, server_id: str, user_id: str) -> UserSchema | None:
        server = self.get_server(server_id)
        if server:
            for user in server.users:
                if user.id == user_id:
                    return user
        return None

    def add_server(self, server_id: str) -> ServerSchema:
        server = ServerSchema(id=server_id, users=[])
        self.servers.append(server)
        return server

    def add_user(self, server_id: str, user_id: str) -> UserSchema:
        server = self.get_server(server_id)
        if not server:
            server = self.add_server(server_id)
        user = UserSchema(id=user_id)
        server.users.append(user)
        return user

    def get_or_create_user(self, server_id: str, user_id: str) -> UserSchema:
        user = self.get_user(server_id, user_id)
        if not user:
            user = self.add_user(server_id, user_id)
        return user

    def get_user_heat_data(self, server_id: str, user_id: str) -> UserHeatData:
        user = self.get_or_create_user(server_id, user_id)
        return user.heat_data

    def reset_server(self, server_id: str):
        server = self.get_server(server_id)
        if server:
            server.users = []

    def reset_user(self, server_id: str, user_id: str):
        server = self.get_server(server_id)
        if server:
            server.users = [user for user in server.users if user.id != user_id]

    def reset_all(self):
        self.servers = []
