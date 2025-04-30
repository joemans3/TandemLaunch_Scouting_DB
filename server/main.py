import csv
import io
import sqlite3
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from .database import get_connection, initialize_database
from .external_lookup import lookup_country_by_name, lookup_ror_for_university
from .models import (
    Country,
    EmailLogOut,
    EmailThreadLog,
    PersonCreate,
    PersonOut,
)

app = FastAPI()
initialize_database()


@app.get("/people/{person_id}/emails/", response_model=List[EmailLogOut])
def get_person_emails(person_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, timestamp, subject, body, thread_id
        FROM email_logs
        WHERE person_id = ?
        ORDER BY timestamp DESC
        """,
        (person_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/emails/")
def ingest_email_thread(log: EmailThreadLog):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, email FROM people")
    known_people = cursor.fetchall()

    matched = []
    for row in known_people:
        if row["email"] in log.participants:
            matched.append(row["id"])

    if not matched:
        conn.close()
        raise HTTPException(status_code=404, detail="No matching people found.")

    for person_id in matched:
        cursor.execute(
            """
            INSERT INTO email_logs (person_id, timestamp, subject, body, thread_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (person_id, log.timestamp, log.subject, log.body, log.thread_id),
        )

    conn.commit()
    conn.close()
    return {"status": "ok", "matched": matched}


@app.post("/email_logs/")
def log_email(entry: EmailLogEntry):
    conn = get_connection()
    cursor = conn.cursor()

    matched_ids = []
    for email in entry.participants:
        cursor.execute("SELECT id FROM people WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row:
            matched_ids.append(row["id"])

    for person_id in matched_ids:
        cursor.execute(
            """
            INSERT INTO email_logs (person_id, timestamp, subject, body, thread_id)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                person_id,
                entry.timestamp,
                entry.subject,
                entry.body,
                entry.thread_id,
            ),
        )

    conn.commit()
    conn.close()

    return {"matched_people": matched_ids, "status": "logged"}


@app.get("/people/export_csv")
def export_people_csv():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.name, p.email, u.name AS university, c.name AS country,
               p.subfield, p.subfield_name, p.role, p.notes
        FROM people p
        JOIN universities u ON p.university_id = u.id
        JOIN countries c ON p.country_id = c.id
        ORDER BY p.id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Name",
            "Email",
            "University",
            "Country",
            "Subfield",
            "Subfield Name",
            "Role",
            "Notes",
        ]
    )

    for row in rows:
        writer.writerow(
            [
                row["name"],
                row["email"],
                row["university"],
                row["country"],
                row["subfield"],
                row["subfield_name"],
                row["role"],
                row["notes"],
            ]
        )

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=people_export.csv"},
    )


@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.post("/people/", response_model=PersonOut)
def create_person(person: PersonCreate):
    conn = get_connection()
    cursor = conn.cursor()

    # --- Resolve university ---
    cursor.execute("SELECT id FROM universities WHERE name = ?", (person.university,))
    row = cursor.fetchone()
    if row:
        university_id = row["id"]
    else:
        cursor.execute(
            "SELECT university_id FROM university_aliases WHERE alias = ?",
            (person.university,),
        )
        alias_row = cursor.fetchone()
        if alias_row:
            university_id = alias_row["university_id"]
        else:
            result = lookup_ror_for_university(person.university)
            if not result:
                conn.close()
                raise HTTPException(
                    status_code=404, detail="University not found via ROR."
                )

            canonical_name, ror_id, aliases = result

        try:
            cursor.execute(
                "INSERT INTO universities (name, ror_id) VALUES (?, ?)",
                (canonical_name, ror_id),
            )
            university_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Already exists — get its ID
            cursor.execute("SELECT id FROM universities WHERE ror_id = ?", (ror_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                raise HTTPException(
                    status_code=400,
                    detail="Failed to retrieve existing university after conflict.",
                )
            university_id = row["id"]

            conn.commit()

    # --- Resolve country ---
    cursor.execute("SELECT id FROM countries WHERE name = ?", (person.country,))
    row = cursor.fetchone()
    if row:
        country_id = row["id"]
    else:
        result = lookup_country_by_name(person.country)
        if not result:
            conn.close()
            raise HTTPException(
                status_code=404, detail="Country not found via ISO lookup."
            )
        canonical_name, code = result
        try:
            cursor.execute(
                "INSERT INTO countries (name, code) VALUES (?, ?)",
                (canonical_name, code),
            )
            country_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Already exists — get ID by code
            cursor.execute("SELECT id FROM countries WHERE code = ?", (code,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                raise HTTPException(
                    status_code=400,
                    detail="Failed to retrieve existing country after conflict.",
                )
            country_id = row["id"]
        conn.commit()

    # --- Insert person ---
    try:
        cursor.execute(
            """
            INSERT INTO people (
                name, email, university_id, country_id,
                subfield, subfield_name, role, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                person.name,
                person.email,
                university_id,
                country_id,
                person.subfield,
                person.subfield_name,
                person.role,
                person.notes,
            ),
        )
        conn.commit()
        person_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already exists.")

    conn.close()
    return PersonOut(
        id=person_id,
        university_id=university_id,
        country_id=country_id,
        **person.dict(),
    )


@app.delete("/people/{person_id}")
def delete_person(person_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    # Check existence
    cursor.execute("SELECT * FROM people WHERE id = ?", (person_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Person not found.")

    # Perform deletion
    cursor.execute("DELETE FROM people WHERE id = ?", (person_id,))
    conn.commit()
    conn.close()

    return {"status": "success", "message": f"Person {person_id} deleted."}


@app.patch("/people/{person_id}", response_model=PersonOut)
def update_person(person_id: int, person: PersonCreate):
    conn = get_connection()
    cursor = conn.cursor()

    # --- Resolve university ---
    cursor.execute("SELECT id FROM universities WHERE name = ?", (person.university,))
    row = cursor.fetchone()
    if row:
        university_id = row["id"]
    else:
        cursor.execute(
            "SELECT university_id FROM university_aliases WHERE alias = ?",
            (person.university,),
        )
        alias_row = cursor.fetchone()
        if alias_row:
            university_id = alias_row["university_id"]
        else:
            result = lookup_ror_for_university(person.university)
            if not result:
                conn.close()
                raise HTTPException(
                    status_code=404, detail="University not found via ROR."
                )
            canonical_name, ror_id, aliases = result
        try:
            cursor.execute(
                "INSERT INTO universities (name, ror_id) VALUES (?, ?)",
                (canonical_name, ror_id),
            )
            university_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Already exists — get its ID
            cursor.execute("SELECT id FROM universities WHERE ror_id = ?", (ror_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                raise HTTPException(
                    status_code=400,
                    detail="Failed to retrieve existing university after conflict.",
                )
            university_id = row["id"]
            conn.commit()

    # --- Resolve country ---
    cursor.execute("SELECT id FROM countries WHERE name = ?", (person.country,))
    row = cursor.fetchone()
    if row:
        country_id = row["id"]
    else:
        result = lookup_country_by_name(person.country)
        if not result:
            conn.close()
            raise HTTPException(
                status_code=404, detail="Country not found via ISO lookup."
            )
        canonical_name, code = result
        try:
            cursor.execute(
                "INSERT INTO countries (name, code) VALUES (?, ?)",
                (canonical_name, code),
            )
            country_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Already exists — get ID by code
            cursor.execute("SELECT id FROM countries WHERE code = ?", (code,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                raise HTTPException(
                    status_code=400,
                    detail="Failed to retrieve existing country after conflict.",
                )
            country_id = row["id"]
        conn.commit()

    # --- Ensure person exists ---
    cursor.execute("SELECT * FROM people WHERE id = ?", (person_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Person not found.")

    # --- Perform update ---
    try:
        cursor.execute(
            """
            UPDATE people SET
                name = ?, email = ?, university_id = ?, country_id = ?,
                subfield = ?, subfield_name = ?, role = ?, notes = ?
            WHERE id = ?
        """,
            (
                person.name,
                person.email,
                university_id,
                country_id,
                person.subfield,
                person.subfield_name,
                person.role,
                person.notes,
                person_id,
            ),
        )
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="Update failed. No matching person or invalid university/country reference.",
            )
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already exists.")

    conn.close()
    return PersonOut(
        id=person_id,
        university_id=university_id,
        country_id=country_id,
        **person.dict(),
    )


@app.get("/people/", response_model=List[PersonOut])
def list_people(
    role: Optional[str] = None,
    country: Optional[str] = None,
    subfield: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT p.*, u.name AS university, c.name AS country
        FROM people p
        JOIN universities u ON p.university_id = u.id
        JOIN countries c ON p.country_id = c.id
    """
    filters = []
    params = []

    # Optional filters
    if role:
        filters.append("p.role = ?")
        params.append(role)
    if country:
        filters.append("c.name = ?")
        params.append(country)
    if subfield:
        filters.append("p.subfield = ?")
        params.append(subfield)
    if q:
        filters.append("""
            (
                p.name LIKE ?
                OR p.email LIKE ?
                OR u.name LIKE ?
                OR c.name LIKE ?
            )
        """)
        params.extend([f"%{q}%"] * 4)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY p.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    return [
        PersonOut(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            university=row["university"],
            country=row["country"],
            university_id=row["university_id"],
            country_id=row["country_id"],
            subfield=row["subfield"],
            subfield_name=row["subfield_name"],
            role=row["role"],
            notes=row["notes"],
        )
        for row in rows
    ]


@app.get("/universities/")
def list_universities(limit: int = 1000):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM universities ORDER BY name LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/universities/aliases/")
def create_university_alias(alias: str, canonical_name: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM universities WHERE name = ?", (canonical_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Canonical university not found.")

    try:
        cursor.execute(
            "INSERT INTO university_aliases (alias, university_id) VALUES (?, ?)",
            (alias, row["id"]),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Alias already exists.")

    conn.close()
    return {"alias": alias, "university_id": row["id"]}


@app.get("/countries/", response_model=List[Country])
def list_countries():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM countries ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
