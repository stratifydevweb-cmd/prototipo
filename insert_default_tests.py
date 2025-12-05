import sqlite3

def insert_default_tests():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Lista de pruebas por defecto
    default_tests = [
        ('PCR', 'PCR-001', 'Prueba PCR para detección de COVID-19', 'Molecular', 'PCR', '24-48 horas', 'Activo'),
        ('Antígeno', 'ANT-001', 'Prueba rápida de antígeno para COVID-19', 'Inmunológica', 'Inmunocromatografía', '15-30 minutos', 'Activo'),
        ('Anticuerpos', 'AC-001', 'Prueba de anticuerpos contra COVID-19', 'Serológica', 'ELISA', '24 horas', 'Activo')
    ]

    # Verificar si ya existen las pruebas
    for test in default_tests:
        existing = cursor.execute('SELECT id FROM pruebas WHERE name = ?', (test[0],)).fetchone()
        if not existing:
            cursor.execute('''
                INSERT INTO pruebas (name, code, description, category, method, duration, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', test)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    insert_default_tests()