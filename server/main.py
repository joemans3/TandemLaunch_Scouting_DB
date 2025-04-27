import sqlite3
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query

from .database import get_connection, initialize_database
from .models import (
    AdminCreate,
    CatalogEntry,
    CatalogEntryCreate,
    DepartmentCreate,
    DepartmentHeadCreate,
    UniversityCreate,
)

app = FastAPI()

initialize_database()


@app.get("/catalog/", response_model=List[CatalogEntry])
def list_catalog_entries(q: Optional[str] = None, offset: int = 0, limit: int = 100):
    conn = get_connection()
    cursor = conn.cursor()

    if q:
        cursor.execute(
            """
            SELECT * FROM catalog_entries
            WHERE university_name LIKE ? OR department_name LIKE ?
            OR department_head_name LIKE ? OR admin_name LIKE ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", limit, offset),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM catalog_entries
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.delete("/department_heads/{head_id}")
def delete_department_head(head_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM department_heads WHERE id = ?", (head_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Department head not found.")
    conn.close()
    return {"status": "success"}


@app.delete("/admins/{admin_id}")
def delete_admin(admin_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Admin not found.")
    conn.close()
    return {"status": "success"}


@app.post("/universities/")
def create_university(university: UniversityCreate):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO universities (name) VALUES (?)", (university.name,))
        conn.commit()
        university_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="University already exists.")
    finally:
        conn.close()

    return {"id": university_id, "name": university.name}


@app.get("/universities/")
def list_universities():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM universities")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# 🔵 New: Create Department
@app.post("/departments/")
def create_department(department: DepartmentCreate):
    conn = get_connection()
    cursor = conn.cursor()

    # check if university exists
    cursor.execute(
        "SELECT * FROM universities WHERE id = ?", (department.university_id,)
    )
    university = cursor.fetchone()
    if not university:
        raise HTTPException(status_code=404, detail="University not found.")

    cursor.execute(
        "INSERT INTO departments (name, university_id) VALUES (?, ?)",
        (department.name, department.university_id),
    )
    conn.commit()
    department_id = cursor.lastrowid
    conn.close()

    return {
        "id": department_id,
        "name": department.name,
        "university_id": department.university_id,
    }


# 🔵 New: List Departments
@app.get("/departments/")
def list_departments():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT departments.id, departments.name, universities.name AS university_name
        FROM departments
        JOIN universities ON departments.university_id = universities.id
    """)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.post("/department_heads/")
def create_department_head(head: DepartmentHeadCreate):
    conn = get_connection()
    cursor = conn.cursor()

    # check if university exists
    cursor.execute("SELECT * FROM universities WHERE id = ?", (head.university_id,))
    university = cursor.fetchone()
    if not university:
        raise HTTPException(status_code=404, detail="University not found.")

    # check if department exists
    cursor.execute(
        "SELECT * FROM departments WHERE id = ? AND university_id = ?",
        (head.department_id, head.university_id),
    )
    department = cursor.fetchone()
    if not department:
        raise HTTPException(
            status_code=404, detail="Department not found for given university."
        )

    cursor.execute(
        "INSERT INTO department_heads (name, email, department_id, university_id) VALUES (?, ?, ?, ?)",
        (head.name, head.email, head.department_id, head.university_id),
    )
    conn.commit()
    head_id = cursor.lastrowid
    conn.close()

    return {
        "id": head_id,
        "name": head.name,
        "email": head.email,
        "department_id": head.department_id,
        "university_id": head.university_id,
    }


