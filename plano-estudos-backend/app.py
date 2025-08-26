import sqlite3
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, g, send_from_directory
from datetime import datetime
from flask_cors import CORS
import os
import sys
import io
import json

# --- Bloco de Caminhos Corrigido ---
# Determina o caminho base, seja rodando como script ou como executável
if getattr(sys, 'frozen', False):
    # Se estiver rodando como um executável do PyInstaller (MODO PRODUÇÃO)
    # O base_path é uma pasta temporária _MEIPASS onde tudo é extraído
    base_path = sys._MEIPASS
    # Em produção, o frontend (pasta 'dist') é empacotado junto ao executável
    frontend_folder = os.path.join(base_path, 'dist')
    executable_dir = os.path.dirname(sys.executable)  # Pasta do executável (dist)
    excel_file = os.path.join(executable_dir, 'Planilha TCU - Auditor - Acompanhamento.xlsx')
else:
    # Se estiver rodando como um script normal (MODO DESENVOLVIMENTO)
    # O base_path é o diretório do script app.py (.../plano-estudos-backend)
    base_path = os.path.dirname(os.path.abspath(__file__))
    # Modo desenvolvimento
    excel_file = os.path.join(base_path, 'Planilha TCU - Auditor - Acompanhamento.xlsx')

    # Em desenvolvimento, a pasta 'dist' do frontend está em um caminho relativo diferente.
    # A estrutura esperada é:
    # .../
    #    |- plano-estudos-backend/ (onde este script está)
    #    |- plano-estudos-frontend/ (onde está a pasta 'dist' após o build)
    # Portanto, subimos um nível ('..') e entramos na pasta do frontend.
    frontend_folder = os.path.abspath(os.path.join(base_path, '..', 'plano-estudos-frontend', 'dist', 'renderer'))



# --- BLOCO DE DEPURAÇÃO ---
print("=== INICIANDO DEPURAÇÃO DE CAMINHOS ===")
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
CORS(app, resources={r"/api/*": {"origins": "file://*"}})

# --- Gerenciamento da Conexão ---
def get_db_connection():
    if getattr(sys, 'frozen', False):
        # Modo produção: tudo na mesma pasta do executável (dist)
        executable_dir = os.path.dirname(sys.executable)  # Pasta do executável (dist)
        db_file = os.path.join(executable_dir, 'data.db')
        
        # Se não existir, cria um novo
        if not os.path.exists(db_file):
            open(db_file, 'w').close()
    else:
        # Modo desenvolvimento
        db_file = os.path.join(base_path, 'data.db')
    
    
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar com banco: {e}")
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
    
    # Inserir sessão
    cursor.execute('INSERT INTO study_session (task_id, start, "end", duration_minutes) VALUES (?, ?, ?, ?)',
                   (data.get('task_id'), data.get('start'), data.get('end'), data.get('duration_minutes')))
    session_id = cursor.lastrowid
    
    # Buscar informações da tarefa e disciplina
    task_info = conn.execute("""
        SELECT t.id, t.title, d.id as discipline_id, d.name as discipline_name
        FROM task t 
        JOIN discipline d ON t.discipline_id = d.id 
        WHERE t.id = ?
    """, (data.get('task_id'),)).fetchone()
    
    if task_info:
        task_dict = dict(task_info)
        duration_hours = data.get('duration_minutes') / 60.0
        
        # Milestones de tempo de estudo (horas) por disciplina
        study_time = conn.execute("""
            SELECT SUM(s.duration_minutes) / 60.0 as total_hours
            FROM study_session s
            JOIN task t ON s.task_id = t.id
            WHERE t.discipline_id = ?
        """, (task_dict['discipline_id'],)).fetchone()['total_hours'] or 0
        
        hour_milestones = [5, 10, 25, 50, 100]
        for milestone in hour_milestones:
            if study_time >= milestone:
                # Verifica se já existe notificação para este milestone
                notification_exists = conn.execute("""
                    SELECT 1 FROM notification 
                    WHERE type = 'achievement' 
                    AND title LIKE ? 
                    AND related_id = ?
                """, (f'%{milestone} horas%', task_dict['discipline_id'])).fetchone()
                
                if not notification_exists:
                    create_achievement_notification(
                        conn,
                        f"{milestone} horas de estudo em {task_dict['discipline_name']}! ⏰",
                        f"Você já dedicou {milestone} horas ao estudo desta disciplina. Continue assim!",
                        task_dict['discipline_id'],
                        'discipline'
                    )
        
        # Sessão longa (mais de 2 horas)
        if duration_hours >= 2:
            create_achievement_notification(
                conn,
                "Sessão produtiva! 💪",
                f"Você estudou {task_dict['discipline_name']} por {duration_hours:.1f} horas.",
                session_id,
                'study_session'
            )
    
    conn.commit()
    recalculate_evolution(conn)
    check_goals_status(conn)  # Verifica se alguma meta foi alcançada
    
    return jsonify({
        "message": "Sessão salva com sucesso", 
        "id": session_id
    }), 201

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

