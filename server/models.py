from typing import List, Optional

from pydantic import BaseModel, EmailStr


class PersonCreate(BaseModel):
    name: str
    email: EmailStr
    university: str  # Can be canonical or alias
    country: str  # Country name as text (must match entry in countries table)
    subfield: str  # 'Department', 'TTO Office', 'Incubator'
    subfield_name: str  # Actual name of the department/incubator
    role: str  # 'Department Head', 'TTO Officer', etc.
    notes: Optional[str] = None


class PersonOut(PersonCreate):
    id: int
    university_id: int
    country_id: int


class University(BaseModel):
    id: int
    name: str
    ror_id: str


class Country(BaseModel):
    id: int
    name: str
    code: str  # ISO 3166-1 alpha-2


class UniversityAlias(BaseModel):
    id: int
    alias: str
    university_id: int


class EmailThreadLog(BaseModel):
    timestamp: str  # ISO format
    subject: Optional[str]
    body: str
    thread_id: Optional[str]
    participants: List[str]


class EmailLogOut(BaseModel):
    id: int
    timestamp: str
    subject: Optional[str]
    body: str
    thread_id: Optional[str]
