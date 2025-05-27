from sqlalchemy import create_engine, Table, Column, String, Boolean, Integer, MetaData
from sqlalchemy.exc import SQLAlchemyError

class DashboardDB:
    def __init__(self, mysql_connection, hash_function):
        mysql_connection = mysql_connection.replace("mysql://", "mysql+pymysql://")
        self.engine = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()
        self.hash = hash_function

        self.users = Table(
            'dashboarddb', self.metadata,
            Column('username', String(255), primary_key=True, nullable=False),
            Column('owned_server', String(255), nullable=True),
            Column('premium_user', Boolean, default=False),
            Column('total_modern_auth_players', Integer, default=0),
            Column('total_players', Integer, default=0)
        )
        self.metadata.create_all(self.engine)

    def get_user(self, username):
        if isinstance(username, dict):
            username = username.get('username')
        try:
            with self.engine.connect() as conn:
                stmt = self.users.select().where(self.users.c.username == username)
                result = conn.execute(stmt)
                row = result.mappings().first()
                return dict(row) if row else None
        except (SQLAlchemyError, TypeError) as e:
            print(f"[dashdb.get_user] error fetching '{username}': {e}")
            return None

    def set_user(self, username, data):
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.users.insert()
                    .values(
                        username=username,
                        owned_server=data.get('owned_server'),
                        premium_user=data.get('premium_user', False),
                        total_modern_auth_players=data.get('total_modern_auth_players', 0),
                        total_players=data.get('total_players', 0)
                    )
                    .prefix_with('IGNORE')
                )
                conn.execute(
                    self.users.update()
                    .where(self.users.c.username == username)
                    .values(
                        owned_server=data.get('owned_server'),
                        premium_user=data.get('premium_user', False),
                        total_modern_auth_players=data.get('total_modern_auth_players', 0),
                        total_players=data.get('total_players', 0)
                    )
                )
        except SQLAlchemyError as e:
            print(f"Failed to save user: {e}")

    def create_user_if_missing(self, username):
        if not self.get_user(username):
            self.set_user(username, {
                "owned_server": None,
                "premium_user": False,
                "total_modern_auth_players": 0,
                "total_players": 0
            })