@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
def delete_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Deleta a sessão
    cursor.execute('DELETE FROM study_session WHERE id = ?', (session_id,))
    conn.commit()
    
    # Recalcula evolução após excluir a sessão
    recalculate_evolution(conn)
    
    return jsonify({"message": "Sessão excluída com sucesso"})

@app.route('/api/results', methods=['POST'])
def add_result():
    data = request.get_json()
    conn = get_db_connection()
    percent = (data['correct'] / data['total']) * 100 if data['total'] > 0 else 0
    cursor = conn.cursor()
    
    # Inserir resultado
    cursor.execute('INSERT INTO result (task_id, correct, total, percent, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)',
                   (data.get('task_id'), data['correct'], data['total'], percent))
    
    # Buscar informações da tarefa
    task_info = conn.execute("""
        SELECT t.id, t.title, d.id as discipline_id, d.name as discipline_name
        FROM task t 
        JOIN discipline d ON t.discipline_id = d.id 
        WHERE t.id = ?
    """, (data.get('task_id'),)).fetchone()
    
    if task_info:
        task_dict = dict(task_info)
        
        # Cálculo de média recente para a disciplina
        recent_avg = conn.execute("""
            SELECT AVG(r.percent) as avg_performance
            FROM result r
            JOIN task t ON r.task_id = t.id
            WHERE t.discipline_id = ?
            AND r.created_at >= date('now', '-7 days')
        """, (task_dict['discipline_id'],)).fetchone()['avg_performance']
        
        # Notificações baseadas no desempenho
        if percent >= 80:
            create_performance_notification(
                conn,
                f"Excelente resultado em {task_dict['discipline_name']}! 🌟",
                f"Você acertou {percent:.1f}% dos exercícios em {task_dict['title']}.",
                'normal',
                task_dict['discipline_id'],
                'discipline'
            )
        elif percent < 60:
            create_performance_notification(
                conn,
                f"Atenção ao resultado em {task_dict['discipline_name']}",
                f"Você acertou {percent:.1f}% dos exercícios em {task_dict['title']}. Considere revisar o conteúdo.",
                'high',
                task_dict['discipline_id'],
                'discipline'
            )
        
        # Se houve uma melhoria significativa na média
        if recent_avg and recent_avg < 60 and percent >= 80:
            create_achievement_notification(
                conn,
                "Melhoria significativa! 📈",
                f"Seu desempenho em {task_dict['discipline_name']} melhorou muito! Continue assim!"
            )
    
    conn.commit()
    recalculate_evolution(conn)
    check_performance_alerts(conn)
    
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

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    conn = get_db_connection()
    notifications = conn.execute("""
        SELECT * FROM notification
        WHERE read_at IS NULL
        ORDER BY created_at DESC
    """).fetchall()
    return jsonify([dict(row) for row in notifications])

