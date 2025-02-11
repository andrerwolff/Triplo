from submittal import Submittal

class Project:
    def __init__(self, name, desc, status='Active'):
        self.name = name
        self.desc = desc
        self.status = status # Active, Completed, On Hold
        self.project_resources = []
        self.submittals = []
        #self.created_at = datetime.now()
        #self.updated_at = datetime.now()
        self.contacts = []
        print(self)

    def add_project_resource(self, file):
        self.project_resources.append(file)
        print(self)
    
    def add_submittal(self, submittal):
        self.submittals.append(submittal)
        print(self, "submittal add")

    def add_team_member(self, contact):
        self.contacts.append(contact)

    def __repr__ (self):
        return f"Project({self.name}, {len(self.project_resources)} resources, {len(self.submittals)} submittals)"

