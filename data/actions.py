import sqlalchemy
from .db_session import SqlAlchemyBase


class Action(SqlAlchemyBase):
    __tablename__ = 'actions'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    task_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('tasks.id'))
    status = sqlalchemy.Column(sqlalchemy.Integer)