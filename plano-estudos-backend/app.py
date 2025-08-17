import sqlite3
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, g
from datetime import datetime
from flask_cors import CORS

# --- Configuração ---
DB_FILE = 'data.db'
EXCEL_FILE = 'Planilha TCU - Auditor - Acompanhamento.xlsx'
app = Flask(__name__)
CORS(app)

# --- Gerenciamento da Conexão com o Banco de Dados ---
def get_db_connection():
    conn = getattr(g, '_database', None)
    if conn is None:
        conn = g._database = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
    return conn

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
        SELECT d.name as discipline_name, SUM(s.duration_minutes) as total_minutes
        FROM study_session s
        JOIN task t ON s.task_id = t.id
        JOIN discipline d ON t.discipline_id = d.id
        WHERE s.duration_minutes IS NOT NULL
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

# --- NOVOS ENDPOINTS PARA AS TRILHAS ---

@app.route('/api/trilhas', methods=['GET'])
def get_all_trilhas():
    """Busca todas as trilhas e calcula o status de conclusão de cada uma."""
    conn = get_db_connection()
    trilhas = conn.execute('SELECT * FROM trilha ORDER BY id').fetchall()
    trilhas_list = []
    for trilha in trilhas:
        trilha_dict = dict(trilha)
        # Verifica se ainda existem tarefas pendentes para esta trilha
        pending_tasks = conn.execute(
            "SELECT COUNT(id) as count FROM task WHERE trilha_id = ? AND status = 'Pendente'",
            (trilha_dict['id'],)
        ).fetchone()
        
        trilha_dict['status'] = 'Concluída' if pending_tasks['count'] == 0 else 'Pendente'
        trilhas_list.append(trilha_dict)
        
    return jsonify(trilhas_list)

@app.route('/api/trilhas/<int:trilha_id>/tasks', methods=['GET'])
def get_tasks_for_trilha(trilha_id):
    """Busca todas as tarefas de uma trilha específica."""
    conn = get_db_connection()
    # Usa a função já existente de buscar tarefas, mas filtrada pela trilha
    tasks_rows = conn.execute("SELECT * FROM task WHERE trilha_id = ? ORDER BY id ASC", (trilha_id,)).fetchall()
    tasks_list = []
    for row in tasks_rows:
        task_dict = dict(row)
        topics = conn.execute("SELECT t.id, t.name FROM topic t JOIN task_topics tt ON t.id = tt.topic_id WHERE tt.task_id = ?", (task_dict['id'],)).fetchall()
        task_dict['topics'] = [dict(t) for t in topics]
        tasks_list.append(task_dict)
    return jsonify(tasks_list)

# --- CRUD de Disciplinas ---
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

# --- CRUD de Tópicos ---
@app.route('/api/disciplines/<int:discipline_id>/topics', methods=['GET', 'POST'])
def handle_topics(discipline_id):
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

# --- CRUD de Tarefas ---
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
        
        # --- LÓGICA DE ORDENAÇÃO CORRIGIDA ---
        if status == 'Pendente':
            # Se pedir tarefas pendentes, ordena em ordem crescente pelo ID
            query += " ORDER BY id ASC"
        else:
            # Para outros casos (Concluídas, etc.), mantém a ordem decrescente (mais recentes primeiro)
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

# Em app.py, substitua toda a função handle_task por esta:

