from datetime import datetime, timedelta

class Submittal:
    def __init__(self, num :int, name, comments, spec_refs=None, references=None, status='Active'):
        self.number = num
        self.name = name

        self.spec_ref = []
        if spec_refs is not None:
            for spec in spec_refs:
                self.spec_ref.append(spec)

        self.references = []
        if references is not None:
            for ref in references:
                self.references.append(ref)

        self.status = status # Active, Completed
        self.date_received = datetime.now()
        self.deadline = self.date_received + timedelta(days=14)
        self.comments = comments
