from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import csv
from io import TextIOWrapper
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import re


app = Flask(__name__)
app.secret_key = 'cinderace'  #

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Página de inicio / login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE email = ? AND password = ?', 
                            (email, password)).fetchone()
        conn.close()

        if user:
            session['usuario_id'] = user['id']
            session['usuario_rol'] = user['rol']
            session['usuario_nombre'] = user['nombre']
            if user['rol'] == 'admin':
                return redirect(url_for('dashboard_admin'))
            else:
                return redirect(url_for('dashboard_empleado'))
        else:
            flash('Credenciales incorrectas')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        rol = request.form['rol']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO usuarios (nombre, email, password, rol) VALUES (?, ?, ?, ?)',
                         (nombre, email, password, rol))
            conn.commit()
            flash('Usuario registrado correctamente. Inicia sesión.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El correo ya está registrado.')
        finally:
            conn.close()

    return render_template('register.html')



@app.route('/admin')
def dashboard_admin():
    if 'usuario_id' not in session or session['usuario_rol'] != 'admin':
        return redirect(url_for('login'))
    return render_template('dashboard_admin.html', nombre=session['usuario_nombre'])


@app.route('/empleado')
def dashboard_empleado():
    if 'usuario_id' not in session or session['usuario_rol'] != 'empleado':
        return redirect(url_for('login'))
    return render_template('dashboard_empleado.html', nombre=session['usuario_nombre'])

# Cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/candidatos', methods=['GET', 'POST'])
def analizar_candidatos():
    import re
    candidatos = []

    if request.method == 'POST':
        archivo = request.files['archivo_csv']
        if archivo and archivo.filename.endswith('.csv'):
            try:
                archivo_stream = TextIOWrapper(archivo, encoding='utf-8')
                lector_original = csv.DictReader(archivo_stream)

                # Normalizamos los nombres de las columnas
                fieldnames_normalizadas = {k: k.strip().lower() for k in lector_original.fieldnames}
                lector = csv.DictReader(archivo_stream, fieldnames=fieldnames_normalizadas.values())

                # Reiniciamos archivo para que lea desde el principio
                archivo.stream.seek(0)
                archivo_stream = TextIOWrapper(archivo, encoding='utf-8')
                lector = csv.DictReader(archivo_stream)
                lector.fieldnames = [campo.strip().lower() for campo in lector.fieldnames]

                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()

                aptitudes_deseadas = [
                    'python', 'flask', 'django', 'html', 'css',
                    'javascript', 'sql', 'api', 'git'
                ]

                for fila in lector:
                    try:
                        # Normalizar claves
                        fila = {k.strip().lower(): v.strip() for k, v in fila.items() if v}

                        if not all(k in fila for k in ['nombre', 'email', 'experiencia', 'habilidades']):
                            print(f"⚠️ Fila incompleta, omitida: {fila}")
                            continue

                        nombre = fila['nombre']
                        email = fila['email']
                        experiencia_raw = fila['experiencia']
                        match = re.search(r'\d+', experiencia_raw)
                        experiencia = int(match.group()) if match else 0

                        habilidades = fila['habilidades'].lower()
                        habilidades_lista = [h.strip() for h in habilidades.split(',')]

                        coincidencias = sum(1 for apt in aptitudes_deseadas if apt in habilidades)

                        if experiencia >= 2 and coincidencias >= 3:
                            apto = 'Sí'
                        elif experiencia >= 1 and 1 <= coincidencias < 3:
                            apto = 'Apto con restricciones'
                        else:
                            apto = 'No'

                        cursor.execute("""
                            INSERT INTO candidatos (nombre, email, experiencia, habilidades, aptitud)
                            VALUES (?, ?, ?, ?, ?)
                        """, (nombre, email, experiencia, habilidades, apto))

                        candidatos.append({
                            'nombre': nombre,
                            'email': email,
                            'experiencia': experiencia,
                            'habilidades': habilidades,
                            'aptitud': apto
                        })

                    except Exception as e:
                        print(f"❌ Error al procesar fila: {fila} - {e}")
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"❌ Error al procesar el archivo CSV: {e}")

    return render_template('candidatos.html', candidatos=candidatos)



