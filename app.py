import sqlite3
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from base62 import codificar  
import os

app = Flask(__name__)
CORS(app)  


def conectar_banco():
    return sqlite3.connect('banco.db')

def inicializar_banco():
    conexao = sqlite3.connect('banco.db')
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            long_url TEXT NOT NULL,
            short_code TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conexao.commit()
    conexao.close()

    print("Banco inicializado com sucesso.")

inicializar_banco()

@app.route("/")
def home():
    return "API funcionando!"

@app.route("/health")
def health():
    return {
        "status": "ok"
    }, 200

# POST 
@app.route('/api/encurtar', methods=['POST'])
def criar_link():
    dados = request.get_json()

    if not dados or 'long_url' not in dados:
        return jsonify({"erro": "Você precisa enviar uma 'long_url' no JSON!"}), 400

    url_original = dados['long_url'].strip()

    if not url_original.startswith(('http://', 'https://')):
        url_original = 'http://' + url_original

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # Salva a URL e devolve o ID gerado
        cursor.execute(
            "INSERT INTO urls (long_url) VALUES (?);",
            (url_original,)
        )

        id_gerado = cursor.lastrowid

        # Chama a função de codificação
        codigo_curto = codificar(id_gerado)

        # Atualiza a linha salvando o código base62
        cursor.execute("UPDATE urls SET short_code = ? WHERE id = ?;", (codigo_curto, id_gerado))
        conexao.commit()

        # Devolve para o front
        base_url = request.host_url.rstrip('/')

        return jsonify({
            "mensagem": "Encurtado com sucesso!",
            "short_code": codigo_curto,
            "url_completa": f"{base_url}/{codigo_curto}"
        }), 201

    except Exception as e:
        conexao.rollback()
        return jsonify({"erro": f"Erro interno no banco: {str(e)}"}), 500
    finally:
        conexao.close()


# GET
@app.route('/<short_code>', methods=['GET'])
def redirecionar(short_code):
    conexao = conectar_banco()
    cursor = conexao.cursor()

    # Query para buscar o link original
    cursor.execute("SELECT long_url FROM urls WHERE short_code = ?;", (short_code,))
    resultado = cursor.fetchone()
    conexao.close()

    if resultado:
        url_destino = resultado[0]
        return redirect(url_destino, code=302)  
    else:
        return jsonify({"erro": "Este código de link não existe!"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)