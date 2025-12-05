from flask import Flask, render_template, request, redirect, url_for, session, make_response, Response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import pandas as pd
from io import BytesIO, StringIO
import xlsxwriter
from fpdf import FPDF
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def require_role(required_role=None):
    """Decorador para verificar roles. Si required_role es None, solo requiere estar logueado."""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                return redirect(url_for('login'))
            
            # Si no se especifica rol, cualquier usuario logueado puede acceder
            if required_role is None:
                return f(*args, **kwargs)
            
            # Verificar rol del usuario
            user_rol = session.get('rol')
            if user_rol == 'admin' or (required_role == 'empleado' and user_rol == 'empleado'):
                return f(*args, **kwargs)
            else:
                return 'No tienes permisos para acceder a esta página', 403
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

def is_admin():
    """Verifica si el usuario actual es admin"""
    return session.get('rol') == 'admin' or session.get('username') == 'admin'

def is_empleado():
    """Verifica si el usuario actual es empleado"""
    return session.get('rol') == 'empleado'

def get_user_context():
    """Obtiene el contexto del usuario para las plantillas"""
    username = session.get('username', 'Usuario')
    rol = session.get('rol', 'Sin rol')
    nombre_completo = username
    
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT nombre_completo FROM usuarios WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        if user:
            nombre_completo = user['nombre_completo']
    
    return {
        'username': nombre_completo,
        'rol': rol,
        'current_user': session.get('username')
    }

