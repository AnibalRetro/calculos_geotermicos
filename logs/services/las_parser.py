import io
from dataclasses import dataclass

import lasio
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot


class LASParserError(Exception):
    pass


@dataclass
class LASAnalysis:
    metadata: dict
    curves: list
    table_preview: list
    table_columns: list
    curve_stats: list
    depth_curve: str
    all_curve_names: list
    interpretation_lines: list
    interval_hints: list


def parse_las_file(file_path):
    try:
        las = lasio.read(file_path)
    except UnicodeDecodeError:
        with open(file_path, 'rb') as f:
            raw = f.read()
        for enc in ('latin-1', 'cp1252'):
            try:
                text = raw.decode(enc)
                las = lasio.read(io.StringIO(text))
                break
            except Exception:
                las = None
        if las is None:
            raise LASParserError('No se pudo leer el archivo por problemas de codificación.')
    except Exception as exc:
        raise LASParserError(f'Archivo inválido o no legible: {exc}') from exc

    df = las.df()
    if df.empty:
        raise LASParserError('El archivo no contiene datos numéricos para analizar.')

    depth_curve = detect_depth_curve(df)
    if depth_curve not in df.columns:
        df = df.reset_index().rename(columns={df.index.name or 'index': depth_curve})

    metadata = {
        'version': _safe_header_value(las, 'VERS', section='Version'),
        'well_name': _safe_header_value(las, 'WELL', section='Well'),
        'company': _safe_header_value(las, 'COMP', section='Well'),
        'field': _safe_header_value(las, 'FLD', section='Well'),
        'location': _safe_header_value(las, 'LOC', section='Well'),
        'start_depth': _safe_header_value(las, 'STRT', section='Well'),
        'stop_depth': _safe_header_value(las, 'STOP', section='Well'),
        'step': _safe_header_value(las, 'STEP', section='Well'),
        'null_value': _safe_header_value(las, 'NULL', section='Well'),
    }

    curves = [{'mnemonic': c.mnemonic, 'unit': c.unit, 'description': c.descr} for c in las.curves]
    table_preview = df.head(50).replace({pd.NA: None}).where(pd.notnull(df), None).to_dict('records')
    curve_stats = build_curve_stats(df)

    return LASAnalysis(
        metadata=metadata,
        curves=curves,
        table_preview=table_preview,
        table_columns=list(df.columns),
        curve_stats=curve_stats,
        depth_curve=depth_curve,
        all_curve_names=[c for c in df.columns if c != depth_curve],
        interpretation_lines=basic_interpretation(df.columns),
        interval_hints=detect_intervals(df, depth_curve),
    ), df


def _safe_header_value(las, mnemonic, section='Well'):
    try:
        value = getattr(las, section.lower())[mnemonic].value
        return value if value not in (None, '') else 'N/D'
    except Exception:
        return 'N/D'


def detect_depth_curve(df):
    for candidate in ['DEPTH', 'DEPT', 'MD']:
        if candidate in df.columns:
            return candidate
    return df.index.name if df.index.name else 'DEPTH'


def build_curve_stats(df):
    stats = []
    for col in df.columns:
        series = pd.to_numeric(df[col], errors='coerce')
        stats.append({
            'curve': col,
            'min': round(series.min(skipna=True), 4) if series.notna().any() else None,
            'max': round(series.max(skipna=True), 4) if series.notna().any() else None,
            'mean': round(series.mean(skipna=True), 4) if series.notna().any() else None,
            'std': round(series.std(skipna=True), 4) if series.notna().any() else None,
            'nulls': int(series.isna().sum()),
        })
    return stats


def basic_interpretation(columns):
    joined = {c.upper() for c in columns}
    notes = ['Esta interpretación es automática, preliminar y no sustituye un análisis petrofísico profesional.']
    if {'GR', 'GRDI', 'GAMMA RAY'} & joined:
        notes.append('GR alto sugiere lutitas/shale; GR bajo sugiere arenas o carbonatos más limpios.')
    if 'RHOB' in joined:
        notes.append('RHOB representa densidad aparente de la formación.')
    if {'NPOR', 'NPHI'} & joined:
        notes.append('NPOR/NPHI ayudan a inferir porosidad neutrón.')
    if {'RILD', 'RILM', 'RES', 'RT'} & joined:
        notes.append('Resistividad alta puede sugerir hidrocarburos o formaciones compactas.')
    if 'SP' in joined:
        notes.append('SP es útil para identificar zonas permeables.')
    if {'DTC', 'DTCM'} & joined:
        notes.append('Sónico (DTC/DTCM) ayuda a evaluar porosidad y compactación.')
    return notes


def detect_intervals(df, depth_curve):
    hints = []
    depth = pd.to_numeric(df[depth_curve], errors='coerce')
    gr_col = next((c for c in df.columns if c.upper() in ['GR', 'GRDI', 'GAMMA RAY']), None)
    res_col = next((c for c in df.columns if c.upper() in ['RILD', 'RILM', 'RES', 'RT']), None)
    por_col = next((c for c in df.columns if c.upper() in ['NPOR', 'NPHI']), None)

    if gr_col:
        gr = pd.to_numeric(df[gr_col], errors='coerce')
        low_gr = df[gr < gr.quantile(0.35)]
        if not low_gr.empty:
            hints.append(f'GR bajo en ~{low_gr[depth_curve].min():.2f} a {low_gr[depth_curve].max():.2f}.')
    if res_col:
        res = pd.to_numeric(df[res_col], errors='coerce')
        hi_res = df[res > res.quantile(0.75)]
        if not hi_res.empty:
            hints.append(f'Resistividad alta en ~{hi_res[depth_curve].min():.2f} a {hi_res[depth_curve].max():.2f}.')
    if por_col:
        por = pd.to_numeric(df[por_col], errors='coerce')
        hi_por = df[por > por.quantile(0.75)]
        if not hi_por.empty:
            hints.append(f'Porosidad relativamente alta en ~{hi_por[depth_curve].min():.2f} a {hi_por[depth_curve].max():.2f}.')
    if gr_col and res_col:
        mask = (pd.to_numeric(df[gr_col], errors='coerce') < pd.to_numeric(df[gr_col], errors='coerce').quantile(0.35)) & (
            pd.to_numeric(df[res_col], errors='coerce') > pd.to_numeric(df[res_col], errors='coerce').quantile(0.75)
        )
        combo = df[mask]
        if not combo.empty:
            hints.append(f'Combinación GR bajo + resistividad alta en ~{combo[depth_curve].min():.2f} a {combo[depth_curve].max():.2f}.')

    return hints if hints else ['No se detectaron intervalos destacados con las reglas básicas disponibles.']


def build_plot_html(df, depth_curve, selected_curves):
    charts = []
    for curve in selected_curves:
        if curve not in df.columns:
            continue
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[curve], y=df[depth_curve], mode='lines', name=curve))
        fig.update_layout(title=f'Curva {curve}', xaxis_title=curve, yaxis_title=depth_curve, height=520)
        fig.update_yaxes(autorange='reversed')
        charts.append({'curve': curve, 'html': plot(fig, output_type='div', include_plotlyjs='cdn')})
    return charts
