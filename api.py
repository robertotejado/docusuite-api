from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from werkzeug.security import check_password_hash
import os

app = FastAPI(title="DocuSuite API", version="1.0")

DATABASE_URL = os.environ.get("DATABASE_URL")

# --- MODELOS DE DATOS (Lo que la API espera recibir) ---
class LoginData(BaseModel):
    username: str
    password: str

class DocumentoNuevo(BaseModel):
    usuario_id: int
    titulo: str
    contenido_texto: str

# --- RUTAS DE LA API ---

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

@app.post("/documentos")
def guardar_documento(doc: DocumentoNuevo):
    """Guarda un nuevo documento en la base de datos"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Asumo que tus columnas se llaman usuario_id, titulo y contenido_texto.
        # Usa RETURNING id para que Supabase nos confirme el ID del documento creado.
        query = """
            INSERT INTO documentos (usuario_id, titulo, contenido_texto) 
            VALUES (%s, %s, %s) RETURNING id;
        """
        cur.execute(query, (doc.usuario_id, doc.titulo, doc.contenido_texto))
        nuevo_id = cur.fetchone()[0]
        
        conn.commit() # ¡Importante! Confirma el guardado en la BD
        cur.close()
        conn.close()
        
        return {"success": True, "mensaje": "Documento guardado", "documento_id": nuevo_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documentos/usuario/{usuario_id}")
def listar_documentos(usuario_id: int):
    """Devuelve la lista de documentos de un usuario para el menú lateral"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Traemos solo lo necesario para la lista, ordenado por el más reciente
        cur.execute("SELECT id, titulo FROM documentos WHERE usuario_id = %s ORDER BY id DESC", (usuario_id,))
        filas = cur.fetchall()
        cur.close()
        conn.close()
        
        # Formateamos la respuesta como una lista de diccionarios
        documentos = [{"id": fila[0], "titulo": fila[1]} for fila in filas]
        return {"success": True, "documentos": documentos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))