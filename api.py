import os
import jwt
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from werkzeug.security import check_password_hash, generate_password_hash

app = FastAPI(title="DocuSuite API Desktop Segura")
DATABASE_URL = os.environ.get("DATABASE_URL")

# --- CONFIGURACIÓN JWT ---
SECRET_KEY = "tu_clave_super_secreta_docusuite" 
ALGORITHM = "HS256"

def crear_token(usuario_id: int):
    caducidad = datetime.utcnow() + timedelta(hours=24) 
    return jwt.encode({"user_id": usuario_id, "exp": caducidad}, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta el Token de seguridad")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El Token ha caducado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido o falsificado")

# --- MODELOS DE DATOS ---
class LoginRequest(BaseModel):
    username: str
    password: str

class UsuarioNuevo(BaseModel):
    username: str
    password: str

class UsuarioActualizar(BaseModel):
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

class ProyectoNuevo(BaseModel):
    usuario_id: int
    nombre: str
    tipo: str

class ProyectoActualizar(BaseModel):
    nombre: str
    tipo: str

# --- AUTENTICACIÓN ---
@app.post("/login")
def login(req: LoginRequest):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, password FROM usuarios WHERE username = %s", (req.username,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()

        if user_data and check_password_hash(user_data['password'], req.password):
            token = crear_token(user_data["id"])
            return {"success": True, "usuario_id": user_data["id"], "token": token}
        
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# --- USUARIOS (CRUD COMPLETO) ---
# ==========================================
@app.get("/usuarios")
def obtener_usuarios(admin_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, username FROM usuarios ORDER BY id ASC")
        usuarios = cur.fetchall()
        cur.close()
        conn.close()
        return usuarios
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register")
def crear_usuario(user: UsuarioNuevo, admin_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE username = %s", (user.username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=400, detail="El usuario ya existe")

        hashed_pw = generate_password_hash(user.password)
        cur.execute("INSERT INTO usuarios (username, password) VALUES (%s, %s) RETURNING id", 
                    (user.username, hashed_pw))
        nuevo_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "id": nuevo_id, "mensaje": "Usuario creado"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/usuarios/{usuario_id}")
def actualizar_usuario(usuario_id: int, user: UsuarioActualizar, admin_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        hashed_pw = generate_password_hash(user.password)
        cur.execute("UPDATE usuarios SET username = %s, password = %s WHERE id = %s", 
                    (user.username, hashed_pw, usuario_id))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "mensaje": "Usuario actualizado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/usuarios/{usuario_id}")
def eliminar_usuario(usuario_id: int, admin_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "mensaje": "Usuario eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# --- PROYECTOS (CRUD COMPLETO) ---
# ==========================================
@app.get("/proyectos/usuario/{usuario_id}")
def obtener_proyectos(usuario_id: int, user_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, nombre, tipo FROM proyectos WHERE usuario_id = %s ORDER BY fecha_creacion DESC", (usuario_id,))
        proyectos = cur.fetchall()
        cur.close()
        conn.close()
        return proyectos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/proyectos")
def crear_proyecto(proy: ProyectoNuevo, user_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO proyectos (nombre, tipo, usuario_id) VALUES (%s, %s, %s) RETURNING id", 
                    (proy.nombre, proy.tipo, proy.usuario_id))
        nuevo_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "id": nuevo_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/proyectos/{proyecto_id}")
def actualizar_proyecto(proyecto_id: int, proy: ProyectoActualizar, user_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("UPDATE proyectos SET nombre = %s, tipo = %s WHERE id = %s", 
                    (proy.nombre, proy.tipo, proyecto_id))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "mensaje": "Proyecto actualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/proyectos/{proyecto_id}")
def eliminar_proyecto(proyecto_id: int, user_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM proyectos WHERE id = %s", (proyecto_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "mensaje": "Proyecto eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# --- DOCUMENTOS (CRUD COMPLETO) ---
# ==========================================
@app.get("/documentos/usuario/{usuario_id}")
def obtener_documentos(usuario_id: int, user_id: int = Depends(verificar_token)):
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
def leer_documento(documento_id: int, user_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, id_proyecto, titulo, contenido_texto FROM documentos WHERE id = %s", (documento_id,))
        doc = cur.fetchone()
        cur.close()
        conn.close()
        if doc: return doc
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documentos")
def crear_documento(doc: DocumentoNuevo, user_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        query = "INSERT INTO documentos (usuario_id, id_proyecto, titulo, autor, contenido_texto) VALUES (%s, %s, %s, %s, %s) RETURNING id"
        cur.execute(query, (doc.usuario_id, doc.id_proyecto, doc.titulo, doc.autor, doc.contenido_texto))
        nuevo_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "id": nuevo_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/documentos/{documento_id}")
def actualizar_documento(documento_id: int, doc: DocumentoActualizar, user_id: int = Depends(verificar_token)):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        query = "UPDATE documentos SET id_proyecto = %s, titulo = %s, contenido_texto = %s, fecha_modificacion = CURRENT_TIMESTAMP WHERE id = %s"
        cur.execute(query, (doc.id_proyecto, doc.titulo, doc.contenido_texto, documento_id))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "mensaje": "Documento actualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.delete("/documentos/{documento_id}")
def eliminar_documento(documento_id: int, user_id: int = Depends(verificar_token)):
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