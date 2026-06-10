import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'barbearia.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_configs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM configuracoes')
    rows = cursor.fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}

def update_config(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO configuracoes (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

def get_all_clients():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, phone, email, username FROM clientes')
    clients = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return clients

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Cria a tabela de clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    
    # 2. Cria a tabela de barbeiros
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS barbeiros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    
    # 3. Cria a tabela de agendamentos relacionais
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            barber TEXT NOT NULL,
            service TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )
    ''')

    # 4. Cria a tabela de servicos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco REAL NOT NULL
        )
    ''')

    # 5. Cria a tabela de configuracoes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    
    # Popula contas padrão de barbeiros se a tabela estiver vazia
    cursor.execute('SELECT COUNT(*) as count FROM barbeiros')
    if cursor.fetchone()['count'] == 0:
        barber_accounts = [
            ("marcus", "123", "Marcus Blade", "marcus@420barbershop.com"),
            ("john", "123", "John Razor", "john@420barbershop.com"),
            ("admin", "admin", "Administrador Master", "admin@420barbershop.com")
        ]
        cursor.executemany('''
            INSERT INTO barbeiros (username, password, display_name, email)
            VALUES (?, ?, ?, ?)
        ''', barber_accounts)
        conn.commit()
        print("Contas administrativas de barbeiros pré-populadas!")

    # Popula serviços padrão se a tabela estiver vazia
    cursor.execute('SELECT COUNT(*) as count FROM servicos')
    if cursor.fetchone()['count'] == 0:
        servicos = [
            ("Corte Vintage", 55.00),
            ("Experiência Imperium", 90.00)
        ]
        cursor.executemany('INSERT INTO servicos (nome, preco) VALUES (?, ?)', servicos)
        conn.commit()

    # Popula configurações padrão se a tabela estiver vazia
    cursor.execute('SELECT COUNT(*) as count FROM configuracoes')
    if cursor.fetchone()['count'] == 0:
        configuracoes = [
            ("start_time", "09:00"),
            ("end_time", "19:00"),
            ("nome_primario", "IMPERIUM"),
            ("nome_secundario", "BARBER"),
            ("whatsapp", "5511999999999")
        ]
        cursor.executemany('INSERT INTO configuracoes (key, value) VALUES (?, ?)', configuracoes)
        conn.commit()
        
    conn.close()
    print("Banco de dados SQLite relacional inicializado com sucesso!")


# === Funções de Autenticação & Cadastro ===

def register_client(username, password, name, phone, email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO clientes (username, password, name, phone, email)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, password, name, phone, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        raise Exception("Este nome de usuário já está sendo utilizado.")
    finally:
        conn.close()

def get_client_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def validate_client(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def validate_barber(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM barbeiros WHERE username = ? AND password = ?', (username, password))
    barber = cursor.fetchone()
    conn.close()
    return dict(barber) if barber else None

# === Funções de Agendamento ===

def add_booking(cliente_id, barber, service, date, time, price):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO agendamentos (cliente_id, barber, service, date, time, price)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (cliente_id, barber, service, date, time, price))
    conn.commit()
    conn.close()
    return True

def get_busy_slots(barber, date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT time FROM agendamentos
        WHERE barber = ? AND date = ?
    ''', (barber, date))
    rows = cursor.fetchall()
    conn.close()
    return [row['time'] for row in rows]

def get_client_bookings(cliente_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM agendamentos WHERE cliente_id = ? ORDER BY date DESC, time ASC', (cliente_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_bookings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.id, a.barber, a.service, a.date, a.time, a.price, c.name as cliente_name, c.phone as cliente_phone
        FROM agendamentos a
        JOIN clientes c ON a.cliente_id = c.id
        ORDER BY a.date DESC, a.time ASC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_bookings_by_barber(barber_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.id, a.barber, a.service, a.date, a.time, a.price, c.name as cliente_name, c.phone as cliente_phone
        FROM agendamentos a
        JOIN clientes c ON a.cliente_id = c.id
        WHERE a.barber = ?
        ORDER BY a.date DESC, a.time ASC
    ''', (barber_name,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_booking_by_client(booking_id, cliente_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM agendamentos WHERE id = ? AND cliente_id = ?', (booking_id, cliente_id))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def delete_booking_by_admin(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM agendamentos WHERE id = ?', (booking_id,))
    conn.commit()
    conn.close()
    return True

# === Funções Dinâmicas (SaaS) ===

def get_all_barbers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, display_name, email FROM barbeiros WHERE username != "admin"')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_barber(username, password, display_name, email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO barbeiros (username, password, display_name, email)
            VALUES (?, ?, ?, ?)
        ''', (username, password, display_name, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_barber(barber_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM barbeiros WHERE id = ? AND username != "admin"', (barber_id,))
    conn.commit()
    conn.close()
    return True

def get_all_services():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM servicos')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_service(nome, preco):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO servicos (nome, preco) VALUES (?, ?)', (nome, preco))
    conn.commit()
    conn.close()
    return True

def delete_service(service_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM servicos WHERE id = ?', (service_id,))
    conn.commit()
    conn.close()
    return True

def get_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM configuracoes')
    rows = cursor.fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}

def update_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE configuracoes SET value = ? WHERE key = ?', (value, key))
    conn.commit()
    conn.close()
    return True