@app.route('/admin/asignar', methods=['GET', 'POST'])
def asignar_empleados():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        id_proyecto = request.form['id_proyecto']
        empleados = request.form.getlist('empleados')

        for id_usuario in empleados:
            cursor.execute("""
                INSERT INTO asignaciones (id_proyecto, id_usuario)
                SELECT ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM asignaciones WHERE id_proyecto = ? AND id_usuario = ?
                )
            """, (id_proyecto, id_usuario, id_proyecto, id_usuario))

        conn.commit()
        conn.close()
        return redirect('/admin/asignar')

    cursor.execute("SELECT id, nombre FROM proyectos")
    proyectos = [{'id': p[0], 'nombre': p[1]} for p in cursor.fetchall()]

    cursor.execute("SELECT id, nombre, email FROM usuarios WHERE rol = 'empleado'")
    empleados = [{'id': u[0], 'nombre': u[1], 'email': u[2]} for u in cursor.fetchall()]

    conn.close()
    return render_template('asignar_empleados.html', proyectos=proyectos, empleados=empleados)

def usuario_asignado_a_actividad(id_usuario, id_actividad):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM actividades a
        JOIN asignaciones asig ON a.id_proyecto = asig.id_proyecto
        WHERE a.id = ? AND asig.id_usuario = ?
    """, (id_actividad, id_usuario))
    resultado = cursor.fetchone()
    conn.close()
    return resultado is not None

@app.route('/admin/proyectos', methods=['GET', 'POST'])
def admin_proyectos():
    conn = get_db_connection()
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        descripcion = request.form['descripcion'].strip()
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']

        # Validaciones simples
        if not nombre or not fecha_inicio or not fecha_fin:
            flash('Por favor, completa todos los campos obligatorios.', 'danger')
        else:
            try:
                # Validar que fecha_inicio <= fecha_fin
                fi = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                ff = datetime.strptime(fecha_fin, '%Y-%m-%d')
                if fi > ff:
                    flash('La fecha de inicio no puede ser mayor que la fecha de fin.', 'danger')
                else:
                    conn.execute(
                        'INSERT INTO proyectos (nombre, descripcion, fecha_inicio, fecha_fin) VALUES (?, ?, ?, ?)',
                        (nombre, descripcion, fecha_inicio, fecha_fin)
                    )
                    conn.commit()
                    flash('Proyecto creado correctamente.', 'success')
                    return redirect(url_for('admin_proyectos'))
            except ValueError:
                flash('Formato de fecha inválido.', 'danger')
    proyectos = conn.execute('SELECT * FROM proyectos ORDER BY fecha_inicio DESC').fetchall()
    conn.close()
    return render_template('admin_proyectos.html', proyectos=proyectos)

@app.route('/api/actividades/<int:id_proyecto>')
def api_actividades(id_proyecto):
    conn = get_db_connection()
    actividades = conn.execute(
        'SELECT id, nombre FROM actividades WHERE id_proyecto = ?', (id_proyecto,)
    ).fetchall()
    conn.close()
    return [{'id': a['id'], 'nombre': a['nombre']} for a in actividades]

@app.route('/empleado/registrar-avance', methods=['GET', 'POST'])
def registrar_avance_empleado():
    if request.method == 'POST':
        id_proyecto = request.form['id_proyecto']
        actividad = request.form['actividad']
        semana = request.form['semana']
        descripcion = request.form['descripcion']
        fecha = request.form['fecha']
        id_usuario = session.get('usuario_id')  # Asegúrate de que el ID del usuario esté en sesión

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO avances (id_proyecto, actividad, id_usuario, semana, descripcion, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_proyecto, actividad, id_usuario, semana, descripcion, fecha))

        conn.commit()
        conn.close()
        return redirect('/empleado/registrar-avance')

    # GET request - Mostrar formulario
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM proyectos")
    proyectos = cursor.fetchall()
    conn.close()
    return render_template('registrar_avance.html', proyectos=proyectos)



@app.route('/admin/ver-avances')
def ver_avances():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            a.id,
            p.nombre AS proyecto,
            a.actividad,
            u.nombre AS usuario,
            a.semana,
            a.descripcion,
            a.fecha
        FROM avances a
        JOIN usuarios u ON a.id_usuario = u.id
        JOIN proyectos p ON a.id_proyecto = p.id
        ORDER BY a.fecha DESC
    """)
    avances = cursor.fetchall()

    cursor.execute("SELECT id, nombre FROM proyectos")
    proyectos = cursor.fetchall()
    cursor.execute("SELECT id, nombre, email FROM usuarios WHERE rol = 'empleado'")
    empleados = cursor.fetchall()
    conn.close()

    return render_template('ver_avances.html', avances=avances, proyectos=proyectos, empleados=empleados)


if __name__ == '__main__':
    app.run(debug=True)
