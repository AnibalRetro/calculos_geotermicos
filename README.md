# Calculadora Geotérmica y Visor LAS (Django)

Proyecto académico gratuito para apoyar a estudiantes de **ingeniería petroquímica, geofísica y geotérmica** con análisis de registros de pozo y visualización técnica de archivos LAS.

**Desarrollado por Make IT Group en sociedad con la Asociación Mexicana de Ingeniería.**

---

## ¿Qué hace este repositorio?

Este sistema web (Django) permite cargar archivos `.las`, interpretarlos automáticamente y mostrar resultados técnicos en paneles de análisis.

### Flujo funcional

1. **Carga de archivo LAS**
   - Vista principal (`upload_view`) con formulario de subida.
   - Guarda archivo en base de datos/modelo `UploadedLAS`.

2. **Parsing robusto del archivo**
   - Parser principal con `lasio` para LAS estándar.
   - Fallback para LAS tabulares cuando el archivo no cumple secciones `~` estándar.
   - Detección automática de curva de profundidad (`DEPTH`, `DEPT`, `MD`).

3. **Procesamiento y análisis**
   - Conversión de columnas a numérico.
   - Estadísticas básicas por curva (mín, máx, media, desviación, nulos).
   - Interpretación preliminar e identificación de intervalos de interés.

4. **Visualización**
   - Gráficas interactivas por curva con Plotly.
   - Tabla de primeros 50 registros.
   - Panel de metadatos y catálogo de curvas.

---

## Estructura principal

- `logs/views.py`: flujo de carga y vista de análisis.
- `logs/services/las_parser.py`: lectura, limpieza, estadísticas, interpretación y detección de intervalos.
- `logs/forms.py`: validación de archivos cargados.
- `logs/templates/logs/`: interfaz HTML de carga y análisis.
- `logs/static/logs/styles.css`: estilos de la aplicación.
- `index.html`: landing informativa institucional del proyecto.

---

## Instalación y ejecución local

1. Crear y activar entorno virtual:
   - Linux/macOS:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecutar migraciones:
   ```bash
   python manage.py migrate
   ```

4. Levantar servidor:
   ```bash
   python manage.py runserver
   ```

5. Abrir:
   - App Django: `http://127.0.0.1:8000/`
   - Landing institucional (archivo estático): abre `index.html` en el navegador.

---

## Notas

- La interpretación técnica es orientativa y no sustituye un estudio profesional integral.
- Si aparece `no such table: logs_uploadedlas`, ejecuta `python manage.py migrate`.

- Creado y desarrollado por Anibal Arenas - We don't try it, We Make IT
