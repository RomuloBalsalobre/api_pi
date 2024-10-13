from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from unidecode import unidecode
import mysql.connector

app = Flask(__name__)
CORS(app)  # Permite receber requisição externa

# Função para conectar ao banco de dados MySQL
def get_db_connection():
    return mysql.connector.connect(
        host='M4h0.mysql.pythonanywhere-services.com',
        user='M4h0',
        password='*s',
        database='M4h0$reports'
    )

# GRava no DB
@app.route('/incidente', methods=['POST'])
def reportincident():
    data = request.json
    rua = unidecode(data.get('rua').upper())
    bairro = unidecode(data.get('bairro'))
    periodo = data.get('periodo')
    obs = data.get('obs')

    # Validação básica da rua
    if not rua or len(rua) < 3:
        return jsonify({'error': 'Rua inválida. Digite um nome de rua válido.'}), 400

    # API do ViaCEP
    response = requests.get(f'https://viacep.com.br/ws/SP/diadema/{rua}/json/')
    data_cep = response.json()

    if data_cep == []:
        return jsonify({'message': 'Rua ou bairro inválido.'}), 400

    # Valida a Rua
    if not data_cep or 'logradouro' not in data_cep[0] or 'bairro' not in data_cep[0]:
        return jsonify({'error': 'Rua ou bairro inválido.'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO assaltos (rua, bairro, periodo, obs, data) VALUES (%s, %s, %s, %s, NOW())"
        val = (rua.upper(), bairro, periodo, obs)
        cursor.execute(sql, val)
        conn.commit()
        return jsonify({'message': 'Endereço salvo com sucesso!'}), 201
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# Retorna para pagina Consulta
@app.route('/consulta', methods=['GET'])
def consulta():
    bairro = request.args.get('bairro')
    periodo = request.args.get('periodo')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Se tanto bairro quanto periodo forem enviados vazios, faz uma consulta geral
        if not bairro and not periodo:
            query = """
            SELECT rua, bairro, periodo, COUNT(*) as quantidade
            FROM assaltos
            GROUP BY rua, bairro, periodo
            ORDER BY quantidade DESC
            """
            cursor.execute(query)
        elif bairro and periodo:
            query = "SELECT rua, bairro, periodo, COUNT(*) FROM assaltos WHERE bairro = %s AND periodo = %s GROUP BY rua, bairro, periodo"
            cursor.execute(query, (bairro, periodo))
        elif bairro:
            query = "SELECT rua, bairro, periodo, COUNT(*) FROM assaltos WHERE bairro = %s GROUP BY rua, bairro, periodo"
            cursor.execute(query, (bairro,))
        elif periodo:
            query = "SELECT rua, bairro, periodo, COUNT(*) FROM assaltos WHERE periodo = %s GROUP BY rua, bairro, periodo"
            cursor.execute(query, (periodo,))

        dados = cursor.fetchall()
        return jsonify(dados), 200
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

#Atualiza o rodapé da pagina
@app.route('/consulta-dados-gerais', methods=['GET'])
def dados_gerais():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta para contar o total de denúncias
        cursor.execute("SELECT COUNT(*) FROM assaltos")
        total_casos = cursor.fetchone()[0]

        cursor.execute("SELECT MAX(data) FROM assaltos")
        ultima_atualizacao = cursor.fetchone()[0]

        return jsonify({
            'total_casos': total_casos,
            'data_atualizacao': ultima_atualizacao.strftime("%d/%m/%Y %H:%M:%S") if ultima_atualizacao else "N/A"
        }), 200
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)