# --- New: List Department Heads ---
@app.get("/department_heads/")
def list_department_heads():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT department_heads.id, department_heads.name, department_heads.email,
               departments.name AS department_name,
               universities.name AS university_name
        FROM department_heads
        JOIN departments ON department_heads.department_id = departments.id
        JOIN universities ON department_heads.university_id = universities.id
    """)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.post("/admins/")
def create_admin(admin: AdminCreate):
    conn = get_connection()
    cursor = conn.cursor()

    # check if university exists
    cursor.execute("SELECT * FROM universities WHERE id = ?", (admin.university_id,))
    university = cursor.fetchone()
    if not university:
        raise HTTPException(status_code=404, detail="University not found.")

    # check if department exists
    cursor.execute(
        "SELECT * FROM departments WHERE id = ? AND university_id = ?",
        (admin.department_id, admin.university_id),
    )
    department = cursor.fetchone()
    if not department:
        raise HTTPException(
            status_code=404, detail="Department not found for given university."
        )

    cursor.execute(
        "INSERT INTO admins (name, email, department_id, university_id) VALUES (?, ?, ?, ?)",
        (admin.name, admin.email, admin.department_id, admin.university_id),
    )
    conn.commit()
    admin_id = cursor.lastrowid
    conn.close()

    return {
        "id": admin_id,
        "name": admin.name,
        "email": admin.email,
        "department_id": admin.department_id,
        "university_id": admin.university_id,
    }


# --- New: List Admins ---
@app.get("/admins/")
def list_admins():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT admins.id, admins.name, admins.email,
               departments.name AS department_name,
               universities.name AS university_name
        FROM admins
        JOIN departments ON admins.department_id = departments.id
        JOIN universities ON admins.university_id = universities.id
    """)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# --- New: Search ---
@app.get("/search/")
def search_all(q: Optional[str] = Query(None)):
    conn = get_connection()
    cursor = conn.cursor()

    results = []

    if not q:
        # 🔵 If no search query, return top 100 most recent entries
        cursor.execute("""
            SELECT universities.id AS university_id,
                   universities.name AS university_name,
                   departments.id AS department_id,
                   departments.name AS department_name,
                   department_heads.id AS department_head_id,
                   department_heads.name AS department_head_name,
                   department_heads.email AS department_head_email,
                   admins.id AS admin_id,
                   admins.name AS admin_name,
                   admins.email AS admin_email
            FROM departments
            JOIN universities ON departments.university_id = universities.id
            LEFT JOIN department_heads ON department_heads.department_id = departments.id
            LEFT JOIN admins ON admins.department_id = departments.id
            ORDER BY departments.id DESC
            LIMIT 100
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # 🔵 Otherwise, perform the full search based on query
    results = []
    # 🔵 Search by University name
    cursor.execute(
        """
        SELECT universities.id AS university_id,
               universities.name AS university_name,
               departments.id AS department_id,
               departments.name AS department_name,
               department_heads.id AS department_head_id,
               department_heads.name AS department_head_name,
               department_heads.email AS department_head_email,
               admins.id AS admin_id,
               admins.name AS admin_name,
               admins.email AS admin_email
        FROM universities
        LEFT JOIN departments ON departments.university_id = universities.id
        LEFT JOIN department_heads ON department_heads.department_id = departments.id
        LEFT JOIN admins ON admins.department_id = departments.id
        WHERE universities.name LIKE ?
    """,
        (f"%{q}%",),
    )
    rows = cursor.fetchall()
    results.extend([dict(row) for row in rows])

    # 🔵 Search by Department name
    cursor.execute(
        """
        SELECT universities.id AS university_id,
               universities.name AS university_name,
               departments.id AS department_id,
               departments.name AS department_name,
               department_heads.id AS department_head_id,
               department_heads.name AS department_head_name,
               department_heads.email AS department_head_email,
               admins.id AS admin_id,
               admins.name AS admin_name,
               admins.email AS admin_email
        FROM departments
        JOIN universities ON departments.university_id = universities.id
        LEFT JOIN department_heads ON department_heads.department_id = departments.id
        LEFT JOIN admins ON admins.department_id = departments.id
        WHERE departments.name LIKE ?
    """,
        (f"%{q}%",),
    )
    rows = cursor.fetchall()
    results.extend([dict(row) for row in rows])

    # 🔵 Search by Department Head name
    cursor.execute(
        """
        SELECT universities.id AS university_id,
               universities.name AS university_name,
               departments.id AS department_id,
               departments.name AS department_name,
               department_heads.id AS department_head_id,
               department_heads.name AS department_head_name,
               department_heads.email AS department_head_email,
               admins.id AS admin_id,
               admins.name AS admin_name,
               admins.email AS admin_email
        FROM department_heads
        JOIN departments ON department_heads.department_id = departments.id
        JOIN universities ON department_heads.university_id = universities.id
        LEFT JOIN admins ON admins.department_id = departments.id
        WHERE department_heads.name LIKE ?
    """,
        (f"%{q}%",),
    )
    rows = cursor.fetchall()
    results.extend([dict(row) for row in rows])

    # 🔵 Search by Admin name
    cursor.execute(
        """
        SELECT universities.id AS university_id,
               universities.name AS university_name,
               departments.id AS department_id,
               departments.name AS department_name,
               department_heads.id AS department_head_id,
               department_heads.name AS department_head_name,
               department_heads.email AS department_head_email,
               admins.id AS admin_id,
               admins.name AS admin_name,
               admins.email AS admin_email
        FROM admins
        JOIN departments ON admins.department_id = departments.id
        JOIN universities ON admins.university_id = universities.id
        LEFT JOIN department_heads ON department_heads.department_id = departments.id
        WHERE admins.name LIKE ?
    """,
        (f"%{q}%",),
    )
    rows = cursor.fetchall()
    results.extend([dict(row) for row in rows])

    conn.close()

    # 🔵 Remove duplicates (since multiple queries might hit same entry)
    unique_results = []
    seen = set()
    for item in results:
        key = tuple(item.items())
        if key not in seen:
            seen.add(key)
            unique_results.append(item)

    return unique_results


@app.post("/catalog/", response_model=CatalogEntry)
def create_catalog_entry(entry: CatalogEntryCreate):
    conn = get_connection()
    cursor = conn.cursor()

    # 🔵 Check for duplicate department head or admin within the same university and department
    cursor.execute(
        """
        SELECT * FROM catalog_entries
        WHERE university_name = ?
        AND department_name = ?
        AND (
            (department_head_name = ? AND department_head_email = ?)
            OR
            (admin_name = ? AND admin_email = ?)
        )
        """,
        (
            entry.university_name,
            entry.department_name,
            entry.department_head_name,
            entry.department_head_email,
            entry.admin_name,
            entry.admin_email,
        ),
    )
    existing = cursor.fetchone()

    if existing:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Duplicate department head or admin for this department/university already exists.",
        )

    # 🔵 Otherwise, insert normally
    cursor.execute(
        """
        INSERT INTO catalog_entries (university_name, department_name,
            department_head_name, department_head_email,
            admin_name, admin_email)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            entry.university_name,
            entry.department_name,
            entry.department_head_name,
            entry.department_head_email,
            entry.admin_name,
            entry.admin_email,
        ),
    )
    conn.commit()
    entry_id = cursor.lastrowid
    conn.close()

    return CatalogEntry(id=entry_id, **entry.dict())


