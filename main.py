import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
import database

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = '420_barbershop_key_2026'

database.init_db()

@app.context_processor
def inject_config():
    return dict(site_config=database.get_all_configs())

EMAIL_LOG_PATH = os.path.join(os.path.dirname(__file__), 'notificacoes_email.txt')

def simulate_email_notification(to_email, subject, body_html):
    try:
        with open(EMAIL_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write("====================================================\n")
            f.write(f" ALERTA DE NOTIFICAÇÃO DISPARADO PARA: {to_email}\n")
            f.write(f" ASSUNTO: {subject}\n")
            f.write("----------------------------------------------------\n")
            plain_text = body_html.replace("<br>", "\n").replace("<strong>", "").replace("</strong>", "")
            f.write(plain_text)
            f.write("\n====================================================\n\n")
    except Exception as e:
        print(f"Erro ao salvar notificação local: {e}")

def send_real_email(to_email, subject, body_html):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_port, smtp_email, smtp_password]):
        simulate_email_notification(to_email, subject, body_html)
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))
        
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, to_email, msg.as_string())
        server.quit()
        simulate_email_notification(to_email, f"[ENVIADO] {subject}", body_html)
        return True
    except Exception as e:
        simulate_email_notification(to_email, f"[FALHA-SMTP] {subject}", body_html)
        return False

