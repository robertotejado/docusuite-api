import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="DocuSuite API Desktop")

# Tu base de datos (Render lo inyecta automáticamente)
DATABASE_URL = os.environ.get("DATABASE_URL")

# --- MODELOS DE DATOS ---
class LoginRequest(BaseModel):
    username: str
    password: str

class DocumentoNuevo(BaseModel):
    usuario_id: int
    id_proyecto: int
    titulo: str
    autor: str
    contenido_texto: str

class DocumentoActualizar(BaseModel):
    id_proyecto: int
    titulo: str
    contenido_texto: str

# --- AUTENTICACIÓN ---
@app.post("/login")
def login(req: LoginRequest):
    """Verifica el usuario y devuelve su ID"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, password FROM usuarios WHERE username = %s", (req.username,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()

        # Simplificación para la API: asume contraseña en texto plano o hash (ajusta según tu DB)
        from werkzeug.security import check_password_hash
        if user_data and check_password_hash(user_data['password'], req.password):
            return {"success": True, "usuario_id": user_data["id"]}
        
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- PROYECTOS ---
@app.get("/proyectos/usuario/{usuario_id}")
def obtener_proyectos(usuario_id: int):
    """Devuelve la lista de proyectos de un usuario"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, nombre FROM proyectos WHERE usuario_id = %s ORDER BY fecha_creacion DESC", (usuario_id,))
        proyectos = cur.fetchall()
        cur.close()
        conn.close()
        return proyectos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- DOCUMENTOS (CRUD COMPLETO) ---
@app.get("/documentos/usuario/{usuario_id}")
def obtener_documentos(usuario_id: int):
    """(READ) Lista todos los documentos de un usuario"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, titulo, fecha_modificacion FROM documentos WHERE usuario_id = %s ORDER BY fecha_modificacion DESC", (usuario_id,))
        docs = cur.fetchall()
        cur.close()
        conn.close()
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documentos/{documento_id}")
def leer_documento(documento_id: int):
    """(READ) Descarga un documento completo para el editor"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, id_proyecto, titulo, contenido_texto FROM documentos WHERE id = %s", (documento_id,))
        doc = cur.fetchone()
        cur.close()
        conn.close()
        
        if doc:
            return doc
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documentos")
def crear_documento(doc: DocumentoNuevo):
    """(CREATE) Guarda un documento nuevo en la base de datos"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        query = """
            INSERT INTO documentos (usuario_id, id_proyecto, titulo, autor, contenido_texto) 
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """
        cur.execute(query, (doc.usuario_id, doc.id_proyecto, doc.titulo, doc.autor, doc.contenido_texto))
        nuevo_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "id": nuevo_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/documentos/{documento_id}")
def actualizar_documento(documento_id: int, doc: DocumentoActualizar):
    """(UPDATE) Sobrescribe un documento existente"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        query = """
            UPDATE documentos 
            SET id_proyecto = %s, titulo = %s, contenido_texto = %s, fecha_modificacion = CURRENT_TIMESTAMP 
            WHERE id = %s
        """
        cur.execute(query, (doc.id_proyecto, doc.titulo, doc.contenido_texto, documento_id))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "mensaje": "Documento actualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.delete("/documentos/{documento_id}")
def eliminar_documento(documento_id: int):
    """(DELETE) Borra un documento de la base de datos"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM documentos WHERE id = %s", (documento_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "mensaje": "Documento eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))