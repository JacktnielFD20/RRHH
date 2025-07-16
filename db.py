import sqlite3

def crear_base_datos():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.executescript("""
    -- Tabla de usuarios
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol TEXT NOT NULL CHECK(rol IN ('admin', 'empleado'))
    );

    -- Tabla de proyectos
    CREATE TABLE IF NOT EXISTS proyectos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        fecha_inicio TEXT,
        fecha_fin TEXT
    );

    -- Tabla de actividades (relacionadas con un proyecto)
    CREATE TABLE IF NOT EXISTS actividades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_proyecto INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        estado TEXT CHECK(estado IN ('pendiente', 'en curso', 'completada')) DEFAULT 'pendiente',
        FOREIGN KEY(id_proyecto) REFERENCES proyectos(id)
    );

CREATE TABLE avances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actividad TEXT NOT NULL,  -- Ahora es texto libre
    id_usuario INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    semana TEXT NOT NULL,
    fecha TEXT DEFAULT CURRENT_DATE,
    FOREIGN KEY(id_usuario) REFERENCES usuarios(id)
);

    -- Tabla de candidatos (para análisis desde archivo CSV)
    CREATE TABLE IF NOT EXISTS candidatos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL,
        experiencia INTEGER,
        habilidades TEXT,
        aptitud TEXT
    );
    -- Tabla de asignaciones de empleados a proyectos
CREATE TABLE IF NOT EXISTS asignaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_proyecto INTEGER NOT NULL,
    id_usuario INTEGER NOT NULL,
    FOREIGN KEY(id_proyecto) REFERENCES proyectos(id),
    FOREIGN KEY(id_usuario) REFERENCES usuarios(id)
);

    """)

    conn.commit()
    conn.close()
    print("✅ Base de datos 'database.db' creada correctamente.")

if __name__ == '__main__':
    crear_base_datos()
