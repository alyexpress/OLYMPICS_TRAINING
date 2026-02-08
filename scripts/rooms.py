from random import shuffle

from data import db_session
from data.tasks import Task


class Rooms:
    def __init__(self):
        self.find = {x: None for x in "SMH"}
        self.active = []

    def join(self, id, level):
        if level not in self.find.keys():
            return None
        if self.find[level] is None:
            self.find[level] = id
            return None
        other = self.find[level]
        self.find[level] = None
        db_sess = db_session.create_session()
        difficult = {"S": "simple", "M": "medium", "H": "hard"}[level]
        tasks = db_sess.query(Task).filter(Task.difficult == difficult).all()
        shuffle(tasks)
        self.active.append({"users": [id, other],
            "tasks": tasks[:3], "resolve": [0] * len(tasks[:3])})
        return other, len(self.active)

    def leave(self, id):
        if id in self.find.values():
            for key, val in self.find.items():
                if val == id: self.find[key] = None

    def check(self, number, id):
        if 0 < number <= len(self.active):
            return id in self.active[number - 1]["users"]
        return False


    def tasks(self, number):
        return self.active[number - 1]["tasks"]

    def resolve(self, number):
        return self.active[number - 1]["resolve"]

    def check_answer(self, number, answer, id):
        index = self.resolve(number).index(0)
        if self.tasks(number)[index].answer == answer:
            self.active[number - 1]["resolve"][index] = id
            return True
        return False

    def other(self, number, id):
        user = self.active[number - 1]["users"].copy()
        user.remove(id)
        return user[0]