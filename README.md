# LAS Viewer (Django)

Aplicación local para cargar, visualizar e interpretar archivos `.las` de registros de pozo.

## Características
- Carga de archivos LAS con validación de extensión.
- Lectura y parseo con `lasio`.
- Visualización de metadatos de pozo y listado completo de curvas.
- Vista tabular de los primeros 50 registros con `pandas`.
- Selección de curvas y gráficas interactivas con `plotly` (profundidad invertida en Y).
- Estadísticas básicas por curva.
- Interpretación petrofísica preliminar e intervalos de interés automáticos.
- Soporte para múltiples archivos cargados y análisis separados.

## Instalación y ejecución
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
4. Correr servidor local:
   ```bash
   python manage.py runserver
   ```
5. Abrir en navegador: `http://127.0.0.1:8000/`

## Estructura
- `logs/services/las_parser.py`: lógica central de lectura, estadísticas, interpretación e intervalos.
- `logs/forms.py`: validaciones de carga.
- `logs/views.py`: vistas de carga y análisis.
- `logs/templates/logs/`: UI de carga y análisis.
- `logs/static/logs/styles.css`: estilos simples y responsivos.

## Notas
- Los archivos se guardan en `media/las_files/` para permitir análisis posteriores locales.
- La interpretación es automática y orientativa; no sustituye un análisis profesional.

## Solución de problemas
- Error `no such table: logs_uploadedlas`: la BD no tiene migraciones aplicadas. Ejecuta:
  ```bash
  python manage.py migrate
  ```
- Si abriste el servidor antes de migrar, detenlo y vuelve a ejecutar `python manage.py runserver`.

- La carpeta `media/las_files/` viene inicializada en el repositorio (`.gitkeep`) y Django creará/gestionará archivos ahí al cargar LAS.
