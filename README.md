# Sistema de Gestión de Pacientes y Pruebas de Laboratorio

## 📋 Descripción del Proyecto

Este es un sistema web desarrollado en Flask (Python) para la gestión de pacientes, pruebas médicas de laboratorio, usuarios e informes. Permite registrar, editar, eliminar y consultar información sobre pacientes y sus pruebas médicas, así como generar reportes en diferentes formatos.

## 🏗️ Estructura del Proyecto

```
prototipo/
├── app.py                 # Aplicación Flask principal
├── init_db.py            # Script para inicializar la base de datos
├── database.db           # Base de datos SQLite
├── requirements.txt      # Dependencias de Python
├── static/
│   ├── styles.css        # Estilos CSS
│   └── script.js         # Scripts JavaScript
└── templates/            # Plantillas HTML
    ├── login.html
    ├── admin.html
    ├── pacientes.html
    ├── pruebas.html
    ├── pruebas_paciente.html
    ├── usuarios.html
    ├── informes.html
    └── ...
```

## 🛠️ Requisitos Previos

Antes de ejecutar el proyecto, necesitas tener instalado:

1. **Python 3.7 o superior**
   - Verifica con: `python --version` o `python3 --version`
   - Descarga desde: https://www.python.org/downloads/

2. **pip** (gestor de paquetes de Python)
   - Generalmente viene con Python

## 📦 Instalación

### Paso 1: Instalar las dependencias

Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
pip install -r requirements.txt
```

O si usas Python 3 específicamente:

```bash
pip3 install -r requirements.txt
```

Esto instalará:
- Flask (framework web)
- pandas (manipulación de datos)
- xlsxwriter y openpyxl (generación de archivos Excel)
- fpdf2 (generación de PDFs)
- Werkzeug (utilidades de seguridad)

### Paso 2: Inicializar la base de datos

Ejecuta el script de inicialización:

```bash
python init_db.py
```

O:

```bash
python3 init_db.py
```

Esto creará la base de datos `database.db` con todas las tablas necesarias:
- `patients` (pacientes)
- `pruebas` (pruebas médicas)
- `pruebas_paciente` (asignación de pruebas a pacientes)
- `usuarios` (usuarios del sistema)
- `informes` (informes generados)

## 🚀 Ejecutar la Aplicación

### Opción 1: Desde la terminal

1. Abre una terminal en la carpeta `prototipo`
2. Ejecuta:

```bash
python app.py
```

O:

```bash
python3 app.py
```

3. Deberías ver un mensaje similar a:
   ```
   * Running on http://127.0.0.1:5000
   ```

### Opción 2: Acceso a la aplicación

1. Abre tu navegador web
2. Ve a la dirección: **http://127.0.0.1:5000**

## 🔐 Credenciales de Acceso

- **Usuario**: `admin`
- **Contraseña**: `adminarthu`

## 📱 Funcionalidades del Sistema

### 1. **Gestión de Pacientes**
   - Crear, editar y eliminar pacientes
   - Buscar pacientes por nombre
   - Campos: nombre, número de identificación, fecha de nacimiento, género, dirección, teléfono

### 2. **Gestión de Pruebas Médicas**
   - Crear, editar y eliminar pruebas
   - Campos: nombre, código, descripción, categoría, método, duración, estado
   - Búsqueda por nombre

### 3. **Asignación de Pruebas a Pacientes**
   - Asignar pruebas a pacientes específicos
   - Registrar resultados, fechas y laboratorio
   - Editar y eliminar asignaciones

### 4. **Gestión de Usuarios**
   - Crear, editar y eliminar usuarios
   - Campos: rol, nombre completo, correo, usuario, contraseña, teléfono, estado
   - Búsqueda por nombre completo

### 5. **Informes y Reportes**
   - Vista general con estadísticas
   - Informes detallados con búsqueda
   - Exportación a Excel, CSV y PDF

### 6. **Consulta de Información**
   - Búsqueda de pacientes y sus pruebas
   - Exportación de resultados en PDF

## 🌐 Rutas Principales

- `/` - Redirección automática (login si no hay sesión, admin si hay sesión)
- `/login` - Página de inicio de sesión
- `/admin` - Panel de control principal
- `/pacientes` - Gestión de pacientes
- `/pruebas` - Gestión de pruebas médicas
- `/pruebas_paciente` - Asignación de pruebas
- `/usuarios` - Gestión de usuarios
- `/informes` - Informes generales
- `/informes/detalle` - Informes detallados
- `/informacion` - Consulta pública de información

## ⚠️ Errores Corregidos

Se corrigieron los siguientes errores en el código:

1. ✅ Variable `conn` no inicializada en la función `informes()`
2. ✅ Faltaba importar `StringIO` desde `io`
3. ✅ Faltaba importar `send_file` desde `flask`
4. ✅ Paréntesis sin cerrar en la creación de la tabla `informes`
5. ✅ Importaciones duplicadas de Flask

## 🔧 Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'flask'"
**Solución**: Ejecuta `pip install -r requirements.txt`

### Error: "sqlite3.OperationalError: no such table"
**Solución**: Ejecuta `python init_db.py` para crear las tablas

### Error al generar PDFs o Excel
**Solución**: Verifica que todas las dependencias estén instaladas correctamente

### Puerto 5000 ocupado
**Solución**: En `app.py`, cambia el puerto modificando la última línea:
```python
app.run(debug=True, port=5001)
```

## 📝 Notas Importantes

- El sistema usa **sesiones** para la autenticación
- La clave secreta está configurada como `'your_secret_key'` (cámbiala en producción)
- La base de datos es SQLite (no requiere servidor de base de datos)
- El modo debug está activado (desactívalo en producción)

## 🔒 Seguridad

⚠️ **Importante para producción**:
- Cambia `app.secret_key` por una clave secreta segura
- Implementa hash de contraseñas para usuarios
- Considera usar HTTPS
- Valida y sanitiza todas las entradas del usuario
- Desactiva el modo debug (`debug=False`)

## 📞 Soporte

Si encuentras problemas, verifica:
1. Que Python esté correctamente instalado
2. Que todas las dependencias estén instaladas
3. Que la base de datos esté inicializada
4. Que no haya otros servicios usando el puerto 5000

