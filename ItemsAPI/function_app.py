import logging
import traceback
import os
import pyodbc
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel
import pandas as pd
import io

# Importaciones de seguridad
from . import security
from fastapi.security import OAuth2PasswordRequestForm


app = FastAPI(title="Circuits DB API")

# --- Lógica de Conexión a la Base de Datos Local ---
db_server = os.getenv("DB_SERVER")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

conn_str = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={db_server},1433;"
    f"DATABASE={db_name};"
    f"UID={db_user};"
    f"PWD={db_password};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=yes;"
)

def get_db_connection():
    try:
        return pyodbc.connect(conn_str)
    except pyodbc.Error:
        logging.error(f"PYODBC CONNECTION ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=503, detail="Database connection error.")

def execute_query(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params) if params else cursor.execute(query)
        if cursor.description is None:
            return []
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()

# --- Modelos de Datos ---
class Circuit(BaseModel):
    circuitId: int
    name: str
    location: Optional[str] = None
    country: Optional[str] = None

class Pilot(BaseModel):
    pilotId: int
    name: str
    nationality: Optional[str] = None
    years_active: Optional[str] = None
    championships: Optional[float] = None
    race_entries: Optional[float] = None
    race_starts: Optional[float] = None
    pole_positions: Optional[float] = None
    race_wins: Optional[float] = None
    podiums: Optional[float] = None
    fastest_laps: Optional[float] = None

class UserCreate(BaseModel):
    username: str
    password: str
    
class User(BaseModel):
    username: str
    role: str
    is_active: bool

# --- Endpoints de Autenticación y Usuarios ---
@app.post("/token", response_model=security.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, hashed_password, role, is_active FROM users WHERE username = ?", form_data.username)
        columns = [column[0] for column in cursor.description]
        user_row_data = cursor.fetchone()

        if not user_row_data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos", headers={"WWW-Authenticate": "Bearer"})
        
        user_dict = dict(zip(columns, user_row_data))

        if not user_dict['is_active'] or not security.verify_password(form_data.password, user_dict['hashed_password']):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos, o cuenta inactiva.", headers={"WWW-Authenticate": "Bearer"})
        
        access_token = security.create_access_token(data={"sub": user_dict['username']})
        return {"access_token": access_token, "token_type": "bearer", "role": user_dict['role']}
    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate):
    hashed_password = security.pwd_context.hash(user.password)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, hashed_password, role, is_active) VALUES (?, ?, 'viewer', 0)", user.username, hashed_password)
        conn.commit()
    except pyodbc.IntegrityError:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe.")
    finally:
        conn.close()
    return {"message": f"Usuario '{user.username}' registrado. Pendiente de aprobación."}

@app.get("/users/me", response_model=User)
def read_users_me(current_user: security.UserInDB = Depends(security.get_current_user)):
    return current_user

# --- Endpoints de Admin ---
@app.get("/admin/pending-users", response_model=List[str])
def get_pending_users(current_user: security.UserInDB = Depends(security.get_current_admin_user)):
    pending_users = execute_query("SELECT username FROM users WHERE is_active = 0")
    return [user['username'] for user in pending_users]

