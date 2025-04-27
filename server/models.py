from typing import Optional

from pydantic import BaseModel, EmailStr


class UniversityCreate(BaseModel):
    name: str


class DepartmentCreate(BaseModel):
    name: str
    university_id: int


class DepartmentHeadCreate(BaseModel):
    name: str
    email: EmailStr
    department_id: int
    university_id: int


class AdminCreate(BaseModel):
    name: str
    email: EmailStr
    department_id: int
    university_id: int


class CatalogEntryCreate(BaseModel):
    university_name: str
    department_name: str
    department_head_name: Optional[str] = None
    department_head_email: Optional[str] = None
    admin_name: Optional[str] = None
    admin_email: Optional[str] = None


class CatalogEntry(CatalogEntryCreate):
    id: int