def check_if_past(date_str, time_str):
    import datetime
    try:
        parts = date_str.split(" de ")
        if len(parts) != 2:
            return False
        day = int(parts[0])
        month_name = parts[1]
        
        months_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        if month_name not in months_pt:
            return False
        month = months_pt.index(month_name) + 1
        
        now = datetime.datetime.now()
        year = now.year
        
        if month == 1 and now.month == 12:
            year += 1
        elif month == 12 and now.month == 1:
            year -= 1
            
        hour, minute = map(int, time_str.split(":"))
        booking_dt = datetime.datetime(year, month, day, hour, minute)
        return booking_dt < now
    except Exception:
        return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
        
    user_type = request.form.get('user_type')
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    if user_type == 'client':
        user = database.validate_client(username, password)
        if user:
            session['user_id'] = user['id']
            session['user_type'] = 'client'
            session['username'] = user['username']
            session['name'] = user['name']
            session['phone'] = user['phone']
            session['email'] = user['email']
            return redirect(url_for('index'))
    else:
        barber = database.validate_barber(username, password)
        if barber:
            session['user_id'] = barber['id']
            session['user_type'] = 'barber'
            session['username'] = barber['username']
            session['display_name'] = barber['display_name']
            session['email'] = barber['email']
            return redirect(url_for('admin'))
            
    flash("Usuário ou senha incorretos.", "error")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
        
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    try:
        database.register_client(username, password, name, phone, email)
        user = database.validate_client(username, password)
        if user:
            session['user_id'] = user['id']
            session['user_type'] = 'client'
            session['username'] = user['username']
            session['name'] = user['name']
            session['phone'] = user['phone']
            session['email'] = user['email']
        return redirect(url_for('index'))
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for('register'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/my-bookings')
def my_bookings():
    if 'user_id' not in session or session.get('user_type') != 'client':
        return redirect(url_for('login'))
    bookings = database.get_client_bookings(session['user_id'])
    for b in bookings:
        b['is_past'] = check_if_past(b['date'], b['time'])
    return render_template('my_bookings.html', client_name=session['name'].upper(), bookings=bookings)

@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('user_type') != 'barber':
        return redirect(url_for('login'))
        
    barber_display_name = session['display_name']
    is_master = (session['username'] == 'admin')
    
    if is_master:
        bookings = database.get_all_bookings()
    else:
        bookings = database.get_bookings_by_barber(barber_display_name)
        
    for b in bookings:
        b['is_past'] = check_if_past(b['date'], b['time'])
        
    total_bookings = len(bookings)
    total_revenue = sum(b['price'] for b in bookings)
    
    barber_counts = {}
    all_bookings = database.get_all_bookings()
    for b in all_bookings:
        barber_counts[b['barber']] = barber_counts.get(b['barber'], 0) + 1
    top_barber = max(barber_counts, key=barber_counts.get) if barber_counts else None

    # Novos dados para o Painel Dinâmico
    servicos_db = []
    barbeiros_db = []
    clientes_crm = []
    if is_master:
        servicos_db = database.get_all_services()
        barbeiros_db = database.get_all_barbers()
        clientes_crm = database.get_all_clients()

    return render_template(
        'admin.html',
        bookings=bookings,
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        top_barber=top_barber,
        is_master=is_master,
        servicos_db=servicos_db,
        barbeiros_db=barbeiros_db,
        clientes_crm=clientes_crm
    )

@app.route('/api/busy-slots', methods=['GET'])
def api_busy_slots():
    barber = request.args.get('barber', '').strip()
    date = request.args.get('date', '').strip()
    if not barber or not date:
        return jsonify([])
    try:
        busy_slots = database.get_busy_slots(barber, date)
        return jsonify(busy_slots)
    except Exception as e:
        return jsonify([])

@app.route('/api/book', methods=['POST'])
def api_book():
    data = request.get_json() or {}
    
    # Se estiver logado
    if 'user_id' in session and session.get('user_type') == 'client':
        client_id = session['user_id']
        client_name = session['name']
        client_phone = session['phone']
        client_email = session['email']
    else:
        # Tenta cadastrar ou recuperar dados do visitante
        client_name = data.get('client_name', '').strip()
        client_phone = data.get('client_phone', '').strip()
        client_email = data.get('client_email', '').strip()
        
        if not all([client_name, client_phone, client_email]):
            return jsonify({"error": "Preencha seus dados de identificação (Nome, E-mail e WhatsApp)."}), 400
            
        # Verifica se já existe um cliente com esse e-mail
        user = database.get_client_by_email(client_email)
        if not user:
            try:
                database.register_client(client_email, client_phone, client_name, client_phone, client_email)
                user = database.get_client_by_email(client_email)
            except Exception as e:
                return jsonify({"error": f"Erro ao registrar cadastro automático: {str(e)}"}), 500
        
        if user:
            # Login silencioso
            session['user_id'] = user['id']
            session['user_type'] = 'client'
            session['username'] = user['username']
            session['name'] = user['name']
            session['phone'] = user['phone']
            session['email'] = user['email']
            client_id = user['id']
        else:
            return jsonify({"error": "Não foi possível autenticar seu agendamento."}), 500

    barber = data.get('barber', '').strip()
    service = data.get('service', '').strip()
    date = data.get('date', '').strip()
    time = data.get('time', '').strip()
    price = data.get('price')
    
    if not all([barber, service, date, time]) or price is None:
        return jsonify({"error": "Dados de agendamento incompletos."}), 400
        
    try:
        busy_slots = database.get_busy_slots(barber, date)
        if time in busy_slots:
            return jsonify({"error": "Desculpe, senhor. Este horário já foi reservado."}), 409
            
        database.add_booking(client_id, barber, service, date, time, float(price))
        
        barber_emails = {
            "Marcus Blade": "marcus@420barbershop.com",
            "John Razor": "john@420barbershop.com"
        }
        barber_email = barber_emails.get(barber, "contato@420barbershop.com")

        subject = f"💈 NOVO AGENDAMENTO: {client_name}"
        body_html = f"""
        <strong>Olá, {barber}!</strong><br><br>
        Você tem um novo cliente agendado:<br><br>
        👤 <strong>Cliente:</strong> {client_name}<br>
        📞 <strong>Celular:</strong> {client_phone}<br>
        ✂️ <strong>Serviço:</strong> {service}<br>
        📅 <strong>Data:</strong> {date}<br>
        ⏰ <strong>Horário:</strong> {time} horas<br>
        💵 <strong>Valor:</strong> R$ {float(price):.2f}<br>
        """
        send_real_email(barber_email, subject, body_html)
        return jsonify({"status": "success", "message": "Agendamento concluído!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/client-cancel', methods=['POST'])
def api_client_cancel():
    if 'user_id' not in session or session.get('user_type') != 'client':
        return jsonify({"error": "Operação não autorizada."}), 401
        
    data = request.get_json() or {}
    booking_id = data.get('id')
    
    if not booking_id:
        return jsonify({"error": "ID da reserva ausente."}), 400
        
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agendamentos WHERE id = ?', (booking_id,))
        b = cursor.fetchone()
        conn.close()

        if b and check_if_past(b['date'], b['time']):
            return jsonify({"error": "Desculpe, senhor. Não é possível cancelar agendamentos que já passaram."}), 400

        success = database.delete_booking_by_client(int(booking_id), session['user_id'])
        if success and b:
            barber = b['barber']
            service = b['service']
            date = b['date']
            time = b['time']
            
            barber_emails = {
                "Marcus Blade": "marcus@420barbershop.com",
                "John Razor": "john@420barbershop.com"
            }
            barber_email = barber_emails.get(barber, "contato@420barbershop.com")
            
            subject = f"⚠️ CANCELAMENTO DE RESERVA: {session['name']}"
            body_html = f"""
            <strong>Olá, {barber}!</strong><br><br>
            Atenção: O cliente cancelou o agendamento:<br><br>
            👤 <strong>Cliente:</strong> {session['name']}<br>
            ✂️ <strong>Serviço:</strong> {service}<br>
            📅 <strong>Data:</strong> {date}<br>
            ⏰ <strong>Horário:</strong> {time} horas<br>
            """
            send_real_email(barber_email, subject, body_html)
            return jsonify({"status": "success", "message": "Cancelamento realizado!"})
        return jsonify({"error": "Reserva não encontrada."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cancel-booking', methods=['POST'])
def api_cancel_booking():
    if 'user_id' not in session or session.get('user_type') != 'barber':
        return jsonify({"error": "Operação restrita à equipe."}), 401
        
    data = request.get_json() or {}
    booking_id = data.get('id')
    
    if not booking_id:
        return jsonify({"error": "ID inválido."}), 400
        
    try:
        database.delete_booking_by_admin(int(booking_id))
        return jsonify({"status": "success", "message": "Cancelado com sucesso."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Rotas da API de Configurações Dinâmicas (SaaS) ===

@app.route('/api/servicos', methods=['GET'])
def api_servicos():
    servicos = database.get_all_services()
    return jsonify(servicos)

@app.route('/api/barbeiros', methods=['GET'])
def api_barbeiros():
    barbeiros = database.get_all_barbers()
    return jsonify(barbeiros)

@app.route('/api/configuracoes', methods=['GET'])
def api_configuracoes():
    settings = database.get_settings()
    return jsonify(settings)

# === Rotas do Painel de Administração Dinâmica ===

@app.route('/admin/add_service', methods=['POST'])
def admin_add_service():
    if 'user_id' not in session or session.get('user_type') != 'barber' or session.get('username') != 'admin':
        return jsonify({"error": "Apenas o Administrador Master pode adicionar serviços."}), 403
    
    data = request.get_json() or {}
    nome = data.get('nome', '').strip()
    preco = data.get('preco')
    
    if not nome or preco is None:
        return jsonify({"error": "Dados inválidos."}), 400
        
    try:
        database.add_service(nome, float(preco))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/delete_service', methods=['POST'])
def admin_delete_service():
    if 'user_id' not in session or session.get('user_type') != 'barber' or session.get('username') != 'admin':
        return jsonify({"error": "Acesso negado."}), 403
        
    data = request.get_json() or {}
    service_id = data.get('id')
    if not service_id:
        return jsonify({"error": "ID inválido."}), 400
        
    try:
        database.delete_service(int(service_id))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/add_barber', methods=['POST'])
def admin_add_barber():
    if 'user_id' not in session or session.get('user_type') != 'barber' or session.get('username') != 'admin':
        return jsonify({"error": "Acesso negado."}), 403
        
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    display_name = data.get('display_name', '').strip()
    email = data.get('email', '').strip()
    
    if not all([username, password, display_name, email]):
        return jsonify({"error": "Dados incompletos."}), 400
        
    success = database.add_barber(username, password, display_name, email)
    if success:
        return jsonify({"status": "success"})
    return jsonify({"error": "Usuário já existe."}), 409

@app.route('/admin/delete_barber', methods=['POST'])
def admin_delete_barber():
    if 'user_id' not in session or session.get('user_type') != 'barber' or session.get('username') != 'admin':
        return jsonify({"error": "Acesso negado."}), 403
        
    data = request.get_json() or {}
    barber_id = data.get('id')
    
    if not barber_id:
        return jsonify({"error": "ID inválido."}), 400
        
    try:
        database.delete_barber(int(barber_id))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/update_config', methods=['POST'])
def update_config():
    if 'user_id' not in session or session.get('username') != 'admin':
        return jsonify({"error": "Acesso negado"}), 403
    data = request.get_json()
    for key, val in data.items():
        database.update_config(key, val)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