@app.route('/api/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    conn = get_db_connection()
    data = request.get_json()
    notification_ids = data.get('ids', [])
    
    if notification_ids:
        placeholders = ','.join('?' * len(notification_ids))
        conn.execute(
            f"UPDATE notification SET read_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
            notification_ids
        )
        conn.commit()
    
    return jsonify({"message": "Notificações marcadas como lidas"})

@app.route('/api/topics/performance', methods=['GET'])
def get_topics_performance():
    conn = get_db_connection()
    # Busca performance por tópico
    topics_data = conn.execute("""
        WITH TopicResults AS (
            SELECT 
                t.id as topic_id,
                t.name as topic_name,
                t.discipline_id,
                d.name as discipline_name,
                SUM(r.correct) as total_correct,
                SUM(r.total) as total_questions,
                COUNT(DISTINCT tt.task_id) as total_tasks,
                ROUND(AVG(r.percent), 2) as avg_performance
            FROM topic t
            JOIN discipline d ON t.discipline_id = d.id
            LEFT JOIN task_topics tt ON t.id = tt.topic_id
            LEFT JOIN task tk ON tt.task_id = tk.id
            LEFT JOIN result r ON tk.id = r.task_id
            GROUP BY t.id, t.name, t.discipline_id, d.name
        )
        SELECT 
            *,
            CASE 
                WHEN avg_performance >= 80 THEN 'strong'
                WHEN avg_performance >= 60 THEN 'medium'
                ELSE 'weak'
            END as performance_level
        FROM TopicResults
        ORDER BY discipline_name, avg_performance DESC
    """).fetchall()

    # Organizar dados por disciplina
    disciplines_map = {}
    for topic in topics_data:
        topic_dict = dict(topic)
        discipline_id = topic_dict['discipline_id']
        
        if discipline_id not in disciplines_map:
            disciplines_map[discipline_id] = {
                'name': topic_dict['discipline_name'],
                'topics': []
            }
        
        # Adicionar tópico à disciplina
        disciplines_map[discipline_id]['topics'].append({
            'id': topic_dict['topic_id'],
            'name': topic_dict['topic_name'],
            'totalCorrect': topic_dict['total_correct'] or 0,
            'totalQuestions': topic_dict['total_questions'] or 0,
            'totalTasks': topic_dict['total_tasks'] or 0,
            'avgPerformance': topic_dict['avg_performance'] or 0,
            'performanceLevel': topic_dict['performance_level']
        })
    
    # Converter para lista
    result = [
        {
            'discipline_id': k,
            'discipline_name': v['name'],
            'topics': sorted(v['topics'], key=lambda x: x['avgPerformance'], reverse=True)
        }
        for k, v in disciplines_map.items()
    ]
    
    return jsonify(result)

@app.route('/api/goals', methods=['GET', 'POST'])
def handle_goals():
    conn = get_db_connection()
    if request.method == 'GET':
        status = request.args.get('status', 'active')
        goals = conn.execute("""
            SELECT g.*, d.name as discipline_name 
            FROM study_goal g 
            JOIN discipline d ON g.discipline_id = d.id
            WHERE g.status = ?
            ORDER BY g.end_date ASC
        """, (status,)).fetchall()
        return jsonify([dict(row) for row in goals])
    
    if request.method == 'POST':
        data = request.get_json()
        required_fields = ['discipline_id', 'type', 'target_value', 'period', 'start_date', 'end_date']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Todos os campos são obrigatórios"}), 400
        
        # Garante que as datas estejam com o dia correto
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO study_goal (discipline_id, type, target_value, period, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data['discipline_id'],
            data['type'],
            data['target_value'],
            data['period'],
            start_date.isoformat(),  # Usa apenas a data, sem informação de hora
            end_date.isoformat()     # Usa apenas a data, sem informação de hora
        ))
        conn.commit()
        
        new_goal = conn.execute("""
            SELECT g.*, d.name as discipline_name 
            FROM study_goal g 
            JOIN discipline d ON g.discipline_id = d.id
            WHERE g.id = ?
        """, (cursor.lastrowid,)).fetchone()
        
        return jsonify(dict(new_goal)), 201

