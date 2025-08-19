import sqlite3
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, g, send_from_directory
from datetime import datetime
from flask_cors import CORS
import os
import sys

# --- Bloco de Caminhos Corrigido ---
# Determina o caminho base, seja rodando como script ou como executável
if getattr(sys, 'frozen', False):
    # Se estiver rodando como um executável do PyInstaller (MODO PRODUÇÃO)
    # O base_path é uma pasta temporária _MEIPASS onde tudo é extraído
    base_path = sys._MEIPASS
    # Em produção, o frontend (pasta 'dist') é empacotado junto ao executável
    frontend_folder = os.path.join(base_path, 'dist')
    spreadsheet_path = os.path.join(base_path, 'backend', 'Planilha TCU - Auditor - Acompanhamento.xlsx')
else:
    # Se estiver rodando como um script normal (MODO DESENVOLVIMENTO)
    # O base_path é o diretório do script app.py (.../plano-estudos-backend)
    base_path = os.path.dirname(os.path.abspath(__file__))
    

    # Em desenvolvimento, a pasta 'dist' do frontend está em um caminho relativo diferente.
    # A estrutura esperada é:
    # .../
    #    |- plano-estudos-backend/ (onde este script está)
    #    |- plano-estudos-frontend/ (onde está a pasta 'dist' após o build)
    # Portanto, subimos um nível ('..') e entramos na pasta do frontend.
    frontend_folder = os.path.abspath(os.path.join(base_path, '..', 'plano-estudos-frontend', 'dist', 'renderer'))



# --- BLOCO DE DEPURAÇÃO ---
print("--- INICIANDO DEPURAÇÃO DE CAMINHOS ---")
print(f"O script está rodando como executável? {getattr(sys, 'frozen', False)}")
print(f"Caminho Base (base_path) = {base_path}")
print(f"Caminho do Frontend (frontend_folder) = {frontend_folder}")
index_html_path = os.path.join(frontend_folder, 'index.html')
print(f"Caminho esperado para o index.html = {index_html_path}")
print(f"O arquivo index.html existe nesse caminho? {os.path.exists(index_html_path)}")
print("--- FIM DA DEPURAÇÃO ---")
# --- FIM DO BLOCO DE DEPURAÇÃO ---

app = Flask(__name__, static_folder=frontend_folder)
# CORS é útil em desenvolvimento, especialmente se o frontend e backend rodam em portas diferentes
CORS(app, resources={r"/api/*": {"origins": "*"}})

# --- Gerenciamento da Conexão ---
def get_db_connection():
    if getattr(sys, 'frozen', False):
        # Modo produção: tudo na mesma pasta do executável (dist)
        executable_dir = os.path.dirname(sys.executable)  # Pasta do executável (dist)
        db_file = os.path.join(executable_dir, 'data.db')
        
        print(f"🔍 Procurando banco em: {db_file}")
        
        # Se não existir, cria um novo
        if not os.path.exists(db_file):
            print("📝 Criando novo banco de dados...")
            open(db_file, 'w').close()
    else:
        # Modo desenvolvimento
        db_file = os.path.join(base_path, 'data.db')
    
    print(f"🔑 Usando banco em: {db_file}")
    
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"❌ Erro ao conectar com banco: {e}")
        # Tenta criar um novo se falhar
        open(db_file, 'w').close()
        return sqlite3.connect(db_file)

@app.teardown_appcontext
def close_connection(exception):
    conn = getattr(g, '_database', None)
    if conn is not None:
        conn.close()

# --- API Endpoints ---

@app.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    conn = get_db_connection()
    hours_by_discipline = conn.execute("""
        SELECT d.name as discipline_name, SUM(e.total_minutos_estudados) as total_minutes
        FROM evolution e
        JOIN discipline d ON e.discipline_id = d.id
        GROUP BY d.name
    """).fetchall()
    avg_percent_by_discipline = conn.execute("""
        SELECT d.name as discipline_name, e.desempenho_medio
        FROM evolution e
        JOIN discipline d ON e.discipline_id = d.id
    """).fetchall()
    return jsonify({
        "hours_by_discipline": [dict(row) for row in hours_by_discipline],
        "avg_percent_by_discipline": [dict(row) for row in avg_percent_by_discipline],
    })

