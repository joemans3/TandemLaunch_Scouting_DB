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