@app.route('/api/goals/<int:goal_id>', methods=['PUT', 'DELETE'])
def handle_goal(goal_id):
    conn = get_db_connection()
    if request.method == 'PUT':
        data = request.get_json()
        cursor = conn.cursor()
        
        if 'status' in data:
            # Atualização apenas do status
            cursor.execute("""
                UPDATE study_goal 
                SET status = ?
                WHERE id = ?
            """, (data['status'], goal_id))
        else:
            # Garante que as datas estejam em UTC
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
            
            # Atualização completa da meta
            cursor.execute("""
                UPDATE study_goal 
                SET discipline_id = ?, type = ?, target_value = ?, 
                    period = ?, start_date = ?, end_date = ?
                WHERE id = ?
            """, (
                data['discipline_id'], data['type'], data['target_value'],
                data['period'], 
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                goal_id
            ))
        
        conn.commit()
        
        updated_goal = conn.execute("""
            SELECT g.*, d.name as discipline_name 
            FROM study_goal g 
            JOIN discipline d ON g.discipline_id = d.id
            WHERE g.id = ?
        """, (goal_id,)).fetchone()
        return jsonify(dict(updated_goal))
    
    if request.method == 'DELETE':
        conn.execute('DELETE FROM study_goal WHERE id = ?', (goal_id,))
        conn.commit()
        return jsonify({"message": "Meta removida com sucesso"})

@app.route('/api/notifications/check', methods=['POST'])
def check_for_notifications():
    """Endpoint para forçar uma verificação de notificações"""
    check_notifications()
    return jsonify({"message": "Notificações verificadas com sucesso"})

@app.route('/api/goals/progress', methods=['GET'])
def get_goals_progress():
    conn = get_db_connection()
    goals = conn.execute("""
        SELECT g.*, d.name as discipline_name 
        FROM study_goal g 
        JOIN discipline d ON g.discipline_id = d.id
        WHERE g.status = 'active'
    """).fetchall()
    
    progress_data = []
    for goal in goals:
        goal_dict = dict(goal)
        
        if goal['type'] == 'study_time':
            # Calcula progresso do tempo de estudo
            progress = conn.execute("""
                SELECT COALESCE(SUM(duration_minutes), 0) as total_minutes
                FROM study_session s
                JOIN task t ON s.task_id = t.id
                WHERE t.discipline_id = ?
                AND date(s.start) >= ?
                AND date(s.start) <= ?
            """, (goal['discipline_id'], goal['start_date'], goal['end_date'])).fetchone()
            
            goal_dict['current_value'] = progress['total_minutes']
            
        elif goal['type'] == 'performance':
            # Calcula média de desempenho
            progress = conn.execute("""
                SELECT AVG(r.percent) as avg_performance
                FROM result r
                JOIN task t ON r.task_id = t.id
                WHERE t.discipline_id = ?
                AND date(r.created_at) >= ?
                AND date(r.created_at) <= ?
            """, (goal['discipline_id'], goal['start_date'], goal['end_date'])).fetchone()
            
            goal_dict['current_value'] = progress['avg_performance'] or 0
            
        elif goal['type'] == 'exercises_completed':
            # Calcula total de exercícios
            progress = conn.execute("""
                SELECT COALESCE(SUM(r.total), 0) as total_exercises
                FROM result r
                JOIN task t ON r.task_id = t.id
                WHERE t.discipline_id = ?
                AND date(r.created_at) >= ?
                AND date(r.created_at) <= ?
            """, (goal['discipline_id'], goal['start_date'], goal['end_date'])).fetchone()
            
            goal_dict['current_value'] = progress['total_exercises']
        
        goal_dict['progress_percent'] = (goal_dict['current_value'] / goal['target_value']) * 100
        
        # Se a meta foi alcançada, atualiza o status
        if goal_dict['progress_percent'] >= 100 and goal_dict['status'] == 'active':
            conn.execute("UPDATE study_goal SET status = 'completed' WHERE id = ?", (goal_dict['id'],))
            conn.commit()
            
            # Criar notificação de conquista
            create_goal_notification(
                conn,
                f"Meta alcançada em {goal_dict['discipline_name']}! 🎉",
                f"Você alcançou a meta de {goal_dict['target_value']} {goal_dict['type']}!",
                'normal',
                goal_dict['id']
            )
        
        progress_data.append(goal_dict)
    
    return jsonify(progress_data)

@app.route('/api/performance/history', methods=['GET'])
def get_performance_history():
    conn = get_db_connection()
    days = request.args.get('days', default=30, type=int)
    discipline_id = request.args.get('discipline_id', type=int)
    
    query = """
        SELECT 
            d.name as discipline_name,
            ph.*,
            ROUND(CAST(ph.correct_answers AS FLOAT) / NULLIF(ph.exercises_completed, 0) * 100, 2) as accuracy
        FROM performance_history ph
        JOIN discipline d ON ph.discipline_id = d.id
        WHERE ph.date >= date('now', ?)
    """
    params = [f'-{days} days']
    
    if discipline_id:
        query += " AND ph.discipline_id = ?"
        params.append(discipline_id)
    
    query += " ORDER BY ph.date"
    
    data = conn.execute(query, params).fetchall()
    return jsonify([dict(row) for row in data])