@app.route('/api/trilhas', methods=['GET'])
def get_all_trilhas():
    conn = get_db_connection()
    trilhas = conn.execute('SELECT * FROM trilha ORDER BY id').fetchall()
    trilhas_list = []
    for trilha in trilhas:
        trilha_dict = dict(trilha)
        pending_tasks = conn.execute(
            "SELECT COUNT(id) as count FROM task WHERE trilha_id = ? AND status = 'Pendente'",
            (trilha_dict['id'],)
        ).fetchone()
        trilha_dict['status'] = 'Concluída' if pending_tasks['count'] == 0 else 'Pendente'
        trilhas_list.append(trilha_dict)
    return jsonify(trilhas_list)

@app.route('/api/trilhas/<int:trilha_id>/tasks', methods=['GET'])
def get_tasks_for_trilha(trilha_id):
    conn = get_db_connection()
    tasks_rows = conn.execute("SELECT * FROM task WHERE trilha_id = ? ORDER BY id ASC", (trilha_id,)).fetchall()
    tasks_list = []
    for row in tasks_rows:
        task_dict = dict(row)
        topics = conn.execute("SELECT t.id, t.name FROM topic t JOIN task_topics tt ON t.id = tt.topic_id WHERE tt.task_id = ?", (task_dict['id'],)).fetchall()
        task_dict['topics'] = [dict(t) for t in topics]
        tasks_list.append(task_dict)
    return jsonify(tasks_list)

@app.route('/api/disciplines', methods=['GET', 'POST'])
def handle_disciplines():
    conn = get_db_connection()
    if request.method == 'GET':
        disciplines = conn.execute('SELECT * FROM discipline ORDER BY name').fetchall()
        return jsonify([dict(d) for d in disciplines])
    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('name'): return jsonify({"error": "O nome é obrigatório"}), 400
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO discipline (name) VALUES (?)", (data['name'],))
            conn.commit()
            new_id = cursor.lastrowid
            new_discipline = conn.execute('SELECT * FROM discipline WHERE id = ?', (new_id,)).fetchone()
            return jsonify(dict(new_discipline)), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": "Disciplina com este nome já existe"}), 409

@app.route('/api/disciplines/<int:discipline_id>', methods=['PUT', 'DELETE'])
def handle_discipline(discipline_id):
    conn = get_db_connection()
    if request.method == 'PUT':
        data = request.get_json()
        if not data or not data.get('name'): return jsonify({"error": "O nome é obrigatório"}), 400
        try:
            conn.execute("UPDATE discipline SET name = ? WHERE id = ?", (data['name'], discipline_id))
            conn.commit()
            updated = conn.execute('SELECT * FROM discipline WHERE id = ?', (discipline_id,)).fetchone()
            return jsonify(dict(updated))
        except sqlite3.IntegrityError:
            return jsonify({"error": "Disciplina com este nome já existe"}), 409
    if request.method == 'DELETE':
        conn.execute('DELETE FROM discipline WHERE id = ?', (discipline_id,))
        conn.commit()
        return jsonify({"message": "Disciplina e todos os dados associados foram deletados"})

@app.route('/api/topics', methods=['GET'])
def get_all_topics():
    conn = get_db_connection()
    topics = conn.execute('SELECT * FROM topic ORDER BY name').fetchall()
    return jsonify([dict(t) for t in topics])

@app.route('/api/disciplines/<int:discipline_id>/topics', methods=['GET', 'POST'])
def handle_topics_by_discipline(discipline_id):
    conn = get_db_connection()
    if request.method == 'GET':
        topics = conn.execute('SELECT * FROM topic WHERE discipline_id = ? ORDER BY name', (discipline_id,)).fetchall()
        return jsonify([dict(t) for t in topics])
    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('name'): return jsonify({"error": "O nome é obrigatório"}), 400
        cursor = conn.cursor()
        cursor.execute("INSERT INTO topic (name, discipline_id) VALUES (?, ?)", (data['name'], discipline_id))
        conn.commit()
        new_id = cursor.lastrowid
        new_topic = conn.execute('SELECT * FROM topic WHERE id = ?', (new_id,)).fetchone()
        return jsonify(dict(new_topic)), 201

