import sqlalchemy
from .db_session import SqlAlchemyBase


class Task(SqlAlchemyBase):
    __tablename__ = 'tasks'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, unique=True)
    condition = sqlalchemy.Column(sqlalchemy.Text)
    image = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    subject = sqlalchemy.Column(sqlalchemy.String)
    theme = sqlalchemy.Column(sqlalchemy.String)
    difficult = sqlalchemy.Column(sqlalchemy.String)