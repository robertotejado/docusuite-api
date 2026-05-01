from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2
from werkzeug.security import check_password_hash
import os

app = FastAPI(title="DocuSuite API", version="1.0")

DATABASE_URL = os.environ.get("DATABASE_URL")

# --- MODELOS DE DATOS ---
class LoginData(BaseModel):
    username: str
    password: str

class DocumentoNuevo(BaseModel):
    usuario_id: int
    titulo: str
    contenido_texto: str
    id_proyecto: Optional[int] = None  # Opcional, por si lo usas
    autor: Optional[str] = None        # Opcional

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
    """Guarda o actualiza un documento en la base de datos"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        query = """
            INSERT INTO documentos (usuario_id, titulo, contenido_texto, id_proyecto, autor) 
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
        """
        cur.execute(query, (doc.usuario_id, doc.titulo, doc.contenido_texto, doc.id_proyecto, doc.autor))
        nuevo_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"success": True, "mensaje": "Documento guardado", "documento_id": nuevo_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documentos/usuario/{usuario_id}")
def listar_documentos(usuario_id: int):
    """Devuelve la lista de documentos (id, titulo y fecha) para el menú lateral"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT id, titulo, fecha_modificacion FROM documentos WHERE usuario_id = %s ORDER BY id DESC", (usuario_id,))
        filas = cur.fetchall()
        cur.close()
        conn.close()
        
        # Formateamos la respuesta
        documentos = [{"id": fila[0], "titulo": fila[1], "fecha": fila[2]} for fila in filas]
        return {"success": True, "documentos": documentos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documentos/{documento_id}")
def leer_documento(documento_id: int):
    """Devuelve el contenido completo (HTML) de un documento específico"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT titulo, contenido_texto FROM documentos WHERE id = %s", (documento_id,))
        doc = cur.fetchone()
        cur.close()
        conn.close()
        
        if doc:
            return {"success": True, "titulo": doc[0], "contenido_texto": doc[1]}
        else:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))