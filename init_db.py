import sqlite3

def create_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Crear tabla pacientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            identification_number TEXT NOT NULL,
            date_of_birth TEXT NOT NULL,
            gender TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    ''')

    # Crear tabla pruebas_paciente
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pruebas_paciente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
	        patient_id	INTEGER NOT NULL,
	        test_id	INTEGER NOT NULL,
	        test_date	TEXT NOT NULL,
	        result	TEXT NOT NULL,
	        result_date	TEXT NOT NULL,
	        laboratory	TEXT NOT NULL
        )
    ''')

    # Crear tabla usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
	        rol	TEXT NOT NULL,
	        nombre_completo	TEXT NOT NULL,
	        correo_electronico	TEXT NOT NULL,
	        nombre_usuario	TEXT NOT NULL,
	        contraseña	TEXT NOT NULL,
	        numero_telefono	TEXT NOT NULL,
	        estado  TEXT NOT NULL,
	        fecha_creacion	DATE NOT NULL
        )
    ''')

    # Crear tabla pruebas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pruebas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
	        name	TEXT NOT NULL,
	        code	TEXT NOT NULL,
	        description	TEXT NOT NULL,
	        category	TEXT NOT NULL,
	        method	TEXT NOT NULL,
	        duration	TEXT NOT NULL,
	        status	TEXT NOT NULL
        )
    ''')

    # Crear tabla informes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS informes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
	    informe	TEXT NOT NULL,
	    fecha	TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_db()