@app.route('/api/topics/<int:topic_id>', methods=['PUT', 'DELETE'])
def handle_topic(topic_id):
    conn = get_db_connection()
    if request.method == 'PUT':
        data = request.get_json()
        if not data or not data.get('name') or not data.get('discipline_id'): return jsonify({"error": "Nome e discipline_id são obrigatórios"}), 400
        conn.execute("UPDATE topic SET name = ?, discipline_id = ? WHERE id = ?", (data['name'], data['discipline_id'], topic_id))
        conn.commit()
        updated = conn.execute('SELECT * FROM topic WHERE id = ?', (topic_id,)).fetchone()
        return jsonify(dict(updated))
    if request.method == 'DELETE':
        conn.execute('DELETE FROM topic WHERE id = ?', (topic_id,))
        conn.commit()
        return jsonify({"message": "Tópico deletado"})

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    conn = get_db_connection()
    if request.method == 'GET':
        status = request.args.get('status')
        query = "SELECT * FROM task"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        if status == 'Pendente':
            query += " ORDER BY id ASC"
        else:
            query += " ORDER BY completion_date DESC, id DESC"
        tasks_rows = conn.execute(query, params).fetchall()
        tasks_list = []
        for row in tasks_rows:
            task_dict = dict(row)
            topics = conn.execute("SELECT t.id, t.name FROM topic t JOIN task_topics tt ON t.id = tt.topic_id WHERE tt.task_id = ?", (task_dict['id'],)).fetchall()
            task_dict['topics'] = [dict(t) for t in topics]
            tasks_list.append(task_dict)
        return jsonify(tasks_list)
    if request.method == 'POST':
        data = request.get_json()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO task (title, discipline_id, completion_date, status) VALUES (?, ?, ?, ?)",
                       (data['title'], data['discipline_id'], data.get('completion_date'), data.get('status', 'Pendente')))
        task_id = cursor.lastrowid
        if data.get('topic_ids'):
            for topic_id in data['topic_ids']:
                cursor.execute("INSERT INTO task_topics (task_id, topic_id) VALUES (?, ?)", (task_id, topic_id))
        conn.commit()
        new_task = conn.execute('SELECT * FROM task WHERE id = ?', (task_id,)).fetchone()
        return jsonify(dict(new_task)), 201

@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_task(task_id):
    conn = get_db_connection()
    if request.method == 'GET':
        task = conn.execute('SELECT * FROM task WHERE id = ?', (task_id,)).fetchone()
        if not task: return jsonify({"error": "Tarefa não encontrada"}), 404
        task_dict = dict(task)
        topics = conn.execute("SELECT t.id, t.name FROM topic t JOIN task_topics tt ON t.id = tt.topic_id WHERE tt.task_id = ?", (task_id,)).fetchall()
        task_dict['topics'] = [dict(t) for t in topics]
        return jsonify(task_dict)
    if request.method == 'PUT':
        data = request.get_json()
        cursor = conn.cursor()
        carga_realizada_minutos = data.get('carga_horaria_realizada_minutos')
        
        current_task = conn.execute('SELECT status FROM task WHERE id = ?', (task_id,)).fetchone()
        if data.get('status') == 'Concluída' and current_task and current_task['status'] != 'Concluída':
            sum_result = conn.execute("SELECT SUM(duration_minutes) as total FROM study_session WHERE task_id = ?", (task_id,)).fetchone()
            if sum_result and sum_result['total'] is not None:
                carga_realizada_minutos = sum_result['total']

        cursor.execute("""
            UPDATE task SET title = ?, discipline_id = ?, completion_date = ?, status = ?, carga_horaria_realizada_minutos = ?
            WHERE id = ?
        """, (data['title'], data['discipline_id'], data.get('completion_date'), data.get('status'), carga_realizada_minutos, task_id))
        
        cursor.execute("DELETE FROM task_topics WHERE task_id = ?", (task_id,))
        if data.get('topic_ids'):
            for topic_id in data['topic_ids']:
                cursor.execute("INSERT INTO task_topics (task_id, topic_id) VALUES (?, ?)", (task_id, topic_id))
        
        conn.commit()
        recalculate_evolution(conn)
        
        return handle_task(task_id)

    if request.method == 'DELETE':
        conn.execute('DELETE FROM task WHERE id = ?', (task_id,))
        conn.commit()
        return jsonify({"message": "Tarefa deletada"})

