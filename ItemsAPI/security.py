import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import pyodbc
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# --- Configuración de Seguridad ---
# Para producción, esta clave debería ser más compleja y estar en una variable de entorno
SECRET_KEY = os.getenv("SECRET_KEY", "un-secreto-muy-dificil-de-adivinar")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Contexto para hashear contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de autenticación que apunta a nuestro endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Modelos de Datos (Pydantic) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserInDB(BaseModel):
    user_id: int
    username: str
    hashed_password: str
    role: str
    is_active: bool 


# --- Funciones de Utilidad ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Lógica de Dependencia ---
# Esta función se ejecutará en cada endpoint protegido

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = None
    conn = None
    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={os.getenv('DB_SERVER')},1433;"
            f"DATABASE={os.getenv('DB_NAME')};"
            f"UID={os.getenv('DB_USER')};"
            f"PWD={os.getenv('DB_PASSWORD')};"
            f"Encrypt=yes;TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Actualizamos la consulta para que traiga el nuevo campo
        cursor.execute("SELECT user_id, username, hashed_password, role, is_active FROM users WHERE username = ?", token_data.username)
        user_row = cursor.fetchone()

        if user_row is None:
            raise credentials_exception

        user = UserInDB(
            user_id=user_row[0], 
            username=user_row[1], 
            hashed_password=user_row[2],
            role=user_row[3],
            is_active=user_row[4] # <-- AÑADIMOS EL CAMPO is_active
        )
    except (pyodbc.Error, KeyError):
        raise credentials_exception
    finally:
        if conn:
            conn.close()

    # --- ¡NUEVA VERIFICACIÓN DE SEGURIDAD! ---
    # Si el usuario no está activo, rechazamos el acceso
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo o pendiente de aprobación")

    return user

# --- NUEVA DEPENDENCIA PARA VERIFICAR ADMINS ---
def get_current_admin_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No tienes permisos suficientes para esta operación"
        )
    return current_user