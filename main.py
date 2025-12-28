from fastapi import FastAPI, HTTPException
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
from fastapi import File, Form, UploadFile
from pydantic import BaseModel
import pymysql
from datetime import date
import base64
import uvicorn

import requests, csv, io, os
from dotenv import load_dotenv


load_dotenv()

# ------------------------------------------------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials= True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------------------

db_config = {
    'host': 'srv1073.hstgr.io',
    'database': 'u771906953_barreto',
    'user': 'u771906953_barreto',
    'password': 'MQPj3:6GY_hFfjA',
    'port': 3306
}

def get_connection():
    try:
        conn = pymysql.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            port=db_config['port']
        )
        return conn
    except Exception as e:
        print("Erro ao conectar ao banco:", e)
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados.")

# ------------------------------------------------------------------------------------------


class LoginRequest(BaseModel):
    usuario: str
    senha: str
    
@app.post("/login")
def login(data: LoginRequest):
    conn = None
    try:
        conn = get_connection()

        query = """
            SELECT id, nome, senha, foto
            FROM tb_pessoas
            WHERE nome = %s;
        """

        df = pd.read_sql(query, conn, params=[data.usuario])

        if df.empty:
            raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")

        usuario_encontrado = df[df["senha"] == data.senha]

        if usuario_encontrado.empty:
            raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")

        id = int(usuario_encontrado.iloc[0]["id"])
        nome = usuario_encontrado.iloc[0]["nome"]
        foto_blob = usuario_encontrado.iloc[0]["foto"]

        # BLOB -> Base64
        foto_base64 = None
        if foto_blob:
            foto_base64 = base64.b64encode(foto_blob).decode("utf-8")

        return {
            "success": True,
            "id": id,
            "nome": nome,
            "foto": foto_base64
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro inesperado no login: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")
    finally:
        if conn:
            conn.close()


# ------------------------------------------------------------------------------------------
# Add Piscineiro

class Add_user(BaseModel):
    nome: str
    senha: str
    foto: str


@app.post("/add_piscineiro")
def inserir_usuario(mov: Add_user):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            query = """
                INSERT INTO tb_pessoas (nome, senha, foto)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (mov.nome, mov.senha, mov.foto)) 
            conn.commit()
        return {"success": True, "message": "Piscineiro inserido com sucesso"}
    except Exception as e:
        print("Erro:", e)
        raise HTTPException(status_code=500, detail="Erro ao inserir Usuário")
    finally:
        if conn:
            conn.close()


# ------------------------------------------------------------------------------------------

class UpdateSenha(BaseModel):
    id: int
    senha: str


@app.post("/update_senha")
def update_senha(data: UpdateSenha):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:

            query = "UPDATE tb_pessoas SET senha = %s WHERE id = %s"
            cursor.execute(query, (data.senha, data.id))
            conn.commit()

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Piscineiro não encontrado")

        return {"success": True, "message": "Senha atualizada com sucesso"}

    except Exception as e:
        print("Erro:", e)
        raise HTTPException(status_code=500, detail="Erro ao atualizar senha")

    finally:
        if conn:
            conn.close()

@app.post("/update_foto")
async def update_foto(
    id: int = Form(...),
    foto: UploadFile = File(...)
):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:

            # Lê o conteúdo binário da imagem
            conteudo_foto = await foto.read()

            query = "UPDATE tb_pessoas SET foto = %s WHERE id = %s"
            cursor.execute(query, (conteudo_foto, id))
            conn.commit()

        return {"success": True, "message": "Foto atualizada com sucesso"}

    except Exception as e:
        print("Erro:", e)
        raise HTTPException(status_code=500, detail="Erro ao atualizar a foto")

    finally:
        if conn:
            conn.close()    


# -------------------------------------------------------------------


@app.get("/piscineiro/{id}")
def get_piscineiro(id: int):
    conn = None
    try:
        conn = get_connection()

        query = """
            SELECT id, nome, senha, foto
            FROM tb_pessoas
            WHERE id = %s;
        """

        df = pd.read_sql(query, conn, params=[id])

        if df.empty:
            raise HTTPException(status_code=404, detail="Piscineiro não encontrado")

        foto_bin = df.iloc[0]["foto"]

        if foto_bin:
            foto_base64 = base64.b64encode(foto_bin).decode("utf-8")
        else:
            foto_base64 = None

        return {
            "id": int(df.iloc[0]["id"]),
            "nome": str(df.iloc[0]["nome"]),
            "senha": str(df.iloc[0]["senha"]),
            "foto": foto_base64
        }

    except Exception as e:
        print("Erro ao carregar piscineiro:", e)
        raise HTTPException(status_code=500, detail="Erro ao buscar informações do piscineiro.")
    finally:
        if conn:
            conn.close()



# ------------------------------------------------------------------------------------------

@app.get("/cliente/{id_piscineiro}")
def get_clientes(id_piscineiro: int):
    conn = None
    try:
        conn = get_connection()

        query = """
            SELECT 
                id,
                nome,
                `cnpj/cpf`,
                id_piscineiro
            FROM 
                tb_cliente
            WHERE 
                id_piscineiro = %s;
        """

        df = pd.read_sql(query, conn, params=[id_piscineiro])
        return df.to_dict(orient="records")

    except Exception as e:
        print("Erro:", e)
        raise HTTPException(status_code=500, detail="Erro ao acessar o banco de dados.")
    finally:
        if conn:
            conn.close()


# ------------------------------------------------------------------------------------------
class Movimentacao(BaseModel):
    id_user: int
    status: str
    categoria: str
    fornecedor: str
    valor: float
    tipo: str
    data: date

# ------------------------------------------------------------------------------------------

@app.post("/add_atendimento")
def inserir_movimentacao(mov: Movimentacao):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            query = """
                INSERT INTO tb_mov (data, categoria, id_piscineiro)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (mov.data, mov.categoria, mov.fornecedor, mov.tipo, mov.status, mov.valor, mov.id_user))
            conn.commit()
        return {"success": True, "message": "Movimentação inserida com sucesso"}
    except Exception as e:
        print("Erro:", e)
        raise HTTPException(status_code=500, detail="Erro ao inserir movimentação")
    finally:
        if conn:
            conn.close()