@app.route('/api/courses', methods=['GET'])
def get_courses():
    try:
        with open(os.path.join(base_path, 'course_links.json')) as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sync', methods=['POST'])
def sync_from_spreadsheet():
    try:
        conn = get_db_connection()
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
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS discipline (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS trilha (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)")
    cursor.execute("""CREATE TABLE IF NOT EXISTS topic (id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                   discipline_id INTEGER NOT NULL, FOREIGN KEY (discipline_id) REFERENCES discipline (id) ON DELETE CASCADE)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS notification (
        id INTEGER PRIMARY KEY,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        read_at DATETIME,
        priority TEXT DEFAULT 'normal',
        related_id INTEGER,
        related_type TEXT,
        CHECK (type IN ('goal', 'review', 'performance', 'achievement')),
        CHECK (priority IN ('low', 'normal', 'high'))
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS study_goal (
        id INTEGER PRIMARY KEY,
        discipline_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        target_value REAL NOT NULL,
        period TEXT NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (discipline_id) REFERENCES discipline (id) ON DELETE CASCADE,
        CHECK (type IN ('study_time', 'performance', 'exercises_completed')),
        CHECK (period IN ('daily', 'weekly', 'monthly', 'custom')),
        CHECK (status IN ('active', 'completed', 'failed', 'cancelled'))
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS performance_history (
        id INTEGER PRIMARY KEY,
        discipline_id INTEGER NOT NULL,
        date DATE NOT NULL,
        exercises_completed INTEGER DEFAULT 0,
        correct_answers INTEGER DEFAULT 0,
        study_time_minutes INTEGER DEFAULT 0,
        performance_percent REAL DEFAULT 0,
        FOREIGN KEY (discipline_id) REFERENCES discipline (id) ON DELETE CASCADE
    )""")
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
    df = pd.read_excel(excel_file, sheet_name='CICLO', header=2, usecols=['DISCIPLINA'])
    disciplinas = df['DISCIPLINA'].dropna().unique()
    cursor = conn.cursor()
    for d in disciplinas: cursor.execute("INSERT OR IGNORE INTO discipline (name) VALUES (?)", (d,))
    conn.commit()

def import_ciclo_from_excel(conn):
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
    print(f"{added} novas tarefas adicionadas.")

def recalculate_evolution(conn):
    print("Iniciando recálculo da tabela de evolução...")
    
    # Query para resultados diários
    daily_results_query = """
        SELECT 
            t.discipline_id,
            d.name as discipline_name,
            date(r.created_at) as date,
            SUM(r.total) as exercises_completed,
            SUM(r.correct) as correct_answers
        FROM task t 
        JOIN discipline d ON t.discipline_id = d.id 
        JOIN result r ON t.id = r.task_id
        GROUP BY t.discipline_id, date(r.created_at)
    """
    
    # Query para tempo de estudo diário
    daily_study_query = """
        SELECT 
            t.discipline_id,
            date(s.start) as date,
            SUM(s.duration_minutes) as study_time_minutes
        FROM task t 
        JOIN study_session s ON t.id = s.task_id
        GROUP BY t.discipline_id, date(s.start)
    """
    
    # Carregar dados
    df_daily_results = pd.read_sql_query(daily_results_query, conn)
    df_daily_study = pd.read_sql_query(daily_study_query, conn)
    
    # Mesclar dados de resultados e tempo de estudo
    if not df_daily_results.empty:
        # Processar dados diários
        for _, row in df_daily_results.iterrows():
            # Buscar tempo de estudo correspondente
            study_time = 0
            if not df_daily_study.empty:
                matching_study = df_daily_study[
                    (df_daily_study['discipline_id'] == row['discipline_id']) &
                    (df_daily_study['date'] == row['date'])
                ]
                if not matching_study.empty:
                    study_time = matching_study.iloc[0]['study_time_minutes']
            
            # Calcular performance
            performance = (row['correct_answers'] / row['exercises_completed'] * 100) if row['exercises_completed'] > 0 else 0
            
            # Inserir ou atualizar histórico
            conn.execute("""
                INSERT OR REPLACE INTO performance_history 
                (discipline_id, date, exercises_completed, correct_answers, study_time_minutes, performance_percent)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                row['discipline_id'],
                row['date'],
                row['exercises_completed'],
                row['correct_answers'],
                study_time,
                performance
            ))
    
    # Continuar com o cálculo normal de evolução
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
        print("Não há dados de tarefas para calcular a evolução.")
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
    print("Tabela de evolução atualizada COM SUCESSO.")

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

def create_achievement_notification(conn, title, message, related_id=None, related_type=None):
    """Cria uma notificação de conquista"""
    conn.execute("""
        INSERT INTO notification (type, title, message, priority, related_id, related_type)
        VALUES ('achievement', ?, ?, 'normal', ?, ?)
    """, (title, message, related_id, related_type))
    conn.commit()

def create_goal_notification(conn, title, message, priority='normal', related_id=None):
    """Cria uma notificação relacionada a uma meta"""
    conn.execute("""
        INSERT INTO notification (type, title, message, priority, related_id, related_type)
        VALUES ('goal', ?, ?, ?, ?, 'goal')
    """, (title, message, priority, related_id))
    conn.commit()

def create_performance_notification(conn, title, message, priority='normal', related_id=None, related_type=None):
    """Cria uma notificação relacionada ao desempenho"""
    conn.execute("""
        INSERT INTO notification (type, title, message, priority, related_id, related_type)
        VALUES ('performance', ?, ?, ?, ?, ?)
    """, (title, message, priority, related_id, related_type))
    conn.commit()

def check_goals_status(conn):
    """
    Verifica o status das metas e gera notificações relevantes
    - Metas próximas do fim (3 dias)
    - Metas vencidas
    - Metas concluídas
    """
    
    # Buscar metas ativas
    goals = conn.execute("""
        SELECT g.*, d.name as discipline_name 
        FROM study_goal g 
        JOIN discipline d ON g.discipline_id = d.id
        WHERE g.status = 'active'
    """).fetchall()
    
    for goal in goals:
        goal_dict = dict(goal)
        
        # Verificar metas vencidas
        end_date = datetime.strptime(goal_dict['end_date'], '%Y-%m-%d').date()
        today = datetime.now().date()
        
        if end_date < today:
            # Marcar meta como falha
            conn.execute("UPDATE study_goal SET status = 'failed' WHERE id = ?", (goal_dict['id'],))
            
            create_goal_notification(
                conn,
                f"Meta não alcançada em {goal_dict['discipline_name']}",
                f"A meta de {goal_dict['target_value']} {goal_dict['type']} não foi alcançada no prazo.",
                'high',
                goal_dict['id']
            )
            continue
        
        # Verificar metas próximas do fim (3 dias)
        days_remaining = (end_date - today).days
        if days_remaining <= 3:
            # Buscar progresso atual
            if goal_dict['type'] == 'study_time':
                progress = conn.execute("""
                    SELECT COALESCE(SUM(duration_minutes), 0) as total_minutes
                    FROM study_session s
                    JOIN task t ON s.task_id = t.id
                    WHERE t.discipline_id = ?
                    AND date(s.start) >= ?
                    AND date(s.start) <= ?
                """, (goal_dict['discipline_id'], goal_dict['start_date'], goal_dict['end_date'])).fetchone()
                
                current_value = progress['total_minutes']
                
            elif goal_dict['type'] == 'performance':
                progress = conn.execute("""
                    SELECT AVG(r.percent) as avg_performance
                    FROM result r
                    JOIN task t ON r.task_id = t.id
                    WHERE t.discipline_id = ?
                    AND date(r.created_at) >= ?
                    AND date(r.created_at) <= ?
                """, (goal_dict['discipline_id'], goal_dict['start_date'], goal_dict['end_date'])).fetchone()
                
                current_value = progress['avg_performance'] or 0
                
            elif goal_dict['type'] == 'exercises_completed':
                progress = conn.execute("""
                    SELECT COALESCE(SUM(r.total), 0) as total_exercises
                    FROM result r
                    JOIN task t ON r.task_id = t.id
                    WHERE t.discipline_id = ?
                    AND date(r.created_at) >= ?
                    AND date(r.created_at) <= ?
                """, (goal_dict['discipline_id'], goal_dict['start_date'], goal_dict['end_date'])).fetchone()
                
                current_value = progress['total_exercises']
            
            progress_percent = (current_value / goal_dict['target_value']) * 100
            
            # Se meta já foi alcançada
            if progress_percent >= 100:
                conn.execute("UPDATE study_goal SET status = 'completed' WHERE id = ?", (goal_dict['id'],))
                create_goal_notification(
                    conn,
                    f"Meta alcançada em {goal_dict['discipline_name']}! 🎉",
                    f"Você alcançou a meta de {goal_dict['target_value']} {goal_dict['type']}!",
                    'normal',
                    goal_dict['id']
                )
            else:
                remaining = goal_dict['target_value'] - current_value
                create_goal_notification(
                    conn,
                    f"Meta próxima do fim em {goal_dict['discipline_name']}",
                    f"Faltam {remaining:.0f} {goal_dict['type']} e {days_remaining} dias para alcançar sua meta.",
                    'high' if days_remaining <= 1 else 'normal',
                    goal_dict['id']
                )

def check_performance_alerts(conn):
    """
    Gera alertas baseados no desempenho:
    - Queda de desempenho (abaixo de 60%)
    - Melhoria significativa (acima de 80%)
    - Recomendações de revisão para tópicos fracos
    """
    
    # Buscar desempenho médio por disciplina nos últimos 30 dias
    performances = conn.execute("""
        SELECT 
            d.id as discipline_id,
            d.name as discipline_name,
            AVG(r.percent) as avg_performance,
            COUNT(r.id) as total_results
        FROM discipline d
        LEFT JOIN task t ON t.discipline_id = d.id
        LEFT JOIN result r ON r.task_id = t.id
        WHERE r.created_at >= date('now', '-30 days')
        GROUP BY d.id, d.name
        HAVING COUNT(r.id) > 0
    """).fetchall()
    
    for perf in performances:
        perf_dict = dict(perf)
        
        # Alerta de baixo desempenho
        if perf_dict['avg_performance'] < 60:
            create_performance_notification(
                conn,
                f"Atenção ao desempenho em {perf_dict['discipline_name']}",
                f"Seu desempenho médio está em {perf_dict['avg_performance']:.1f}%. Considere revisar o conteúdo.",
                'high',
                perf_dict['discipline_id'],
                'discipline'
            )
        
        # Reconhecimento de alto desempenho
        elif perf_dict['avg_performance'] > 80:
            create_performance_notification(
                conn,
                f"Excelente desempenho em {perf_dict['discipline_name']}! 🌟",
                f"Seu desempenho médio está em {perf_dict['avg_performance']:.1f}%. Continue assim!",
                'normal',
                perf_dict['discipline_id'],
                'discipline'
            )
    
    # Verificar tópicos com baixo desempenho
    weak_topics = conn.execute("""
        WITH TopicPerformance AS (
            SELECT 
                t.id as topic_id,
                t.name as topic_name,
                d.id as discipline_id,
                d.name as discipline_name,
                AVG(r.percent) as avg_performance,
                COUNT(r.id) as total_results
            FROM topic t
            JOIN discipline d ON t.discipline_id = d.id
            JOIN task_topics tt ON t.id = tt.topic_id
            JOIN task tk ON tt.task_id = tk.id
            JOIN result r ON tk.id = r.task_id
            WHERE r.created_at >= date('now', '-30 days')
            GROUP BY t.id, t.name, d.id, d.name
            HAVING COUNT(r.id) >= 3
        )
        SELECT *
        FROM TopicPerformance
        WHERE avg_performance < 60
    """).fetchall()
    
    for topic in weak_topics:
        topic_dict = dict(topic)
        create_performance_notification(
            conn,
            f"Tópico precisa de atenção: {topic_dict['topic_name']}",
            f"Seu desempenho neste tópico está em {topic_dict['avg_performance']:.1f}%. Recomendamos revisar o conteúdo.",
            'high',
            topic_dict['topic_id'],
            'topic'
        )

def monitor_achievements(conn):
    """Monitora e cria notificações para conquistas do usuário"""
    
    # Conquista: Primeira meta concluída
    first_goal = conn.execute("""
        SELECT g.*, d.name as discipline_name
        FROM study_goal g
        JOIN discipline d ON g.discipline_id = d.id
        WHERE g.status = 'completed'
        ORDER BY g.end_date ASC
        LIMIT 1
    """).fetchone()
    
    if first_goal:
        # Verifica se já existe notificação para esta conquista
        notification_exists = conn.execute("""
            SELECT 1 FROM notification 
            WHERE type = 'achievement' 
            AND title LIKE '%Primeira meta%'
            AND related_id = ?
        """, (first_goal['id'],)).fetchone()
        
        if not notification_exists:
            create_achievement_notification(
                conn,
                "Primeira meta concluída! 🎯",
                f"Parabéns! Você completou sua primeira meta em {dict(first_goal)['discipline_name']}.",
                first_goal['id'],
                'goal'
            )
    
    # Conquista: 100 exercícios resolvidos
    exercises_count = conn.execute("""
        SELECT COUNT(*) as total
        FROM result
    """).fetchone()['total']
    
    milestones = [100, 500, 1000, 5000]
    for milestone in milestones:
        if exercises_count >= milestone:
            notification_exists = conn.execute("""
                SELECT 1 FROM notification 
                WHERE type = 'achievement' 
                AND title LIKE ?
            """, (f'%{milestone} exercícios%',)).fetchone()
            
            if not notification_exists:
                create_achievement_notification(
                    conn,
                    f"{milestone} exercícios resolvidos! 📚",
                    "Você está no caminho certo! Continue praticando."
                )
    
    # Conquista: Sequência de alto desempenho (3 resultados seguidos acima de 80%)
    high_performance_streak = conn.execute("""
        WITH RankedResults AS (
            SELECT 
                r.id,
                r.percent,
                ROW_NUMBER() OVER (ORDER BY r.created_at DESC) as recent_rank
            FROM result r
            WHERE r.percent >= 80
            ORDER BY r.created_at DESC
            LIMIT 3
        )
        SELECT COUNT(*) as streak
        FROM RankedResults
    """).fetchone()['streak']
    
    if high_performance_streak >= 3:
        # Verifica se já existe notificação recente (últimos 7 dias) para esta conquista
        notification_exists = conn.execute("""
            SELECT 1 FROM notification 
            WHERE type = 'achievement' 
            AND title LIKE '%Sequência de alto desempenho%'
            AND created_at >= date('now', '-7 days')
        """).fetchone()
        
        if not notification_exists:
            create_achievement_notification(
                conn,
                "Sequência de alto desempenho! 🔥",
                "Você manteve um desempenho acima de 80% nas últimas 3 avaliações!"
            )
    
    # Conquista: 10 horas de estudo
    study_hours = conn.execute("""
        SELECT SUM(duration_minutes) / 60.0 as total_hours
        FROM study_session
    """).fetchone()['total_hours'] or 0
    
    hour_milestones = [10, 50, 100, 500]
    for milestone in hour_milestones:
        if study_hours >= milestone:
            notification_exists = conn.execute("""
                SELECT 1 FROM notification 
                WHERE type = 'achievement' 
                AND title LIKE ?
            """, (f'%{milestone} horas%',)).fetchone()
            
            if not notification_exists:
                create_achievement_notification(
                    conn,
                    f"{milestone} horas de estudo! ⏰",
                    "Seu comprometimento está rendendo frutos. Continue dedicado!"
                )

def check_notifications():
    """Verifica e gera todas as notificações necessárias"""
    conn = get_db_connection()
    check_goals_status(conn)
    check_performance_alerts(conn)
    monitor_achievements(conn)

# --- Inicialização ---
if __name__ == '__main__':
    print("Backend Flask INICIADO com sucesso!")
    check_notifications()  # Verifica notificações ao iniciar
    # Garante que o servidor Flask rode na porta 5000, como esperado pelo script 'electron:dev'
    app.run(debug=True, port=5000)
