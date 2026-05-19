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
    intervals_table: list
    warnings: list
    parser_type: str
    units: dict


def parse_las_file(uploaded_file):
    """Parser principal con fallback tabular."""
    try:
        parsed = parse_standard_lasio(uploaded_file)
    except LASParserError as exc:
        if 'No ~ sections found' in str(exc):
            parsed = parse_tabular_las(uploaded_file)
            parsed['warnings'].append('Este archivo no es LAS estándar; se leyó como tabla tabulada.')
        else:
            raise

    return build_analysis_output(parsed)


def parse_standard_lasio(uploaded_file):
    las = _read_las_with_fallback_encoding(uploaded_file)
    df = las.df()
    if df.empty:
        raise LASParserError('El archivo no contiene datos numéricos para analizar.')

    depth_curve = detect_depth_curve(df.columns)
    if not depth_curve:
        if df.index.name:
            depth_curve = df.index.name
            df = df.reset_index()
        else:
            raise LASParserError('No se encontró curva de profundidad')
    elif depth_curve not in df.columns:
        df = df.reset_index().rename(columns={df.index.name or 'index': depth_curve})

    df = coerce_numeric_dataframe(df)
    numeric_cols = [c for c in df.columns if c != depth_curve and pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().any()]
    if not numeric_cols:
        raise LASParserError('No se encontraron curvas numéricas para graficar')

    units = {c.mnemonic: (c.unit or '') for c in las.curves}
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
    curves = [
        {'mnemonic': c.mnemonic, 'unit': c.unit, 'description': c.descr or infer_curve_description(c.mnemonic)}
        for c in las.curves
    ]
    return {
        'metadata': metadata,
        'curves': curves,
        'dataframe': df,
        'depth_column': depth_curve,
        'units': units,
        'warnings': [],
        'parser_type': 'standard_lasio',
    }


def parse_tabular_las(uploaded_file):
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    text = _decode_bytes(raw)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        raise LASParserError('El archivo tabular no tiene suficientes datos')

    separator = '\t' if '\t' in lines[0] else None

    units_df = pd.read_csv(io.StringIO(text), sep=separator, header=None, nrows=2, engine='python')
    headers = [str(v).strip() for v in units_df.iloc[0].tolist()]
    units_row = [str(v).strip() for v in units_df.iloc[1].tolist()]
    units = {headers[i]: units_row[i] if i < len(units_row) else '' for i in range(len(headers))}

    df = pd.read_csv(io.StringIO(text), sep=separator, header=0, skiprows=[1], engine='python')
    df.columns = [str(c).strip() for c in df.columns]
    df = coerce_numeric_dataframe(df)
    df = df.dropna(how='all')

    depth_curve = detect_depth_curve(df.columns)
    if not depth_curve:
        raise LASParserError('No se encontró curva de profundidad')

    numeric_cols = [c for c in df.columns if c != depth_curve and pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().any()]
    if not numeric_cols:
        raise LASParserError('No se encontraron curvas numéricas para graficar')

    curves = [
        {'mnemonic': col, 'unit': units.get(col, ''), 'description': infer_curve_description(col)}
        for col in df.columns
    ]
    metadata = {
        'version': 'N/D (tabular)',
        'well_name': 'N/D',
        'company': 'N/D',
        'field': 'N/D',
        'location': 'N/D',
        'start_depth': df[depth_curve].min(skipna=True),
        'stop_depth': df[depth_curve].max(skipna=True),
        'step': 'N/D',
        'null_value': 'N/D',
    }

    return {
        'metadata': metadata,
        'curves': curves,
        'dataframe': df,
        'depth_column': depth_curve,
        'units': units,
        'warnings': [],
        'parser_type': 'tabular_fallback',
    }


def build_analysis_output(parsed):
    df = parsed['dataframe']
    depth_curve = parsed['depth_column']
    units = parsed['units']

    curve_stats = build_curve_stats(df)
    interval_summary, intervals_table = detect_intervals(df, depth_curve)

    analysis = LASAnalysis(
        metadata=parsed['metadata'],
        curves=parsed['curves'],
        table_preview=df.head(50).where(pd.notnull(df), None).to_dict('records'),
        table_columns=list(df.columns),
        curve_stats=curve_stats,
        depth_curve=depth_curve,
        all_curve_names=[c for c in df.columns if c != depth_curve],
        interpretation_lines=basic_interpretation(df),
        interval_hints=interval_summary,
        intervals_table=intervals_table,
        warnings=parsed['warnings'],
        parser_type=parsed['parser_type'],
        units=units,
    )
    return analysis, df


def _read_las_with_fallback_encoding(file_path):
    try:
        return lasio.read(file_path)
    except UnicodeDecodeError:
        with open(file_path, 'rb') as f:
            raw = f.read()
        for enc in ('utf-8', 'latin-1', 'cp1252'):
            try:
                return lasio.read(io.StringIO(raw.decode(enc)))
            except Exception:
                continue
        raise LASParserError('No se pudo leer el archivo por problemas de codificación.')
    except Exception as exc:
        raise LASParserError(f'Archivo inválido o no legible: {exc}') from exc


def _decode_bytes(raw):
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('latin-1')


def _safe_header_value(las, mnemonic, section='Well'):
    try:
        value = getattr(las, section.lower())[mnemonic].value
        return value if value not in (None, '') else 'N/D'
    except Exception:
        return 'N/D'