@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_task(task_id):
    conn = get_db_connection()
    
    # Lógica para GET (buscar uma tarefa)
    if request.method == 'GET':
        task = conn.execute('SELECT * FROM task WHERE id = ?', (task_id,)).fetchone()
        if not task:
            return jsonify({"error": "Tarefa não encontrada"}), 404
        
        task_dict = dict(task)
        topics = conn.execute("SELECT t.id, t.name FROM topic t JOIN task_topics tt ON t.id = tt.topic_id WHERE tt.task_id = ?", (task_id,)).fetchall()
        task_dict['topics'] = [dict(t) for t in topics]
        return jsonify(task_dict)

    # Lógica para PUT (atualizar uma tarefa)
    if request.method == 'PUT':
        data = request.get_json()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE task SET title = ?, discipline_id = ?, completion_date = ?, status = ? WHERE id = ?",
                       (data['title'], data['discipline_id'], data.get('completion_date'), data.get('status'), task_id))
        
        cursor.execute("DELETE FROM task_topics WHERE task_id = ?", (task_id,))
        if data.get('topic_ids'):
            for topic_id in data['topic_ids']:
                cursor.execute("INSERT INTO task_topics (task_id, topic_id) VALUES (?, ?)", (task_id, topic_id))
        
        conn.commit()
        
        # --- CORREÇÃO APLICADA AQUI ---
        # Em vez de chamar a função novamente, buscamos os dados atualizados e retornamos.
        updated_task = conn.execute('SELECT * FROM task WHERE id = ?', (task_id,)).fetchone()
        if not updated_task:
            return jsonify({"error": "Tarefa não encontrada após atualização"}), 404
            
        updated_task_dict = dict(updated_task)
        updated_topics = conn.execute("SELECT t.id, t.name FROM topic t JOIN task_topics tt ON t.id = tt.topic_id WHERE tt.task_id = ?", (task_id,)).fetchall()
        updated_task_dict['topics'] = [dict(t) for t in updated_topics]
        
        return jsonify(updated_task_dict)
        # --- FIM DA CORREÇÃO ---

    # Lógica para DELETE (deletar uma tarefa)
    if request.method == 'DELETE':
        conn.execute('DELETE FROM task WHERE id = ?', (task_id,))
        conn.commit()
        return jsonify({"message": "Tarefa deletada"})

# --- Endpoints de Sessões, Resultados, Revisões ---

@app.route('/api/sessions/save', methods=['POST'])
def save_session():
    """Recebe uma sessão de estudo completa e a salva no banco."""
    data = request.get_json()
    conn = get_db_connection()
    
    # Pega os dados enviados pelo frontend
    task_id = data.get('task_id')
    start_time_iso = data.get('start')
    end_time_iso = data.get('end')
    duration_minutes = data.get('duration_minutes')

    # Insere a linha completa no banco de dados
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO study_session (task_id, start, "end", duration_minutes) VALUES (?, ?, ?, ?)',
        (task_id, start_time_iso, end_time_iso, duration_minutes)
    )
    conn.commit()
    
    # Opcional: recalcular a evolução após salvar uma sessão de estudo
    recalculate_evolution(conn)
    
    return jsonify({"message": "Sessão salva com sucesso", "id": cursor.lastrowid}), 201

