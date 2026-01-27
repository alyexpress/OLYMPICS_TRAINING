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
        self.active.append([id, other])
        return other, len(self.active)

    def leave(self, id):
        if id in self.find.values():
            for key, val in self.find.items():
                if val == id: self.find[key] = None

    def check(self, number, id):
        if 0 < number <= len(self.active):
            return id in self.active[number - 1]
        return False
