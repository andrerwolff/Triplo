class Submittal:
    def __init__(self, name, desc, status='Active'):
        self.name = name
        self.desc = desc
        self.status = status # Active, Completed
        print(self)