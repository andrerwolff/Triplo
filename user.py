from project import Project

class User:
    def __init__(self, name):
        self.name = name
        self.project_list = []

    def add_project(self, project: Project):
        self.project_list.append(project)
        print(f"{project.name} added!")

    def remove_project(self, project_name):
        for p in self.project_list:
            if p.name == project_name:
                self.project_list.remove(p)
                return True
