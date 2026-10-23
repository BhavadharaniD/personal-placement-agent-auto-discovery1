from pydantic import BaseModel, Field
from typing import Optional, List

class ProfileIn(BaseModel):
    full_name: str = ""
    degree: str = ""
    graduation_year: Optional[int] = None
    skills: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)
    include_internships: bool = True
    resume_text: str = ""

class JobIn(BaseModel):
    title: str
    company: str = ""
    location: str = ""
    job_type: str = "Full-time"
    experience: str = "Fresher"
    graduation_years: List[int] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    description: str = ""
    source_url: str = ""
    source: str = "Manual"

class StatusIn(BaseModel):
    status: str
    notes: str = ""