@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect(url_for('admin'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Primero verificar el admin hardcoded (para compatibilidad)
        if username == 'admin' and password == 'adminarthu':
            session['logged_in'] = True
            session['username'] = 'admin'
            session['rol'] = 'admin'
            return redirect(url_for('admin'))
        
        # Luego verificar en la base de datos
        conn = get_db_connection()
        # Primero verificar si el usuario existe
        user = conn.execute(
            'SELECT * FROM usuarios WHERE nombre_usuario = ?',
            (username,)
        ).fetchone()
        
        if user:
            # Verificar que el usuario esté activo
            if user['estado'] != 'Activo':
                conn.close()
                return render_template('login.html', error='Tu cuenta está inactiva. Contacta al administrador.')
            
            conn.close()
            stored_password = user['contraseña']
            
            # Intentar verificar con check_password_hash (funciona con hashes y detecta texto plano)
            # Si la contraseña está hasheada, check_password_hash la verificará
            # Si está en texto plano, check_password_hash retornará False y verificamos manualmente
            if check_password_hash(stored_password, password):
                # Contraseña hasheada y correcta
                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = user['id']
                session['rol'] = user['rol']
                return redirect(url_for('admin'))
            elif stored_password == password:
                # Contraseña en texto plano (para compatibilidad con usuarios antiguos)
                # Actualizar a hash para mayor seguridad
                conn = get_db_connection()
                hashed_password = generate_password_hash(password)
                conn.execute('UPDATE usuarios SET contraseña = ? WHERE id = ?', 
                           (hashed_password, user['id']))
                conn.commit()
                conn.close()
                
                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = user['id']
                session['rol'] = user['rol']
            return redirect(url_for('admin'))
        
        return render_template('login.html', error='Credenciales inválidas')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if 'logged_in' in session:
        username = session.get('username', 'Usuario')
        rol = session.get('rol', 'Sin rol')

        # Obtener nombre completo si es un usuario de la BD
        nombre_completo = username
        if 'user_id' in session:
            conn = get_db_connection()
            user = conn.execute(
                'SELECT nombre_completo FROM usuarios WHERE id = ?',
                (session['user_id'],)
            ).fetchone()
            conn.close()
            if user:
                nombre_completo = user['nombre_completo']

        # Obtener datos de pruebas por categoría para la gráfica
        conn = get_db_connection()

        # Total real de pruebas (todas las realizadas)
        total_pruebas_real = conn.execute(
            'SELECT COUNT(*) FROM pruebas_paciente'
        ).fetchone()[0]

        # Conteo de pruebas por categoría (tipo de prueba)
        # Evita duplicados si hay nombres repetidos en la tabla "pruebas"
        pruebas_por_categoria = conn.execute('''
            SELECT 
                t.name AS categoria,
                COUNT(DISTINCT pp.id) AS cantidad
            FROM pruebas_paciente pp
            JOIN (
                SELECT DISTINCT id, name FROM pruebas
            ) t ON pp.test_id = t.id
            GROUP BY t.name
            ORDER BY cantidad DESC
        ''').fetchall()

        conn.close()

        # Convertir los resultados a formato JSON para la plantilla
        datos_grafica = [
            {'categoria': row['categoria'], 'cantidad': row['cantidad']}
            for row in pruebas_por_categoria
        ]

        # Validar totales
        total_calculado = sum(row['cantidad'] for row in datos_grafica)
        print("DEBUG -> Total real:", total_pruebas_real)
        print("DEBUG -> Total gráfico:", total_calculado)

        # Contexto para el template
        context = get_user_context()
        context.update({
            'username': nombre_completo,
            'rol': rol,
            'current_user': session.get('username'),
            'datos_grafica': datos_grafica,
            'total_pruebas_real': total_pruebas_real
        })

        return render_template('admin.html', **context)

    # Si no hay sesión activa, redirigir al login
    return redirect(url_for('login'))

@app.route('/pacientes', methods=['GET', 'POST'])
def pacientes():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()

    if request.method == 'POST':
        # Todos los usuarios pueden agregar pacientes
        name = request.form['name']
        identification_number = request.form['identification_number']
        date_of_birth = request.form['date_of_birth']
        gender = request.form['gender']
        address = request.form['address']
        phone = request.form['phone']
        
        conn.execute('''
            INSERT INTO patients (name, identification_number, date_of_birth, gender, address, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, identification_number, date_of_birth, gender, address, phone))
        conn.commit()
        
    search_name = request.args.get('search_name')
    query = 'SELECT * FROM patients WHERE 1=1'
    params = []
    if search_name:
        query += ' AND name LIKE ?'
        params.append(f'%{search_name}%')
    pacientes = conn.execute(query, params).fetchall()
    
    # Obtener información del usuario para el menú
    username = session.get('username', 'Usuario')
    rol = session.get('rol', 'Sin rol')
    nombre_completo = username
    if 'user_id' in session:
        user = conn.execute('SELECT nombre_completo FROM usuarios WHERE id = ?', (session['user_id'],)).fetchone()
        if user:
            nombre_completo = user['nombre_completo']
        conn.close()
    
    return render_template('pacientes.html', pacientes=pacientes, is_admin=is_admin(), username=nombre_completo, rol=rol, current_user=session.get('username'))


@app.route('/editar_paciente/<int:id>', methods=['GET', 'POST'])
@require_role('admin')
def editar_paciente(id):
    conn = get_db_connection()
    paciente = conn.execute('SELECT * FROM patients WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        name = request.form['name']
        identification_number = request.form['identification_number']
        date_of_birth = request.form['date_of_birth']
        gender = request.form['gender']
        address = request.form['address']
        phone = request.form['phone']
        conn.execute('''
            UPDATE patients
            SET name = ?, identification_number = ?, date_of_birth = ?, gender = ?, address = ?, phone = ?
            WHERE id = ?
        ''', (name, identification_number, date_of_birth, gender, address, phone, id))
        conn.commit()
        conn.close()
        return redirect(url_for('pacientes'))
    context = get_user_context()
    context.update({
        'paciente': paciente,
        'is_admin': is_admin()
    })
    conn.close()
    return render_template('editar_paciente.html', **context)

@app.route('/eliminar_paciente/<int:id>')
@require_role('admin')
def eliminar_paciente(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM patients WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('pacientes'))

@app.route('/pruebas_paciente', methods=['GET', 'POST'])
def pruebas_paciente():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Manejar la creación de una nueva prueba
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        test_id = request.form['test_id']
        test_date = request.form['test_date']
        result = request.form['result']
        result_date = request.form['result_date']
        laboratory = request.form['laboratory']
        
        conn.execute('''
            INSERT INTO pruebas_paciente 
            (patient_id, test_id, test_date, result, result_date, laboratory) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (patient_id, test_id, test_date, result, result_date, laboratory))
        conn.commit()
    
    # Obtener la lista de pacientes para el select
    pacientes = conn.execute('SELECT id, name FROM patients').fetchall()
    
    # Obtener solo las pruebas específicas (PCR, Antígeno, Anticuerpo)
    pruebas = conn.execute('''
        SELECT id, name 
        FROM pruebas 
        WHERE name IN ('PCR', 'Antígeno', 'Anticuerpo')
    ''').fetchall()
    
    # Buscar pruebas por nombre de paciente si se especifica
    search_name = request.args.get('search_name')
    query = '''
        SELECT
            pp.id,
            p.name AS patient_name,
            t.name AS test_name,
            pp.test_date,
            pp.result,
            pp.result_date,
            pp.laboratory
        FROM pruebas_paciente pp
        JOIN patients p ON pp.patient_id = p.id
        JOIN pruebas t ON pp.test_id = t.id
        WHERE 1=1
    '''
    params = []
    if search_name:
        query += ' AND p.name LIKE ?'
        params.append(f'%{search_name}%')
    query += ' ORDER BY pp.test_date DESC, pp.id DESC'
    
    # Obtener las pruebas registradas
    pruebas_paciente = conn.execute(query, params).fetchall()
    conn.close()
    
    # Obtener información del usuario y rol para el menú
    username = session.get('username', 'Usuario')
    rol = session.get('rol', 'Sin rol')
    
    # Obtener nombre completo si es un usuario de la BD
    nombre_completo = username
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute(
            'SELECT nombre_completo FROM usuarios WHERE id = ?',
            (session['user_id'],)
        ).fetchone()
        conn.close()
        if user:
            nombre_completo = user['nombre_completo']
    
    # Renderizar la plantilla con todos los datos necesarios
    return render_template('pruebas_paciente.html',
                         pacientes=pacientes,
                         pruebas=pruebas,
                         pruebas_paciente=pruebas_paciente,
                         is_admin=is_admin(),
                         username=nombre_completo,
                         rol=rol,
                         current_user=session.get('username'))
@app.route('/editar_prueba_paciente/<int:id>', methods=['GET', 'POST'])
@require_role('admin')
def editar_prueba_paciente(id):
    conn = get_db_connection()
    # Obtener la prueba específica con información detallada
    prueba = conn.execute('''
        SELECT pp.*, p.name as patient_name
        FROM pruebas_paciente pp
        LEFT JOIN patients p ON pp.patient_id = p.id
        WHERE pp.id = ?
    ''', (id,)).fetchone()
    
    if prueba is None:
        conn.close()
        return "Prueba no encontrada", 404
        
    # Obtener lista de pacientes para el select
    pacientes = conn.execute('SELECT id, name FROM patients').fetchall()
    
    # Solo seleccionar PCR, Antígeno y Anticuerpo
    pruebas = conn.execute('''
        SELECT id, name 
        FROM pruebas 
        WHERE name IN ('PCR', 'Antígeno', 'Anticuerpo')
    ''').fetchall()
    
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        test_id = request.form['test_id']
        test_date = request.form['test_date']
        result = request.form['result']
        result_date = request.form['result_date']
        laboratory = request.form['laboratory']
        
        # Actualizar la prueba
        conn.execute('''
            UPDATE pruebas_paciente 
            SET patient_id = ?, 
                test_id = ?, 
                test_date = ?, 
                result = ?, 
                result_date = ?, 
                laboratory = ? 
            WHERE id = ?
        ''', (patient_id, test_id, test_date, result, result_date, laboratory, id))
        
        conn.commit()
        conn.close()
        return redirect(url_for('pruebas_paciente'))
    
    conn.close()
    
    # Obtener el contexto del usuario y agregar las variables adicionales
    context = get_user_context()
    context.update({
        'prueba': prueba,
        'pacientes': pacientes,
        'pruebas': pruebas,
        'is_admin': is_admin()
    })
    
    return render_template('editar_prueba_paciente.html', **context)

@app.route('/eliminar_prueba_paciente/<int:id>')
@require_role('admin')
def eliminar_prueba_paciente(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM pruebas_paciente WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('pruebas_paciente'))

@app.route('/descargar_reporte/<int:prueba_id>')
def descargar_reporte(prueba_id):
    """Ruta pública para descargar el reporte PDF de una prueba específica (sin necesidad de login)"""
    buffer = generar_reporte_prueba_pdf(prueba_id)
    
    if buffer is None:
        return "Prueba no encontrada", 404
    
    # Obtener nombre del archivo basado en la prueba
    conn = get_db_connection()
    prueba_info = conn.execute('''
        SELECT p.name, pp.test_date, t.name AS test_name
        FROM pruebas_paciente pp
        JOIN patients p ON pp.patient_id = p.id
        JOIN pruebas t ON pp.test_id = t.id
        WHERE pp.id = ?
    ''', (prueba_id,)).fetchone()
    conn.close()
    
    if prueba_info:
        # Nombre del archivo: NombrePaciente_FechaPrueba_NombrePrueba.pdf
        nombre_archivo = f"{prueba_info['name'].replace(' ', '_')}_{prueba_info['test_date']}_{prueba_info['test_name'].replace(' ', '_')}.pdf"
        nombre_archivo = nombre_archivo.replace('/', '_')  # Reemplazar / en fechas
    else:
        nombre_archivo = f"reporte_prueba_{prueba_id}.pdf"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype='application/pdf'
    )

@app.route('/pruebas', methods=['GET', 'POST'])
@require_role('admin')
def pruebas():
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        code = request.form['code']
        description = request.form['description']
        category = request.form['category']
        method = request.form['method']
        duration = request.form['duration']
        status = request.form['status']
        conn.execute('INSERT INTO pruebas (name, code, description, category, method, duration, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (name, code, description, category, method, duration, status))
        conn.commit()
    search_name = request.args.get('search_name')
    query = 'SELECT * FROM pruebas WHERE 1=1'
    params = []
    if search_name:
        query += ' AND name LIKE ?'
        params.append(f'%{search_name}%')
    pruebas = conn.execute(query, params).fetchall()
    conn.close()
    context = get_user_context()
    context.update({
        'pruebas': pruebas,
        'is_admin': is_admin()
    })
    return render_template('pruebas.html', **context)

@app.route('/editar_prueba/<int:id>', methods=['GET', 'POST'])
@require_role('admin')
def editar_prueba(id):
    conn = get_db_connection()
    prueba = conn.execute('SELECT * FROM pruebas WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        nombre = request.form['name'] 
        codigo = request.form['code']
        descripcion = request.form['description']
        categoria = request.form['category']
        metodo = request.form['method']
        duracion = request.form['duration']
        estado = request.form['status']
        conn.execute('''
            UPDATE pruebas
            SET name = ?, code = ?, description = ?, category = ?, method = ?, duration = ?, status = ?
            WHERE id = ?
        ''', (nombre, codigo, descripcion, categoria, metodo, duracion, estado, id))
        conn.commit()
        conn.close()
        return redirect(url_for('pruebas'))
    context = get_user_context()
    context.update({
        'prueba': prueba,
        'is_admin': is_admin()
    })
    conn.close()
    return render_template('editar_prueba.html', **context)

@app.route('/eliminar_prueba/<int:id>')
@require_role('admin')
def eliminar_prueba(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM pruebas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('pruebas'))

@app.route('/usuarios', methods=['GET', 'POST'])
@require_role('admin')
def usuarios():
    conn = get_db_connection()
    if request.method == 'POST':
        rol = request.form['rol']
        nombre_completo = request.form['nombre_completo']
        correo_electronico = request.form['correo_electronico']
        nombre_usuario = request.form['nombre_usuario']
        contraseña = request.form['contraseña']
        confirmacion_contraseña = request.form['confirmacion_contraseña']
        numero_telefono = request.form['numero_telefono']
        estado = request.form['estado']
        fecha_creacion = request.form['fecha_creacion']

        if contraseña != confirmacion_contraseña:
            return "Las contraseñas no coinciden"
        # Normalizar el rol: convertir "Administrador" a "admin" y "Empleado" a "empleado"
        if rol == "Administrador":
            rol = "admin"
        elif rol == "Empleado":
            rol = "empleado"
        # Hashear la contraseña antes de guardarla
        hashed_password = generate_password_hash(contraseña)
        conn.execute('INSERT INTO usuarios (rol, nombre_completo, correo_electronico, nombre_usuario, contraseña, numero_telefono, estado, fecha_creacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                     (rol, nombre_completo, correo_electronico, nombre_usuario, hashed_password, numero_telefono, estado, fecha_creacion))
        conn.commit()
    search_name = request.args.get('search_name')
    query = 'SELECT * FROM usuarios WHERE 1=1'
    params = []
    if search_name:
        query += ' AND nombre_completo LIKE ?'
        params.append(f'%{search_name}%')
    usuarios = conn.execute(query, params).fetchall()
    conn.close()
    context = get_user_context()
    context.update({
        'usuarios': usuarios,
        'is_admin': is_admin()
    })
    return render_template('usuarios.html', **context)

@app.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@require_role('admin')
def editar_usuario(id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuarios WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        nombre = request.form['nombre_completo']
        correo = request.form['correo_electronico']
        nombre_usuario = request.form['nombre_usuario']
        telefono = request.form['numero_telefono']
        rol = request.form['rol']
        estado = request.form['estado']
        
        # Normalizar el rol
        if rol == "Administrador":
            rol = "admin"
        elif rol == "Empleado":
            rol = "empleado"
            
        password = request.form.get('contraseña')
        
        if password:
            # Si se proporcionó una nueva contraseña, actualizamos todos los campos incluyendo la contraseña
            hashed_password = generate_password_hash(password)
            conn.execute('''
                UPDATE usuarios 
                SET nombre_completo = ?, 
                    correo_electronico = ?, 
                    nombre_usuario = ?, 
                    numero_telefono = ?, 
                    rol = ?, 
                    estado = ?,
                    contraseña = ?
                WHERE id = ?
            ''', (nombre, correo, nombre_usuario, telefono, rol, estado, hashed_password, id))
        else:
            # Si no se proporcionó contraseña, actualizamos todos los campos excepto la contraseña
            conn.execute('''
                UPDATE usuarios 
                SET nombre_completo = ?, 
                    correo_electronico = ?, 
                    nombre_usuario = ?, 
                    numero_telefono = ?, 
                    rol = ?, 
                    estado = ?
                WHERE id = ?
            ''', (nombre, correo, nombre_usuario, telefono, rol, estado, id))
        
        conn.commit()
        conn.close()
        return redirect(url_for('usuarios'))
        
    context = get_user_context()
    context.update({
        'user': user,
        'is_admin': is_admin()
    })
    conn.close()
    return render_template('editar_usuario.html', **context)

@app.route('/eliminar_usuario/<int:id>')
@require_role('admin')
def eliminar_usuario(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM usuarios WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('usuarios'))

@app.route('/informes', methods=['GET', 'POST'])
def informes():
    conn = get_db_connection()
    
    # Obtener datos de resumen
    total_pacientes = conn.execute('SELECT COUNT(*) FROM patients').fetchone()[0]
    total_pruebas = conn.execute('SELECT COUNT(*) FROM pruebas_paciente').fetchone()[0]
    
    # Contar pruebas por categoría (solo Anticuerpos, Antígeno y PCR)
    pacientes_por_estado = conn.execute('''
        SELECT 
            t.name AS tipo_prueba,
            COUNT(pp.id) AS cantidad
        FROM pruebas_paciente pp
        JOIN pruebas t ON pp.test_id = t.id
        WHERE t.name IN ('Anticuerpos', 'Antígeno', 'PCR')
        GROUP BY t.name
        ORDER BY t.name
    ''').fetchall()
    
    # Obtener todos los pacientes y pruebas para las tablas
    pacientes = conn.execute('SELECT * FROM patients').fetchall()
    pruebas = conn.execute(''' 
        SELECT pp.id, p.name AS patient_name, t.name AS test_name, t.code, pp.test_date, pp.result, pp.result_date, pp.laboratory
        FROM pruebas_paciente pp
        JOIN patients p ON pp.patient_id = p.id
        JOIN pruebas t ON pp.test_id = t.id
    ''').fetchall()
    
    # Manejar búsqueda si se envió el formulario
    search_query = None
    if request.method == 'POST':
        search_query = request.form.get('search_query', '')
        
        if search_query:
            # Buscar pacientes que coincidan con la consulta
            pacientes = conn.execute(
                'SELECT * FROM patients WHERE name LIKE ? OR identification_number LIKE ?',
                ('%' + search_query + '%', '%' + search_query + '%')
            ).fetchall()
            
            # Buscar pruebas relacionadas con pacientes que coincidan
            pruebas = conn.execute(''' 
                SELECT pp.id, p.name AS patient_name, t.name AS test_name, t.code, pp.test_date, pp.result, pp.result_date, pp.laboratory
                FROM pruebas_paciente pp
                JOIN patients p ON pp.patient_id = p.id
                JOIN pruebas t ON pp.test_id = t.id
                WHERE p.name LIKE ? OR p.identification_number LIKE ? OR t.name LIKE ?
            ''', ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%')).fetchall()
    
    conn.close()
    context = get_user_context()
    context.update({
        'total_pacientes': total_pacientes,
        'total_pruebas': total_pruebas,
        'pacientes_por_estado': pacientes_por_estado,
        'pacientes': pacientes,
        'pruebas': pruebas,
        'search_query': search_query
    })
    return render_template('informes.html', **context)
@app.route('/informes/detalle', methods=['GET', 'POST'])
def informes_detalle():
    conn = get_db_connection()
    if request.method == 'POST':
        search_query = request.form.get('search_query')
        if search_query:
            pacientes = conn.execute('''SELECT * FROM patients WHERE name LIKE ? OR identification_number LIKE ?''', 
                                     ('%' + search_query + '%', '%' + search_query + '%')).fetchall()
            pruebas = conn.execute(''' 
                SELECT pp.id, p.name AS patient_name, t.name AS test_name, t.code, pp.test_date, pp.result, pp.result_date, pp.laboratory
                FROM pruebas_paciente pp
                JOIN patients p ON pp.patient_id = p.id
                JOIN pruebas t ON pp.test_id = t.id
                WHERE p.name LIKE ? OR p.identification_number LIKE ?
            ''', ('%' + search_query + '%', '%' + search_query + '%')).fetchall()
        else:
            pacientes = conn.execute('SELECT * FROM patients').fetchall()
            pruebas = conn.execute(''' 
                SELECT pp.id, p.name AS patient_name, t.name AS test_name, t.code, pp.test_date, pp.result, pp.result_date, pp.laboratory
                FROM pruebas_paciente pp
                JOIN patients p ON pp.patient_id = p.id
                JOIN pruebas t ON pp.test_id = t.id
            ''').fetchall()
        if 'export_excel' in request.form:
            df = pd.DataFrame(pruebas, columns=['id', 'patient_name', 'test_name', 'code', 'test_date', 'result', 'result_date', 'laboratory'])
            df = df.drop(columns=['id'])
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Pruebas')
            output.seek(0)
            return Response(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment;filename=pruebas.xlsx"}
            )
        conn.close()
        context = get_user_context()
        context.update({
            'pacientes': pacientes,
            'pruebas': pruebas
        })
        return render_template('informes_detalle.html', **context)
    else:
        pacientes = conn.execute('SELECT * FROM patients').fetchall()
        pruebas = conn.execute(''' 
            SELECT pp.id, p.name AS patient_name, t.name AS test_name, t.code, pp.test_date, pp.result, pp.result_date, pp.laboratory
            FROM pruebas_paciente pp
            JOIN patients p ON pp.patient_id = p.id
            JOIN pruebas t ON pp.test_id = t.id
        ''').fetchall()
        conn.close()
        context = get_user_context()
        context.update({
            'pacientes': pacientes,
            'pruebas': pruebas
        })
        return render_template('informes_detalle.html', **context)
    
@app.route('/informes/exportar', methods=['POST'])
def exportar_datos():
    format = request.form['format']
    conn = get_db_connection()
    df = pd.read_sql_query('''
        SELECT pruebas_paciente.*, patients.name AS patient_name, pruebas.name AS test_name
        FROM pruebas_paciente
        JOIN patients ON pruebas_paciente.patient_id = patients.id
        JOIN pruebas ON pruebas_paciente.test_id = pruebas.id
    ''', conn)
    conn.close()
    if format == 'csv':
        output = StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=informes.csv"
        response.headers["Content-type"] = "text/csv"
        return response
    elif format == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        response = make_response(output.read())
        response.headers["Content-Disposition"] = "attachment; filename=informes.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response

@app.route('/informacion', methods=['GET', 'POST'])
def informacion():
    """Ruta pública para consultar información de pruebas sin necesidad de login"""
    conn = get_db_connection()
    resultados = []
    pruebas_completas = []  # Para tener acceso a los IDs de pruebas_paciente
    
    if request.method == 'POST':
        nombre = request.form.get('nombre') or ''
        carnet = request.form.get('carnet') or ''
        
        # Query mejorada para obtener más información y el ID de pruebas_paciente
        query = '''
        SELECT 
            pp.id AS prueba_paciente_id,
            p.id AS patient_id,
            p.name,
            p.identification_number,
            pp.test_id,
            pp.test_date,
            pp.result,
            pp.result_date,
            pp.laboratory,
            t.name AS test_name,
            t.code AS test_code
        FROM patients p
        JOIN pruebas_paciente pp ON p.id = pp.patient_id
        JOIN pruebas t ON pp.test_id = t.id
        WHERE p.name LIKE ? AND p.identification_number LIKE ?
        ORDER BY pp.test_date DESC
        '''
        params = [f'%{nombre}%', f'%{carnet}%']
        
        pruebas_completas = conn.execute(query, params).fetchall()
        resultados = [dict(row) for row in pruebas_completas]
        conn.close()
        
        return render_template('informacion.html', 
                             resultados=resultados,
                             pruebas_completas=pruebas_completas,
                             nombre_busqueda=nombre,
                             carnet_busqueda=carnet,
                             is_public=True)
    
        conn.close()
    return render_template('informacion.html', is_public=True)

def export_to_excel_func():
    conn = get_db_connection()
    pacientes = pd.read_sql_query('SELECT * FROM patients', conn)
    pruebas = pd.read_sql_query('SELECT * FROM pruebas_paciente', conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pacientes.to_excel(writer, sheet_name='Pacientes', index=False)
        pruebas.to_excel(writer, sheet_name='Pruebas', index=False)
    output.seek(0)
    response = make_response(output.read())
    response.headers["Content-Disposition"] = "attachment; filename=informes_detalle.xlsx"
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response

def exportar_pdf(resultados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(200, 10, txt='Informe de Pruebas', ln=True, align='C')
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 10, 'ID Paciente', 1)
    pdf.cell(60, 10, 'Nombre', 1)
    pdf.cell(40, 10, 'Carnet', 1)
    pdf.cell(30, 10, 'ID Prueba', 1)
    pdf.cell(30, 10, 'Fecha', 1)
    pdf.cell(30, 10, 'Resultado', 1)
    pdf.ln()
    pdf.set_font('Arial', '', 10)
    for resultado in resultados:
        pdf.cell(40, 10, str(resultado['id']), 1)
        pdf.cell(60, 10, resultado['name'], 1)
        pdf.cell(40, 10, resultado['identification_number'], 1)
        pdf.cell(30, 10, str(resultado['test_id']), 1)
        pdf.cell(30, 10, resultado['test_date'], 1)
        pdf.cell(30, 10, resultado['result'], 1)
        pdf.ln()
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='informe_pruebas.pdf', mimetype='application/pdf')

def generar_reporte_prueba_pdf(prueba_id):
    """Genera un PDF profesional para una prueba específica de un paciente"""
    conn = get_db_connection()
    
    # Obtener información completa de la prueba
    prueba_data = conn.execute('''
        SELECT 
            pp.id AS prueba_id,
            pp.test_date,
            pp.result,
            pp.result_date,
            pp.laboratory,
            p.id AS patient_id,
            p.name AS patient_name,
            p.identification_number,
            p.date_of_birth,
            p.gender,
            p.address,
            p.phone,
            t.id AS test_id,
            t.name AS test_name,
            t.code AS test_code,
            t.description AS test_description,
            t.category AS test_category,
            t.method AS test_method
        FROM pruebas_paciente pp
        JOIN patients p ON pp.patient_id = p.id
        JOIN pruebas t ON pp.test_id = t.id
        WHERE pp.id = ?
    ''', (prueba_id,)).fetchone()
    
    conn.close()
    
    if not prueba_data:
        return None
    
    # Crear PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Configuración de fuentes y colores
    pdf.set_fill_color(59, 130, 246)  # Azul
    pdf.set_text_color(255, 255, 255)
    
    # Encabezado
    pdf.set_font('Arial', 'B', 20)
    pdf.cell(0, 15, 'REPORTE DE PRUEBA MÉDICA', 0, 1, 'C', True)
    pdf.ln(10)
    
    # Información del paciente
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'INFORMACIÓN DEL PACIENTE', 0, 1, 'L')
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_fill_color(245, 247, 250)
    pdf.set_text_color(0, 0, 0)
    
    # Datos del paciente en formato tabla
    datos_paciente = [
        ('Nombre Completo:', prueba_data['patient_name']),
        ('Número de Identificación:', prueba_data['identification_number']),
        ('Fecha de Nacimiento:', prueba_data['date_of_birth']),
        ('Género:', prueba_data['gender']),
        ('Dirección:', prueba_data['address']),
        ('Teléfono:', prueba_data['phone'])
    ]
    
    for etiqueta, valor in datos_paciente:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(60, 8, etiqueta, 0, 0, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, str(valor), 0, 1, 'L')
        pdf.ln(2)
    
    pdf.ln(5)
    
    # Información de la prueba
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'DETALLES DE LA PRUEBA', 0, 1, 'L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 11)
    
    # Datos de la prueba
    datos_prueba = [
        ('Nombre de la Prueba:', prueba_data['test_name']),
        ('Código de Prueba:', prueba_data['test_code']),
        ('Categoría:', prueba_data['test_category']),
        ('Método:', prueba_data['test_method']),
        ('Descripción:', prueba_data['test_description']),
        ('Fecha de Realización:', prueba_data['test_date']),
        ('Fecha de Resultado:', prueba_data['result_date']),
        ('Laboratorio:', prueba_data['laboratory'])
    ]
    
    for etiqueta, valor in datos_prueba:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(60, 8, etiqueta, 0, 0, 'L')
        pdf.set_font('Arial', '', 10)
        # Manejar texto largo
        if len(str(valor)) > 50 and etiqueta in ['Descripción:', 'Dirección:']:
            pdf.multi_cell(0, 8, str(valor), 0, 'L')
        else:
            pdf.cell(0, 8, str(valor), 0, 1, 'L')
        pdf.ln(2)
    
    pdf.ln(5)
    
    # Resultado destacado
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'RESULTADO', 0, 1, 'L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # Resultado con fondo de color
    resultado = prueba_data['result']
    pdf.set_fill_color(59, 130, 246)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 12, resultado.upper(), 0, 1, 'C', True)
    pdf.ln(10)
    
    # Pie de página
    pdf.set_text_color(128, 128, 128)
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 5, f'Reporte generado el: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}', 0, 1, 'C')
    pdf.cell(0, 5, f'ID de Prueba: {prueba_id} | ID de Paciente: {prueba_data["patient_id"]}', 0, 1, 'C')
    
    # Generar buffer
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    
    return buffer

def generar_pdf_pacientes_detallado():
    """Genera un PDF detallado con todos los pacientes en formato horizontal"""
    conn = get_db_connection()
    pacientes = conn.execute('SELECT * FROM patients ORDER BY name').fetchall()
    conn.close()
    
    pdf = FPDF(orientation='L')  # Landscape (horizontal)
    pdf.add_page()
    
    # Encabezado
    pdf.set_fill_color(59, 130, 246)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 20)
    pdf.cell(0, 15, 'REPORTE DETALLADO DE PACIENTES', 0, 1, 'C', True)
    pdf.ln(10)
    
    # Información general
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f'Total de Pacientes: {len(pacientes)}', 0, 1, 'L')
    pdf.ln(5)
    
    # Tabla de pacientes con todas las columnas
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(200, 200, 200)
    
    # Encabezados de tabla - formato horizontal permite más columnas
    pdf.cell(50, 10, 'Nombre', 1, 0, 'C', True)
    pdf.cell(40, 10, 'Carnet de Identidad', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Fecha Nacimiento', 1, 0, 'C', True)
    pdf.cell(25, 10, 'Género', 1, 0, 'C', True)
    pdf.cell(80, 10, 'Dirección', 1, 0, 'C', True)
    pdf.cell(40, 10, 'Teléfono', 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 9)
    pdf.set_fill_color(255, 255, 255)
    
    for paciente in pacientes:
        # Verificar si necesitamos nueva página (altura disponible en landscape)
        if pdf.get_y() > 180:
            pdf.add_page()
            # Repetir encabezados
            pdf.set_font('Arial', 'B', 10)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(50, 10, 'Nombre', 1, 0, 'C', True)
            pdf.cell(40, 10, 'Carnet de Identidad', 1, 0, 'C', True)
            pdf.cell(35, 10, 'Fecha Nacimiento', 1, 0, 'C', True)
            pdf.cell(25, 10, 'Género', 1, 0, 'C', True)
            pdf.cell(80, 10, 'Dirección', 1, 0, 'C', True)
            pdf.cell(40, 10, 'Teléfono', 1, 1, 'C', True)
            pdf.set_font('Arial', '', 9)
            pdf.set_fill_color(255, 255, 255)
        
        # Obtener valores completos
        nombre = str(paciente['name'])
        carnet = str(paciente['identification_number'])
        fecha_nac = str(paciente['date_of_birth'])
        genero = str(paciente['gender'])
        direccion = str(paciente['address'])
        telefono = str(paciente['phone'])
        
        # Escribir datos - calcular altura necesaria primero
        x_inicio = pdf.get_x()
        y_inicio = pdf.get_y()
        
        # Calcular alturas necesarias para cada campo
        pdf.set_font('Arial', '', 9)
        altura_nombre = max(8, (len(nombre) // 30 + 1) * 6)
        altura_direccion = max(8, (len(direccion) // 40 + 1) * 6)
        altura_max = max(altura_nombre, altura_direccion, 8)
        
        # Escribir cada celda con la altura máxima
        # Nombre (puede ser largo, usar multi_cell)
        pdf.set_xy(x_inicio, y_inicio)
        pdf.multi_cell(50, 6, nombre, 1, 'L', False)
        pdf.set_xy(x_inicio + 50, y_inicio)
        
        # Carnet de Identidad
        pdf.cell(40, altura_max, carnet, 1, 0, 'C')
        pdf.set_xy(x_inicio + 90, y_inicio)
        
        # Fecha Nacimiento
        pdf.cell(35, altura_max, fecha_nac, 1, 0, 'C')
        pdf.set_xy(x_inicio + 125, y_inicio)
        
        # Género
        pdf.cell(25, altura_max, genero, 1, 0, 'C')
        pdf.set_xy(x_inicio + 150, y_inicio)
        
        # Dirección (puede ser muy larga, usar multi_cell)
        pdf.multi_cell(80, 6, direccion, 1, 'L', False)
        pdf.set_xy(x_inicio + 230, y_inicio)
        
        # Teléfono
        pdf.cell(40, altura_max, telefono, 1, 0, 'C')
        
        # Mover al siguiente renglón usando la altura máxima
        pdf.set_xy(10, y_inicio + altura_max)
    
    # Pie de página
    pdf.set_text_color(128, 128, 128)
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 5, f'Reporte generado el: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}', 0, 1, 'C')
    
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

def generar_pdf_pruebas_detallado():
    """Genera un PDF detallado con todas las pruebas de pacientes en formato horizontal"""
    conn = get_db_connection()
    pruebas = conn.execute(''' 
        SELECT 
            pp.id,
            p.name AS patient_name,
            p.identification_number,
            t.name AS test_name,
            t.code AS test_code,
            pp.test_date,
            pp.result,
            pp.result_date,
            pp.laboratory,
            t.description AS test_description,
            t.category AS test_category
        FROM pruebas_paciente pp
        JOIN patients p ON pp.patient_id = p.id
        JOIN pruebas t ON pp.test_id = t.id
        ORDER BY pp.test_date DESC
    ''').fetchall()
    conn.close()
    
    pdf = FPDF(orientation='L')  # Landscape (horizontal)
    pdf.add_page()
    
    # Encabezado
    pdf.set_fill_color(34, 197, 94)  # Verde
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 20)
    pdf.cell(0, 15, 'REPORTE DETALLADO DE PRUEBAS', 0, 1, 'C', True)
    pdf.ln(10)
    
    # Información general
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f'Total de Pruebas: {len(pruebas)}', 0, 1, 'L')
    pdf.ln(5)
    
    # Tabla principal con todas las columnas
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(200, 200, 200)
    
    # Encabezados - formato horizontal permite más columnas
    pdf.cell(45, 10, 'Paciente', 1, 0, 'C', True)
    pdf.cell(40, 10, 'Prueba', 1, 0, 'C', True)
    pdf.cell(30, 10, 'Código', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Fecha Prueba', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Resultado', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Fecha Resultado', 1, 0, 'C', True)
    pdf.cell(50, 10, 'Laboratorio', 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 9)
    pdf.set_fill_color(255, 255, 255)
    
    for prueba in pruebas:
        # Verificar si necesitamos nueva página (altura disponible en landscape)
        if pdf.get_y() > 180:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 10)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(45, 10, 'Paciente', 1, 0, 'C', True)
            pdf.cell(40, 10, 'Prueba', 1, 0, 'C', True)
            pdf.cell(30, 10, 'Código', 1, 0, 'C', True)
            pdf.cell(35, 10, 'Fecha Prueba', 1, 0, 'C', True)
            pdf.cell(35, 10, 'Resultado', 1, 0, 'C', True)
            pdf.cell(35, 10, 'Fecha Resultado', 1, 0, 'C', True)
            pdf.cell(50, 10, 'Laboratorio', 1, 1, 'C', True)
            pdf.set_font('Arial', '', 9)
            pdf.set_fill_color(255, 255, 255)
        
        # Obtener valores completos sin truncar
        paciente = str(prueba['patient_name'])
        prueba_nombre = str(prueba['test_name'])
        codigo = str(prueba['test_code'])
        fecha_prueba = str(prueba['test_date'])
        resultado = str(prueba['result'])
        fecha_resultado = str(prueba['result_date'])
        laboratorio = str(prueba['laboratory'])
        
        # Calcular altura necesaria para la fila basada en el texto más largo
        lineas_paciente = max(1, (len(paciente) // 25))
        lineas_prueba = max(1, (len(prueba_nombre) // 25))
        lineas_laboratorio = max(1, (len(laboratorio) // 30))
        max_lineas = max(lineas_paciente, lineas_prueba, lineas_laboratorio, 1)
        altura_fila = max(8, max_lineas * 6)
        
        # Escribir datos - calcular altura necesaria primero
        x_inicio = pdf.get_x()
        y_inicio = pdf.get_y()
        
        # Calcular alturas necesarias para cada campo
        pdf.set_font('Arial', '', 9)
        altura_paciente = max(8, (len(paciente) // 25 + 1) * 6)
        altura_prueba = max(8, (len(prueba_nombre) // 25 + 1) * 6)
        altura_laboratorio = max(8, (len(laboratorio) // 30 + 1) * 6)
        altura_max = max(altura_paciente, altura_prueba, altura_laboratorio, 8)
        
        # Escribir cada celda con la altura máxima
        # Paciente (puede ser largo, usar multi_cell)
        pdf.set_xy(x_inicio, y_inicio)
        pdf.multi_cell(45, 6, paciente, 1, 'L', False)
        pdf.set_xy(x_inicio + 45, y_inicio)
        
        # Prueba (puede ser largo, usar multi_cell)
        pdf.multi_cell(40, 6, prueba_nombre, 1, 'L', False)
        pdf.set_xy(x_inicio + 85, y_inicio)
        
        # Código
        pdf.cell(30, altura_max, codigo, 1, 0, 'C')
        pdf.set_xy(x_inicio + 115, y_inicio)
        
        # Fecha Prueba
        pdf.cell(35, altura_max, fecha_prueba, 1, 0, 'C')
        pdf.set_xy(x_inicio + 150, y_inicio)
        
        # Resultado
        pdf.cell(35, altura_max, resultado, 1, 0, 'C')
        pdf.set_xy(x_inicio + 185, y_inicio)
        
        # Fecha Resultado
        pdf.cell(35, altura_max, fecha_resultado, 1, 0, 'C')
        pdf.set_xy(x_inicio + 220, y_inicio)
        
        # Laboratorio (puede ser largo, usar multi_cell)
        pdf.multi_cell(50, 6, laboratorio, 1, 'L', False)
        pdf.set_xy(x_inicio + 270, y_inicio)
        
        # Mover al siguiente renglón usando la altura máxima
        pdf.set_xy(10, y_inicio + altura_max)
    
    # Pie de página
    pdf.set_text_color(128, 128, 128)
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 5, f'Reporte generado el: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}', 0, 1, 'C')
    
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

@app.route('/exportar_pacientes_pdf')
def exportar_pacientes_pdf():
    """Ruta para exportar todos los pacientes en PDF"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    buffer = generar_pdf_pacientes_detallado()
    nombre_archivo = f"reporte_pacientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype='application/pdf'
    )

@app.route('/exportar_pruebas_pdf')
def exportar_pruebas_pdf():
    """Ruta para exportar todas las pruebas en PDF"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    buffer = generar_pdf_pruebas_detallado()
    nombre_archivo = f"reporte_pruebas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=True)