@app.get("/catalog/", response_model=List[CatalogEntry])
def list_catalog_entries(q: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()

    if q:
        cursor.execute(
            """
            SELECT * FROM catalog_entries
            WHERE university_name LIKE ? OR department_name LIKE ?
            OR department_head_name LIKE ? OR admin_name LIKE ?
            LIMIT 100
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM catalog_entries
            ORDER BY id DESC
            LIMIT 100
            """
        )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# 🔵 Delete a catalog entry by ID
@app.delete("/catalog/{entry_id}")
def delete_catalog_entry(entry_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM catalog_entries WHERE id = ?", (entry_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Entry not found.")
    conn.close()

    return {"status": "success"}


# 🔵 Update a catalog entry (optional for later)
@app.patch("/catalog/{entry_id}")
def update_catalog_entry(entry_id: int, entry: CatalogEntryCreate):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE catalog_entries
        SET university_name = ?, department_name = ?,
            department_head_name = ?, department_head_email = ?,
            admin_name = ?, admin_email = ?
        WHERE id = ?
        """,
        (
            entry.university_name,
            entry.department_name,
            entry.department_head_name,
            entry.department_head_email,
            entry.admin_name,
            entry.admin_email,
            entry_id,
        ),
    )
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Entry not found.")
    conn.close()

    return {"status": "success"}