@app.route('/api/sessions/history', methods=['GET'])
def get_session_history():
    """Busca as últimas 20 sessões de estudo salvas."""
    conn = get_db_connection()
    history = conn.execute("""
        SELECT 
            s.id,
            s.start,
            s."end",
            s.duration_minutes,
            t.title as task_title,
            d.name as discipline_name
        FROM study_session s
        LEFT JOIN task t ON s.task_id = t.id
        LEFT JOIN discipline d ON t.discipline_id = d.id
        WHERE s."end" IS NOT NULL
        ORDER BY s.start DESC
        LIMIT 20
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
    
    # ADIÇÃO IMPORTANTE: Recalcula a evolução logo após salvar um resultado
    recalculate_evolution(conn)
    
    return jsonify({"message": "Resultado salvo", "percent": percent})

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    conn = get_db_connection()
    query = "SELECT r.*, d.name as discipline_name, t.title as task_title FROM review r JOIN task t ON r.task_id = t.id JOIN discipline d ON t.discipline_id = d.id"
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

# --- Endpoints de Sincronização e Evolução ---
@app.route('/api/evolution', methods=['GET'])
def get_evolution():
    conn = get_db_connection()
    data = conn.execute("SELECT d.name as discipline_name, e.* FROM evolution e JOIN discipline d ON e.discipline_id = d.id").fetchall()
    return jsonify([dict(row) for row in data])

@app.route('/api/sync', methods=['POST'])
def sync_from_spreadsheet():
    try:
        conn = get_db_connection()
        import_disciplines_from_excel(conn)
        import_ciclo_from_excel(conn)
        recalculate_evolution(conn)
        return jsonify({"message": "Sincronização concluída!"})
    except Exception as e: return jsonify({"error": str(e)}), 500

# --- Funções Auxiliares (Lógica de Banco e Importação) ---

def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS discipline (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS trilha (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
    cursor.execute("""CREATE TABLE IF NOT EXISTS topic (id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                   discipline_id INTEGER NOT NULL, FOREIGN KEY (discipline_id) REFERENCES discipline (id) ON DELETE CASCADE)""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task (
        id INTEGER PRIMARY KEY, spreadsheet_task_id REAL UNIQUE, title TEXT, discipline_id INTEGER,
        trilha_id INTEGER, completion_date DATE, status TEXT, carga_horaria_planejada_minutos INTEGER,
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
        id INTEGER PRIMARY KEY,
        discipline_id INTEGER NOT NULL,
        qtd_tarefas INTEGER,
        qtd_exercicios_feitos INTEGER,
        total_acertos INTEGER,
        desempenho_medio REAL,
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
    df = pd.read_excel(EXCEL_FILE, sheet_name='CICLO', header=2, usecols=['DISCIPLINA'])
    disciplinas = df['DISCIPLINA'].dropna().unique()
    cursor = conn.cursor()
    for d in disciplinas: cursor.execute("INSERT OR IGNORE INTO discipline (name) VALUES (?)", (d,))
    conn.commit()

def import_ciclo_from_excel(conn):
    df = pd.read_excel(EXCEL_FILE, sheet_name='CICLO', header=2)
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
        
        cursor.execute("""INSERT OR IGNORE INTO task (spreadsheet_task_id, title, discipline_id, trilha_id, completion_date, carga_horaria_planejada_minutos, status)
                          VALUES (?, ?, ?, ?, ?, ?, ?)""",
                       (task_id_sheet, row.get('TAREFAS'), disc_id, trilha_id, completion_date, convert_time_to_minutes(row.get('CH')), status))
        
        if cursor.rowcount > 0:
            added += 1
            task_id_db = cursor.lastrowid
            ch_eff = convert_time_to_minutes(row.get('CH (EFETIVA)'))
            if ch_eff > 0: cursor.execute("INSERT INTO study_session (task_id, duration_minutes, start) VALUES (?, ?, ?)", (task_id_db, ch_eff, datetime.now()))
            
            q_total, q_correct = row.get('TOTAL QUESTÕES', 0), row.get('TOTAL ACERTOS', 0)
            if pd.notna(q_total) and q_total > 0:
                percent = (q_correct / q_total) * 100 if q_total > 0 else 0
                cursor.execute("INSERT INTO result (task_id, correct, total, percent, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                               (task_id_db, q_correct, q_total, percent))
    conn.commit()
    print(f"✔️ {added} novas tarefas adicionadas.")


def recalculate_evolution(conn):
    tasks_results_query = "SELECT t.discipline_id, d.name as discipline_name, r.total, r.correct FROM task t JOIN discipline d ON t.discipline_id = d.id LEFT JOIN result r ON t.id = r.task_id"
    df_tasks = pd.read_sql_query(tasks_results_query, conn)
    study_session_query = "SELECT t.discipline_id, s.duration_minutes FROM study_session s JOIN task t ON s.task_id = t.id"
    df_sessions = pd.read_sql_query(study_session_query, conn)
    if df_tasks.empty:
        print("⚠️ Não há dados de tarefas para calcular a evolução.")
        return
    df_tasks.fillna(0, inplace=True)
    evo_data = df_tasks.groupby(['discipline_id', 'discipline_name']).agg(
        qtd_tarefas=('discipline_id', 'size'), qtd_exercicios_feitos=('total', 'sum'), total_acertos=('correct', 'sum')).reset_index()
    evo_data['desempenho_medio'] = np.where(evo_data['qtd_exercicios_feitos'] > 0, (evo_data['total_acertos'] / evo_data['qtd_exercicios_feitos']) * 100, 0)
    if not df_sessions.empty:
        session_data = df_sessions.groupby('discipline_id').agg(total_minutos_estudados=('duration_minutes', 'sum')).reset_index()
        evo_data = pd.merge(evo_data, session_data, on='discipline_id', how='left')
    else:
        evo_data['total_minutos_estudados'] = 0
    evo_data.fillna(0, inplace=True)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evolution")
    for i, row in evo_data.iterrows():
        cursor.execute("INSERT INTO evolution (discipline_id, qtd_tarefas, qtd_exercicios_feitos, total_acertos, desempenho_medio, total_minutos_estudados) VALUES (?, ?, ?, ?, ?, ?)",
                       (row['discipline_id'], int(row['qtd_tarefas']), int(row['qtd_exercicios_feitos']), int(row['total_acertos']), row['desempenho_medio'], int(row['total_minutos_estudados'])))
    conn.commit()
    print("✔️ Tabela de evolução atualizada.")


# --- Inicialização ---
with app.app_context():
    create_tables(get_db_connection())

if __name__ == '__main__':
    app.run(debug=True, port=5000)