# ------------------------------------------------------------------------------------------

# @app.get("/atendimentos")
# def get_atendimentos(piscineiro: int, data: str = None):
#     conn = None
#     try:
#         conn = get_connection()

#         query = """
#             SELECT 
#                 id,
#                 cliente,
#                 DATE(data) AS data
#             FROM tb_atendimentos
#             WHERE piscineiro = %s
#         """

#         params = [piscineiro]

#         if data:
#             query += " AND DATE(data) = %s"
#             params.append(data)

#         df = pd.read_sql(query, conn, params=params)

#         return df.to_dict(orient="records")

#     except Exception as e:
#         print("Erro ao carregar atendimentos:", e)
#         raise HTTPException(status_code=500, detail="Erro ao buscar atendimentos.")
#     finally:
#         if conn:
#             conn.close()


@app.get("/atendimentos")
def get_atendimentos(piscineiro: int, data: str = None):
    conn = None
    try:
        conn = get_connection()

        if not data:
            data = date.today().isoformat()

        query = """
            SELECT 
                id,
                cliente,
                DATE(data) AS data
            FROM tb_atendimentos
            WHERE piscineiro = %s
              AND DATE(data) = %s
            ORDER BY data
        """

        params = [piscineiro, data]

        df = pd.read_sql(query, conn, params=params)
        return df.to_dict(orient="records")

    except Exception as e:
        print("Erro ao carregar atendimentos:", e)
        raise HTTPException(status_code=500, detail="Erro ao buscar atendimentos.")
    finally:
        if conn:
            conn.close()



# uvicorn main:app --reload

# uvicorn main:app --host 0.0.0.0 --port 10000


