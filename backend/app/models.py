"""Project and related data models."""
from pydantic import BaseModel
from typing import Optional


class ProjectBase(BaseModel):
    name: str


class ProjectCreate(ProjectBase):
    pass


class ReferenceDoc(BaseModel):
    id: Optional[str] = None
    name: str
    csi_division: Optional[str] = None
    extracted_text: str = ""


class Submittal(BaseModel):
    id: Optional[str] = None
    name: str
    csi_division: Optional[str] = None
    extracted_text: str = ""
    evaluation_report: Optional[dict] = None
    evaluated_at: Optional[str] = None


class RFI(BaseModel):
    id: Optional[str] = None
    title: str
    description: str = ""
    status: str = "Open"
    date: str = ""


class Project(ProjectBase):
    id: Optional[str] = None
    open_submittals: list[Submittal] = []
    closed_submittals: list[Submittal] = []
    reference_docs: list[ReferenceDoc] = []
    rfis: list[RFI] = []

    class Config:
        from_attributes = True
