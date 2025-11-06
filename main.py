from fastapi import FastAPI, HTTPException
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pymysql
from datetime import date
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
            SELECT id, nome, senha
            FROM tb_piscineiro
            WHERE nome = %s;
        """
        df = pd.read_sql(query, conn, params=[data.usuario])

        if df.empty:
            raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")

        usuario_encontrado = df[df["senha"] == data.senha]

        if usuario_encontrado.empty:
            raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")


        id = int(usuario_encontrado.iloc[0]['id'])
        nome = usuario_encontrado.iloc[0]['nome']
        senha = usuario_encontrado.iloc[0]["senha"]

        

        return {"success": True, "id": id, "nome": nome, "senha": senha }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Erro inesperado no login: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")
    finally:
        if conn:
            conn.close()


# ------------------------------------------------------------------------------------------

class Add_user(BaseModel):
    usuario: str
    password: str
    email: str
    cpf: str


@app.post("/add_piscineiro")
def inserir_usuario(mov: Add_user):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            query = """
                INSERT INTO tb_piscineiro (usuario, password, email, status, cpf, data_cad)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (mov.usuario, mov.password, mov.email, 1, mov.cpf, date.today()) )
            conn.commit()
        return {"success": True, "message": "Piscineiro cadastrado com sucesso"}
    except Exception as e:
        print("Erro:", e)
        raise HTTPException(status_code=500, detail="Erro ao inserir Piscineiro")
    finally:
        if conn:
            conn.close()


# ------------------------------------------------------------------------------------------


@app.get("/atendimentos/{id_user}")
def get_movimentacao(id_user: int):
    conn = None
    try:
        conn = get_connection()
        
        query = """
                SELECT 
                    id,
                    data,
                    descricao,
                    categoria,
                    tipo,
                    status,
                    valor,
                    id_user,
                    EXTRACT(DAY FROM data) AS dia,
                    EXTRACT(MONTH FROM data) AS mes,
                    EXTRACT(YEAR FROM data) AS ano
                FROM 
                    u771906953_financas.tb_mov
                WHERE 
                    id_user = %s;
                """

        df = pd.read_sql(query, conn, params=[id_user])
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao acessar o banco de dados.")
    finally:
        if conn:
            conn.close()
    return df.to_dict(orient="records")


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


class Categoria(BaseModel):
    categoria: str
    tipo: str
    id_user: int

@app.post("/add_descricao")
def inserir_categoria(cat: Categoria):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            query = """
                INSERT INTO tb_descricao (categoria, tipo, id_user)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (cat.categoria, cat.tipo, cat.id_user))
            conn.commit()
        return {"success": True, "message": "Categoria inserida com sucesso"}
    except Exception as e:
        print("Erro ao inserir categoria:", e)
        raise HTTPException(status_code=500, detail="Erro ao inserir categoria")
    finally:
        if conn:
            conn.close()
 
# ------------------------------------------------------------------------------------------


class UpdateStatusRequest(BaseModel):
    status: str

@app.put("/update-status/{id}")
def update_status(id: int, status_data: UpdateStatusRequest):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
    
            query = "UPDATE tb_mov SET status = %s WHERE id = %s"
            cursor.execute(query, (status_data.status, id))
            conn.commit()

            if cursor.rowcount == 0:
                return {"success": False, "message": "Movimentação não encontrada."}

        return {"success": True, "message": "Status atualizado com sucesso."}
    except Exception as e:
        print("Erro ao atualizar status:", e)
        raise HTTPException(status_code=500, detail="Erro ao atualizar status.")
    finally:
        if conn:
            conn.close()
            

# ------------------------------------------------------------------------------------------


@app.delete("/delete-mov/{id}")
def delete_movimentacao(id: int):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            query = "DELETE FROM tb_mov WHERE id = %s"
            cursor.execute(query, (id,))
            conn.commit()

            if cursor.rowcount == 0:
                return {"success": False, "message": "Movimentação não encontrada."}

        return {"success": True, "message": "Movimentação deletada com sucesso."}
    except Exception as e:
        print("Erro ao deletar movimentação:", e)
        raise HTTPException(status_code=500, detail="Erro ao deletar movimentação.")
    finally:
        if conn:
            conn.close()

# ------------------------------------------------------------------------------------------

@app.delete("/delete_descricao/{id}")
def delete_categoria(id: int):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            query = "DELETE FROM tb_descricao WHERE id_desc = %s"
            cursor.execute(query, (id,))
            conn.commit()

            if cursor.rowcount == 0:
                return {"success": False, "message": "Categoria não encontrada."}

        return {"success": True, "message": "Categoria deletada com sucesso."}
    except Exception as e:
        print("Erro ao deletar categoria:", e)
        raise HTTPException(status_code=500, detail="Erro ao deletar categoria.")
    finally:
        if conn:
            conn.close()

# --------------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------------

    
# uvicorn main:app --reload

# uvicorn main:app --host 0.0.0.0 --port 10000


