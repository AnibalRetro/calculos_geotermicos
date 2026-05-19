from django.contrib import messages
from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import LASUploadForm
from .models import UploadedLAS
from .services.las_parser import LASParserError, build_plot_html, parse_las_file


def upload_view(request):
    files = []
    db_ready = True
    try:
        files = list(UploadedLAS.objects.order_by('-uploaded_at'))
    except (OperationalError, ProgrammingError):
        db_ready = False
        messages.warning(
            request,
            'La base de datos aún no está inicializada. Ejecuta: python manage.py migrate',
        )
    if request.method == 'POST':
        form = LASUploadForm(request.POST, request.FILES)
        if form.is_valid():
            if not db_ready:
                messages.error(request, 'No se puede cargar el archivo hasta ejecutar migraciones.')
                return render(request, 'logs/upload.html', {'form': form, 'files': files})
            uploaded = form.cleaned_data['las_file']
            obj = UploadedLAS.objects.create(file=uploaded, original_name=uploaded.name)
            return redirect('analysis', file_id=obj.id)
    else:
        form = LASUploadForm()
    return render(request, 'logs/upload.html', {'form': form, 'files': files})


def analysis_view(request, file_id):
    record = get_object_or_404(UploadedLAS, id=file_id)
    try:
        analysis, df = parse_las_file(record.file.path)
    except LASParserError as exc:
        messages.error(request, str(exc))
        return redirect('upload')

    selected_curves = request.POST.getlist('curves') if request.method == 'POST' else analysis.all_curve_names[:3]
    charts = build_plot_html(df, analysis.depth_curve, selected_curves)

    context = {
        'record': record,
        'analysis': analysis,
        'selected_curves': selected_curves,
        'charts': charts,
    }
    return render(request, 'logs/analysis.html', context)