@app.post("/admin/approve-user/{username}", status_code=status.HTTP_200_OK)
def approve_user(username: str, current_user: security.UserInDB = Depends(security.get_current_admin_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_active = 1 WHERE username = ?", username)
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    finally:
        conn.close()
    return {"message": f"Usuario '{username}' ha sido aprobado."}

@app.delete("/admin/decline-user/{username}", status_code=status.HTTP_200_OK)
def decline_user(username: str, current_user: security.UserInDB = Depends(security.get_current_admin_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE username = ? AND is_active = 0", username)
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario pendiente no encontrado.")
    finally:
        conn.close()
    return {"message": f"La solicitud del usuario '{username}' ha sido rechazada."}

# --- Endpoints de Subida de Ficheros (Solo Admin) ---
@app.post("/upload-circuits-csv/", status_code=201)
async def upload_circuits_csv(file: UploadFile = File(...), current_user: security.UserInDB = Depends(security.get_current_admin_user)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Tipo de fichero inválido. Por favor, sube un CSV.")
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        if not {'name', 'location', 'country'}.issubset(df.columns):
            raise HTTPException(status_code=400, detail="El CSV debe contener las columnas 'name', 'location' y 'country'.")
        conn = get_db_connection()
        cursor = conn.cursor()
        for row in df.itertuples(index=False):
            cursor.execute("INSERT INTO circuits (name, location, country) VALUES (?, ?, ?)", (row.name, row.location, row.country))
        conn.commit()
        inserted_rows = len(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el fichero: {e}")
    finally:
        conn.close()
    return {"detail": f"Se han insertado {inserted_rows} nuevos circuitos desde {file.filename}."}

@app.post("/upload-pilots-csv/", status_code=201)
async def upload_pilots_csv(file: UploadFile = File(...), current_user: security.UserInDB = Depends(security.get_current_admin_user)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Tipo de fichero inválido. Por favor, sube un CSV.")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        column_mapping = {
            'Driver': 'name', 'Nationality': 'nationality', 'Seasons': 'years_active',
            'Championships': 'championships', 'Race_Entries': 'race_entries', 'Race_Starts': 'race_starts',
            'Pole_Positions': 'pole_positions', 'Race_Wins': 'race_wins', 'Podiums': 'podiums',
            'Fastest_Laps': 'fastest_laps'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        expected_db_columns = {'name', 'nationality', 'years_active', 'championships', 'race_entries', 'race_starts', 'pole_positions', 'race_wins', 'podiums', 'fastest_laps'}
        if not expected_db_columns.issubset(df.columns):
            missing_cols = expected_db_columns - set(df.columns)
            raise HTTPException(status_code=400, detail=f"Faltan las siguientes columnas en el CSV después del mapeo: {', '.join(missing_cols)}")

        float_columns = ['championships', 'race_entries', 'race_starts', 'pole_positions', 'race_wins', 'podiums', 'fastest_laps']
        for col in float_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)
        df['years_active'] = df['years_active'].astype(str).fillna('')

        sql_query = "INSERT INTO pilots (name, nationality, years_active, championships, race_entries, race_starts, pole_positions, race_wins, podiums, fastest_laps) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        
        for row in df.itertuples(index=False):
            params = (
                row.name, row.nationality, row.years_active, row.championships, 
                row.race_entries, row.race_starts, row.pole_positions, 
                row.race_wins, row.podiums, row.fastest_laps
            )
            cursor.execute(sql_query, params)

        conn.commit()
        inserted_rows = len(df)
    except Exception as e:
        logging.error(f"Error procesando el fichero CSV: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error procesando el fichero: {str(e)}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
    return {"detail": f"Se han insertado {inserted_rows} nuevos pilotos desde {file.filename}."}

# --- Endpoints de Datos Protegidos ---
@app.get("/items", response_model=List[Circuit])
def get_all_items(current_user: security.UserInDB = Depends(security.get_current_user)):
    return execute_query("SELECT * FROM circuits")

@app.get("/items/{item_id}", response_model=Circuit)
def get_item_by_id(item_id: int, current_user: security.UserInDB = Depends(security.get_current_user)):
    results = execute_query("SELECT * FROM circuits WHERE circuitId = ?", (item_id,))
    if not results:
        raise HTTPException(status_code=404, detail="Item not found")
    return results[0]

@app.get("/location/{location_name}", response_model=List[Circuit])
def get_circuits_by_location(location_name: str, current_user: security.UserInDB = Depends(security.get_current_user)):
    return execute_query("SELECT * FROM circuits WHERE location = ?", (location_name,))

@app.get("/country/{country_name}", response_model=List[Circuit])
def get_circuits_by_country(country_name: str, current_user: security.UserInDB = Depends(security.get_current_user)):
    return execute_query("SELECT * FROM circuits WHERE country = ?", (country_name,))

@app.get("/pilots", response_model=List[Pilot])
def get_all_pilots(current_user: security.UserInDB = Depends(security.get_current_admin_user)):
    return execute_query("SELECT * FROM pilots")

@app.get("/pilots/search/{pilot_name}", response_model=List[Pilot])
def search_pilots_by_name(pilot_name: str, current_user: security.UserInDB = Depends(security.get_current_admin_user)):
    """Busca pilotos por nombre (Solo para Admins)."""
    query = "SELECT * FROM pilots WHERE name LIKE ?"
    params = (f"%{pilot_name}%",)
    return execute_query(query, params)
