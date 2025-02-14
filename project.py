from submittal import Submittal
from reference import Reference

class Project:
    def __init__(self, name, desc, status='Active'):
        self.name = name
        self.desc = desc
        self.status = status # Active, Completed, On Hold
        self.references = []
        self.submittals = []
        #self.created_at = datetime.now()
        #self.updated_at = datetime.now()
        self.contacts = []
        print(self)

    def add_reference(self, file, ref_type, comments):
        ref = Reference(file.name, ref_type, file, comments)
        self.references.append(ref)
        print(self.references)

    def remove_project_resource(self, file_name):
        for file in self.references:
            if file.name == file_name:
                self.references.remove(file)
                return True
    
    def add_submittal(self, file, num, comments, s_refs):
        sub = Submittal(num, file.name, file, comments, s_refs)
        self.submittals.append(sub)

    def remove_submittal(self, sub_name):
        for sub in self.submittals:
            if sub.name == sub_name:
                self.submittals.remove(sub)
                return True

    def add_team_member(self, contact):
        self.contacts.append(contact)

    def __repr__ (self):
        return f"Project({self.name}, {len(self.references)} references, {len(self.submittals)} submittals)"