def detect_depth_curve(columns):
    cols = list(columns)
    for candidate in ['DEPTH', 'DEPT', 'MD']:
        if candidate in cols:
            return candidate
    return None


def coerce_numeric_dataframe(df):
    out = df.copy()
    for col in out.columns:
        out[col] = pd.to_numeric(out[col], errors='coerce')
    return out


def infer_curve_description(mnemonic):
    m = mnemonic.upper()
    mapping = {
        'DEPTH': 'Profundidad',
        'DEPT': 'Profundidad',
        'MD': 'Profundidad medida',
        'DTCM': 'Sónico',
        'SPOR': 'Porosidad sónica',
        'GRDI': 'Gamma Ray',
        'RILD': 'Resistividad profunda',
        'RILM': 'Resistividad media',
        'RSFE': 'Resistividad somera',
        'SP': 'Potencial espontáneo',
        'PEDN': 'Factor fotoeléctrico',
        'NPOR': 'Porosidad neutrón',
        'RHOB': 'Densidad bulk',
        'DPOR': 'Porosidad por densidad',
    }
    return mapping.get(m, 'Curva de registro')


def build_curve_stats(df):
    stats = []
    for col in df.columns:
        series = pd.to_numeric(df[col], errors='coerce')
        stats.append({'curve': col, 'min': _r(series.min()), 'max': _r(series.max()), 'mean': _r(series.mean()), 'std': _r(series.std()), 'nulls': int(series.isna().sum())})
    return stats


def _r(value):
    return round(float(value), 4) if pd.notna(value) else None


def basic_interpretation(df):
    cols = {c.upper() for c in df.columns}
    notes = ['Esta interpretación es automática, preliminar y no sustituye un análisis petrofísico profesional.']
    if 'GRDI' in cols:
        notes.append('GRDI alto: posible lutita/shale. GRDI bajo: posible arena limpia o carbonato.')
    if 'RILD' in cols:
        notes.append('RILD alto: posible zona resistiva, compacta o con hidrocarburos.')
    if 'NPOR' in cols:
        notes.append('NPOR alto: posible mayor porosidad.')
    if 'RHOB' in cols:
        notes.append('RHOB bajo: posible mayor porosidad.')
    if 'SP' in cols:
        notes.append('SP con deflexiones: posible zona permeable.')
    return notes


def detect_intervals(df, depth_curve):
    intervals = []
    summary = []
    depth = pd.to_numeric(df[depth_curve], errors='coerce')

    conditions = {}
    if 'GRDI' in df.columns:
        gr = pd.to_numeric(df['GRDI'], errors='coerce')
        conditions['GRDI bajo'] = gr <= gr.quantile(0.30)
    if 'RILD' in df.columns:
        rild = pd.to_numeric(df['RILD'], errors='coerce')
        conditions['RILD alto'] = rild >= rild.quantile(0.70)
    if 'NPOR' in df.columns:
        npor = pd.to_numeric(df['NPOR'], errors='coerce')
        conditions['NPOR alto'] = npor >= npor.quantile(0.70)
    if 'RHOB' in df.columns:
        rhob = pd.to_numeric(df['RHOB'], errors='coerce')
        conditions['RHOB bajo'] = rhob <= rhob.quantile(0.30)

    for label, mask in conditions.items():
        intervals.extend(group_intervals(df, depth_curve, mask, [label]))

    if all(k in conditions for k in ['GRDI bajo', 'RILD alto', 'NPOR alto']):
        combo_mask = conditions['GRDI bajo'] & conditions['RILD alto'] & conditions['NPOR alto']
        intervals.extend(group_intervals(df, depth_curve, combo_mask, ['GRDI bajo', 'RILD alto', 'NPOR alto']))

    if intervals:
        summary.append(f'Se detectaron {len(intervals)} intervalos de interés con reglas básicas.')
    else:
        summary.append('No se detectaron intervalos destacados con las reglas básicas disponibles.')
    return summary, intervals


def group_intervals(df, depth_curve, mask, tags):
    rows = df[mask.fillna(False)].copy()
    if rows.empty:
        return []
    rows = rows[[depth_curve]].dropna().sort_values(depth_curve)
    if rows.empty:
        return []
    depths = rows[depth_curve].tolist()
    intervals = []
    start = prev = depths[0]
    step = max((depths[-1] - depths[0]) / max(len(depths), 1), 0.0001)
    threshold = step * 2.5

    for d in depths[1:]:
        if (d - prev) > threshold:
            intervals.append({'start_depth': _r(start), 'end_depth': _r(prev), 'conditions': ', '.join(tags)})
            start = d
        prev = d
    intervals.append({'start_depth': _r(start), 'end_depth': _r(prev), 'conditions': ', '.join(tags)})
    return intervals


def build_plot_html(df, depth_curve, selected_curves, units=None):
    units = units or {}
    charts = []
    depth_unit = (units.get(depth_curve, '') or '').lower()
    y_title = 'Depth (ft)' if depth_unit == 'ft' else depth_curve
    for curve in selected_curves:
        if curve not in df.columns:
            continue
        x_title = f"{curve} ({units.get(curve, '')})" if units.get(curve) else curve
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[curve], y=df[depth_curve], mode='lines', name=curve))
        fig.update_layout(title=f'Curva {curve}', xaxis_title=x_title, yaxis_title=y_title, height=520)
        fig.update_yaxes(autorange='reversed')
        charts.append({'curve': curve, 'html': plot(fig, output_type='div', include_plotlyjs='cdn')})
    return charts