@app.route('/api/sessions/save', methods=['POST'])
def save_session():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO study_session (task_id, start, "end", duration_minutes) VALUES (?, ?, ?, ?)',
                   (data.get('task_id'), data.get('start'), data.get('end'), data.get('duration_minutes')))
    conn.commit()
    recalculate_evolution(conn)
    return jsonify({"message": "Sessão salva com sucesso", "id": cursor.lastrowid}), 201

@app.route('/api/sessions/history', methods=['GET'])
def get_session_history():
    conn = get_db_connection()
    history = conn.execute("""
        SELECT s.id, s.start, s."end", s.duration_minutes, t.title as task_title, d.name as discipline_name
        FROM study_session s
        LEFT JOIN task t ON s.task_id = t.id
        LEFT JOIN discipline d ON t.discipline_id = d.id
        WHERE s."end" IS NOT NULL ORDER BY s.start DESC LIMIT 20
    """).fetchall()
    return jsonify([dict(row) for row in history])

@app.route('/api/results', methods=['POST'])
def add_result():
    data = request.get_json()
    conn = get_db_connection()
    percent = (data['correct'] / data['total']) * 100 if data['total'] > 0 else 0
    cursor = conn.cursor()
    cursor.execute('INSERT INTO result (task_id, correct, total, percent, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)',
                   (data.get('task_id'), data['correct'], data['total'], percent))
    conn.commit()
    recalculate_evolution(conn)
    return jsonify({"message": "Resultado salvo", "percent": percent})

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    conn = get_db_connection()
    query = "SELECT r.*, d.name as discipline_name, t.title as task_title FROM review r LEFT JOIN task t ON r.task_id = t.id LEFT JOIN discipline d ON t.discipline_id = d.id"
    params = []
    conditions = []
    if date_from:
        conditions.append("r.scheduled_for >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("r.scheduled_for <= ?")
        params.append(date_to)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY r.scheduled_for"
    reviews = conn.execute(query, params).fetchall()
    return jsonify([dict(row) for row in reviews])

@app.route('/api/evolution', methods=['GET'])
def get_evolution():
    conn = get_db_connection()
    data = conn.execute("SELECT d.name as discipline_name, e.* FROM evolution e JOIN discipline d ON e.discipline_id = d.id").fetchall()
    return jsonify([dict(row) for row in data])

@app.route('/api/sync', methods=['POST'])
def sync_from_spreadsheet():
    try:
        conn = get_db_connection()
        if getattr(sys, 'frozen', False):
            # Modo produção: planilha na mesma pasta do executável
            executable_dir = os.path.dirname(sys.executable)
            excel_file = os.path.join(executable_dir, 'Planilha TCU - Auditor - Acompanhamento.xlsx')
        else:
            # Modo desenvolvimento
            excel_file = os.path.join(base_path, 'Planilha TCU - Auditor - Acompanhamento.xlsx')
        
        print(f"Tentando importar do arquivo: {excel_file}")
        if not os.path.exists(excel_file):
            return jsonify({"error": f"Arquivo não encontrado em: {excel_file}"}), 404
        import_disciplines_from_excel(conn)
        import_ciclo_from_excel(conn)
        recalculate_evolution(conn)
        return jsonify({"message": "Sincronização concluída!"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- Funções Auxiliares ---

def create_tables(conn):
    print("✅ Verificando/Criando tabelas no banco de dados...")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS discipline (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS trilha (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
    cursor.execute("""CREATE TABLE IF NOT EXISTS topic (id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                   discipline_id INTEGER NOT NULL, FOREIGN KEY (discipline_id) REFERENCES discipline (id) ON DELETE CASCADE)""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task (
        id INTEGER PRIMARY KEY, spreadsheet_task_id REAL UNIQUE, title TEXT, discipline_id INTEGER,
        trilha_id INTEGER, completion_date DATE, status TEXT, carga_horaria_planejada_minutos INTEGER,
        carga_horaria_realizada_minutos INTEGER,
        FOREIGN KEY (discipline_id) REFERENCES discipline (id) ON DELETE CASCADE, FOREIGN KEY (trilha_id) REFERENCES trilha (id)
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_topics (
        task_id INTEGER NOT NULL, topic_id INTEGER NOT NULL, PRIMARY KEY (task_id, topic_id),
        FOREIGN KEY (task_id) REFERENCES task (id) ON DELETE CASCADE, FOREIGN KEY (topic_id) REFERENCES topic (id) ON DELETE CASCADE
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS study_session (id INTEGER PRIMARY KEY, task_id INTEGER,
                   start DATETIME, "end" DATETIME, duration_minutes INTEGER, FOREIGN KEY (task_id) REFERENCES task (id) ON DELETE CASCADE)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS result (id INTEGER PRIMARY KEY, task_id INTEGER, correct INTEGER, 
                   total INTEGER, percent REAL, created_at DATETIME NOT NULL, FOREIGN KEY (task_id) REFERENCES task (id) ON DELETE CASCADE)""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evolution (
        id INTEGER PRIMARY KEY, discipline_id INTEGER NOT NULL, qtd_tarefas INTEGER,
        qtd_exercicios_feitos INTEGER, total_acertos INTEGER, desempenho_medio REAL,
        total_minutos_estudados INTEGER,
        FOREIGN KEY (discipline_id) REFERENCES discipline (id) ON DELETE CASCADE
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS review (
        id INTEGER PRIMARY KEY, task_id INTEGER, discipline_id INTEGER, topic_id INTEGER, scheduled_for DATE NOT NULL,
        status VARCHAR, reason VARCHAR, 
        FOREIGN KEY(task_id) REFERENCES task(id) ON DELETE CASCADE,
        FOREIGN KEY(discipline_id) REFERENCES discipline(id) ON DELETE CASCADE,
        FOREIGN KEY(topic_id) REFERENCES topic(id) ON DELETE CASCADE
    )""")
    conn.commit()

def convert_time_to_minutes(time_obj):
    if pd.isna(time_obj): return 0
    if isinstance(time_obj, str):
        try:
            h, m = map(int, time_obj.split(':')); return h * 60 + m
        except: return 0
    elif hasattr(time_obj, 'hour'): return time_obj.hour * 60 + time_obj.minute
    return 0

def import_disciplines_from_excel(conn):
    excel_file = os.path.join(base_path, 'Planilha TCU - Auditor - Acompanhamento.xlsx')
    df = pd.read_excel(excel_file, sheet_name='CICLO', header=2, usecols=['DISCIPLINA'])
    disciplinas = df['DISCIPLINA'].dropna().unique()
    cursor = conn.cursor()
    for d in disciplinas: cursor.execute("INSERT OR IGNORE INTO discipline (name) VALUES (?)", (d,))
    conn.commit()

def import_ciclo_from_excel(conn):
    excel_file = os.path.join(base_path, 'Planilha TCU - Auditor - Acompanhamento.xlsx')
    df = pd.read_excel(excel_file, sheet_name='CICLO', header=2)
    df.columns = [c.strip() for c in df.columns]
    cursor = conn.cursor()
    added = 0
    for i, row in df.iterrows():
        task_id_raw = row.get('TAREFA')
        if pd.isna(task_id_raw): continue
        try: task_id_sheet = float(task_id_raw)
        except: continue
        task_date_str = row.get('DATA')
        status = 'Pendente'
        completion_date = None
        if pd.notna(task_date_str):
            status = 'Concluída'
            completion_date = pd.to_datetime(task_date_str, errors='coerce').strftime('%Y-%m-%d')
        trilha_name = row.get('TRILHA'); trilha_id = None
        if pd.notna(trilha_name):
            cursor.execute("INSERT OR IGNORE INTO trilha (name) VALUES (?)", (str(trilha_name),))
            trilha_id = cursor.execute("SELECT id FROM trilha WHERE name = ?", (str(trilha_name),)).fetchone()[0]
        disc_name = row.get('DISCIPLINA'); disc_id = None
        if pd.notna(disc_name):
            disc_id_res = cursor.execute("SELECT id FROM discipline WHERE name = ?", (disc_name,)).fetchone()
            if not disc_id_res: continue
            disc_id = disc_id_res[0]
        else: continue
        ch_efetiva_min = convert_time_to_minutes(row.get('CH (EFETIVA)'))
        cursor.execute("""INSERT OR IGNORE INTO task (spreadsheet_task_id, title, discipline_id, trilha_id, completion_date, 
                          carga_horaria_planejada_minutos, carga_horaria_realizada_minutos, status)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                       (task_id_sheet, row.get('TAREFAS'), disc_id, trilha_id, completion_date, 
                        convert_time_to_minutes(row.get('CH')), ch_efetiva_min, status))
        if cursor.rowcount > 0:
            added += 1
            task_id_db = cursor.lastrowid
            q_total, q_correct = row.get('TOTAL QUESTÕES', 0), row.get('TOTAL ACERTOS', 0)
            if pd.notna(q_total) and q_total > 0:
                percent = (q_correct / q_total) * 100 if q_total > 0 else 0
                cursor.execute("INSERT INTO result (task_id, correct, total, percent, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                               (task_id_db, q_correct, q_total, percent))
    conn.commit()
    print(f"✔️ {added} novas tarefas adicionadas.")

def recalculate_evolution(conn):
    print("⏳ Iniciando recálculo da tabela de evolução...")
    tasks_results_query = "SELECT t.discipline_id, d.name as discipline_name, r.total, r.correct FROM task t JOIN discipline d ON t.discipline_id = d.id LEFT JOIN result r ON t.id = r.task_id"
    df_tasks = pd.read_sql_query(tasks_results_query, conn)
    study_time_query = """
        SELECT discipline_id, SUM(total_minutes) as total_minutos_estudados
        FROM (
            SELECT discipline_id, carga_horaria_realizada_minutos as total_minutes FROM task WHERE carga_horaria_realizada_minutos IS NOT NULL
            UNION ALL
            SELECT t.discipline_id, s.duration_minutes as total_minutes FROM study_session s JOIN task t ON s.task_id = t.id WHERE s.duration_minutes IS NOT NULL
        )
        GROUP BY discipline_id
    """
    df_study_time = pd.read_sql_query(study_time_query, conn)
    if df_tasks.empty:
        print("⚠️ Não há dados de tarefas para calcular a evolução.")
        return
    df_tasks.fillna(0, inplace=True)
    evo_data = df_tasks.groupby(['discipline_id', 'discipline_name']).agg(
        qtd_tarefas=('discipline_id', 'size'), qtd_exercicios_feitos=('total', 'sum'), total_acertos=('correct', 'sum')).reset_index()
    evo_data['desempenho_medio'] = np.where(evo_data['qtd_exercicios_feitos'] > 0, (evo_data['total_acertos'] / evo_data['qtd_exercicios_feitos']) * 100, 0)
    if not df_study_time.empty:
        evo_data = pd.merge(evo_data, df_study_time, on='discipline_id', how='left')
    else:
        evo_data['total_minutos_estudados'] = 0
    evo_data.fillna(0, inplace=True)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evolution")
    for i, row in evo_data.iterrows():
        cursor.execute("""
        INSERT INTO evolution (discipline_id, qtd_tarefas, qtd_exercicios_feitos, total_acertos, desempenho_medio, total_minutos_estudados)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (row['discipline_id'], int(row['qtd_tarefas']), int(row['qtd_exercicios_feitos']), int(row['total_acertos']), row['desempenho_medio'], int(row['total_minutos_estudados'])))
    conn.commit()
    print("✔️ Tabela de evolução atualizada.")

# --- Servindo o Frontend ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        # Se o caminho não for encontrado, ou for a raiz, sirva o index.html
        # Isso é crucial para que o roteamento do React (React Router) funcione
        return send_from_directory(app.static_folder, 'renderer/index.html')

# --- Inicialização ---
with app.app_context():
    create_tables(get_db_connection())

if __name__ == '__main__':
    print("✅✅✅✅ Backend Flask INICIADO com sucesso! ✅✅✅✅")
    # Garante que o servidor Flask rode na porta 5000, como esperado pelo script 'electron:dev'
    app.run(debug=True, port=5000)
