class Reference:
    def __init__(self, name, type, file, comments):
        self.name = name
        self.type = type
        self.comments = comments
        self.file = file

    def __repr__ (self):
        return f"Reference({self.type}, {self.file})"