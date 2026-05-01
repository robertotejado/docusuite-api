from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from werkzeug.security import check_password_hash
import os

app = FastAPI()

# La URL la configuraremos en las variables de entorno del nuevo proyecto
DATABASE_URL = os.environ.get("DATABASE_URL")

class LoginData(BaseModel):
    username: str
    password: str

@app.get("/")
def home():
    return {"status": "DocuSuite API Online"}

@app.post("/login")
def login(data: LoginData):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT id, password FROM usuarios WHERE username = %s", (data.username,))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if user and check_password_hash(user[1], data.password):
            return {"success": True, "usuario_id": user[0]}
        else:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))