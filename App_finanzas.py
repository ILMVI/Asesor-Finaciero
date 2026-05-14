"""
Asesor Financiero PREMIUM v6 — Fix definitivo de inputs:
- Fondo oscuro translúcido en TODOS los inputs (login y sidebar)
- Texto blanco visible
- Sin afectar el resto de la app
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, date
from pathlib import Path
from streamlit_echarts import st_echarts
from scipy.optimize import linprog
from io import BytesIO

# Para PDF
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                  TableStyle, PageBreak, Image as RLImage,
                                  KeepTogether)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Circle, Rect, String, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.legends import Legend

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

st.set_page_config(
    page_title="Asesor Financiero Premium",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================
# DB CON SOPORTE MULTI-USUARIO
# =====================================================
HOME_DIR = Path.home()
APP_DATA_DIR = HOME_DIR / ".asesor_financiero"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(APP_DATA_DIR / "finanzas.db")


def get_conn():
    return sqlite3.connect(DB_PATH, timeout=10)


def init_db():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS registros_personal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL DEFAULT 'default',
                fecha TEXT NOT NULL,
                mes_periodo TEXT NOT NULL,
                ingreso REAL,
                alquiler REAL, luz REAL, internet REAL,
                comida REAL, transporte REAL, salidas REAL,
                cafe_diario REAL, suscripciones REAL,
                comisiones_banco REAL, delivery REAL, impulsivos REAL,
                UNIQUE(usuario, mes_periodo)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                nombre TEXT PRIMARY KEY,
                fecha_registro TEXT,
                ultima_sesion TEXT
            )
        """)
        conn.commit()
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)


def registrar_usuario(nombre):
    try:
        conn = get_conn()
        cur = conn.cursor()
        ahora = datetime.now().isoformat()
        cur.execute("""
            INSERT INTO usuarios (nombre, fecha_registro, ultima_sesion)
            VALUES (?, ?, ?)
            ON CONFLICT(nombre) DO UPDATE SET ultima_sesion=excluded.ultima_sesion
        """, (nombre, ahora, ahora))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def listar_usuarios():
    try:
        conn = get_conn()
        df = pd.read_sql_query("SELECT nombre, ultima_sesion FROM usuarios ORDER BY ultima_sesion DESC", conn)
        conn.close()
        return df["nombre"].tolist() if not df.empty else []
    except Exception:
        return []


def guardar_personal(usuario, datos):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO registros_personal
            (usuario, fecha, mes_periodo, ingreso, alquiler, luz, internet, comida, transporte, salidas,
             cafe_diario, suscripciones, comisiones_banco, delivery, impulsivos)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(usuario, mes_periodo) DO UPDATE SET
                fecha=excluded.fecha, ingreso=excluded.ingreso, alquiler=excluded.alquiler,
                luz=excluded.luz, internet=excluded.internet, comida=excluded.comida,
                transporte=excluded.transporte, salidas=excluded.salidas,
                cafe_diario=excluded.cafe_diario, suscripciones=excluded.suscripciones,
                comisiones_banco=excluded.comisiones_banco, delivery=excluded.delivery,
                impulsivos=excluded.impulsivos
        """, (usuario,) + datos)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        return False


def cargar_historico(usuario):
    try:
        conn = get_conn()
        df = pd.read_sql_query(
            "SELECT * FROM registros_personal WHERE usuario=? ORDER BY mes_periodo",
            conn, params=(usuario,))
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def borrar_registro(usuario, mes_periodo):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM registros_personal WHERE usuario=? AND mes_periodo=?",
                    (usuario, mes_periodo))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


ok, err = init_db()
if not ok:
    st.error(f"DB Error: {err}")
    st.stop()

# =====================================================
# CSS GLOBAL DE INPUTS — APLICA EN LOGIN Y APP PRINCIPAL
# =====================================================
GLOBAL_INPUT_CSS = """
<style>
/* ===== FIX UNIVERSAL DE INPUTS ===== */
/* Fondo OSCURO translúcido + texto blanco. Aplica en TODA la app */

.stApp input,
.stApp input[type="text"],
.stApp input[type="password"],
.stApp input[type="number"] {
    background: rgba(20, 20, 35, 0.7) !important;
    background-color: rgba(20, 20, 35, 0.7) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    caret-color: #ffffff !important;
}

.stApp [data-baseweb="input"] {
    background: rgba(20, 20, 35, 0.7) !important;
    background-color: rgba(20, 20, 35, 0.7) !important;
}
.stApp [data-baseweb="input"] > div {
    background: transparent !important;
    background-color: transparent !important;
}

.stApp [data-testid="stNumberInput"] > div > div {
    background: rgba(20, 20, 35, 0.7) !important;
    background-color: rgba(20, 20, 35, 0.7) !important;
}

.stApp input::placeholder {
    color: rgba(255,255,255,0.4) !important;
    -webkit-text-fill-color: rgba(255,255,255,0.4) !important;
    opacity: 1 !important;
}

.stApp input[type="text"] {
    border: 1px solid rgba(167,139,250,0.4) !important;
    border-radius: 10px !important;
    padding: 12px !important;
    font-size: 16px !important;
}

.stApp [data-baseweb="select"] > div {
    background: rgba(20, 20, 35, 0.7) !important;
    background-color: rgba(20, 20, 35, 0.7) !important;
    border: 1px solid rgba(167,139,250,0.4) !important;
    border-radius: 10px !important;
}
.stApp [data-baseweb="select"] *,
.stApp [data-baseweb="select"] span {
    color: white !important;
    -webkit-text-fill-color: white !important;
}

[role="radiogroup"] label,
[role="radiogroup"] label * {
    color: white !important;
}
</style>
"""

# =====================================================
# PANTALLA DE LOGIN
# =====================================================
if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None

if not st.session_state.usuario_actual:
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #2d2410 100%);
        background-attachment: fixed;
    }
    header[data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .login-card {
        background: rgba(124,58,237,0.08);
        backdrop-filter: blur(30px);
        border: 1px solid rgba(167,139,250,0.3);
        border-radius: 20px;
        padding: 40px;
        max-width: 500px;
        margin: 50px auto;
        box-shadow: 0 20px 60px rgba(124,58,237,0.2);
        text-align: center;
    }
    .login-title {
        font-size: 42px;
        font-weight: 800;
        background: linear-gradient(135deg, #7c3aed, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }
    .login-subtitle {
        color: rgba(255,255,255,0.7);
        font-size: 14px;
        letter-spacing: 1px;
        margin-bottom: 30px;
    }
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #a78bfa) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px 28px !important;
        font-weight: 700 !important;
        width: 100%;
    }
    label { color: rgba(255,255,255,0.85) !important; }
    </style>
    """, unsafe_allow_html=True)

    # CSS UNIVERSAL DE INPUTS — también aplica en login
    st.markdown(GLOBAL_INPUT_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; padding-top: 40px;">
        <div class="login-title">◆ Asesor Financiero Premium</div>
        <div class="login-subtitle">INGENIERÍA FINANCIERA · ANÁLISIS PREDICTIVO</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<h3 style="color: white; margin-top: 0;">👤 Identifícate</h3>', unsafe_allow_html=True)
        st.markdown('<p style="color: rgba(255,255,255,0.7); font-size: 13px;">Cada usuario tiene su histórico privado y separado.</p>', unsafe_allow_html=True)

        usuarios_existentes = listar_usuarios()

        modo_login = st.radio("", ["🔐 Soy usuario existente", "✨ Soy nuevo"], horizontal=True,
                              label_visibility="collapsed")

        if modo_login == "🔐 Soy usuario existente":
            if usuarios_existentes:
                usuario_seleccionado = st.selectbox("Selecciona tu perfil:", usuarios_existentes)
                if st.button("🚀 Entrar"):
                    registrar_usuario(usuario_seleccionado)
                    st.session_state.usuario_actual = usuario_seleccionado
                    st.rerun()
            else:
                st.info("No hay usuarios registrados aún. Crea uno nuevo.")
        else:
            nuevo_usuario = st.text_input("Tu nombre o nickname:",
                                           placeholder="Ej: Mauricio, Juan_Perez, etc.")
            if st.button("✨ Crear perfil y entrar"):
                if nuevo_usuario.strip():
                    nuevo_usuario_clean = nuevo_usuario.strip()
                    if nuevo_usuario_clean in usuarios_existentes:
                        st.error("Ese nombre ya existe. Inicia sesión con la opción anterior.")
                    else:
                        registrar_usuario(nuevo_usuario_clean)
                        st.session_state.usuario_actual = nuevo_usuario_clean
                        st.rerun()
                else:
                    st.warning("Ingresa un nombre.")

        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

USUARIO = st.session_state.usuario_actual

# =====================================================
# SCORE
# =====================================================
def calcular_score(ingreso, gastos_fijos, gastos_var, hormiga, restante):
    if ingreso <= 0:
        return 0
    pct_ahorro = (restante / ingreso) * 100
    pct_fijos = (gastos_fijos / ingreso) * 100
    pct_var = (gastos_var / ingreso) * 100
    pct_hormiga = (hormiga / ingreso) * 100

    if pct_ahorro >= 20:
        f_ahorro = 35
    elif pct_ahorro >= 10:
        f_ahorro = 35 * (pct_ahorro / 20)
    elif pct_ahorro >= 0:
        f_ahorro = 15 * (pct_ahorro / 10)
    else:
        f_ahorro = 0

    f_fijos = 25 if pct_fijos <= 50 else (25 * (1 - (pct_fijos - 50) / 20) if pct_fijos <= 70 else 0)
    f_var = 20 if pct_var <= 30 else (20 * (1 - (pct_var - 30) / 20) if pct_var <= 50 else 0)
    f_hormiga = 15 if pct_hormiga <= 5 else (15 * (1 - (pct_hormiga - 5) / 10) if pct_hormiga <= 15 else 0)
    f_sost = 5 if restante >= 0 else 0

    return max(0, min(100, round(f_ahorro + f_fijos + f_var + f_hormiga + f_sost)))


def generar_plan_accion(categoria, monto_actual, monto_recortar):
    planes = {
        "Alquiler": [
            f"📞 Renegocia con tu casero. Pide rebaja de Bs. {monto_recortar:,.0f} a cambio de firmar 1 año más.",
            f"🏠 Si es imposible, busca compañero de cuarto. Compartir baja gastos al 50%.",
            f"📍 Mudarte 1 km más alejado del centro reduce alquiler 15-25%.",
        ],
        "Luz": [
            f"💡 Cambia a bombillas LED (ahorro 60-80% en iluminación).",
            f"🔌 Desenchufa electrodomésticos cuando no los uses.",
            f"❄️ Sube el aire acondicionado 2°C: ahorra 12% del consumo.",
        ],
        "Internet": [
            f"📞 Llama a tu proveedor y di que vas a cancelar. 80% de las veces te dan 20-30% rebaja.",
            f"🔄 Compara con la competencia: Tigo, Entel, Cotel.",
            f"📦 Negocia paquete combinado (internet + cable).",
        ],
        "Comida": [
            f"🛒 Lista de compras semanal y cíñete a ella. Reduce 30% el gasto.",
            f"🍳 Cocina en casa 5 días a la semana. Cada comida fuera cuesta 4x más.",
            f"🥗 Compra en mercado tradicional: 30-40% más barato.",
            f"📦 Cocina por lotes los domingos.",
        ],
        "Transporte": [
            f"🚌 Cambia 2-3 viajes en taxi por minibús (ahorro 70%).",
            f"🚲 Distancias <3 km: caminar o bici.",
            f"🚗 Comparte taxi con compañeros de trabajo.",
            f"⛽ Si tienes auto: revisa presión de llantas mensualmente.",
        ],
        "Salidas": [
            f"📅 Limita salidas a 2 por mes. Calidad sobre cantidad.",
            f"🍷 Hace 'previa' en casa: reduce 60% el gasto en bares.",
            f"🎉 Busca planes gratuitos: parques, museos libres.",
            f"💳 Presupuesto fijo y úsalo SOLO en efectivo.",
        ],
        "Café/Snacks": [
            f"☕ Compra termo y prepara café en casa. Bs. 3 vs Bs. 18 en cafetería.",
            f"🍪 Lleva snacks de casa: frutos secos, fruta.",
            f"💰 Reto: 1 semana sin café fuera = Bs. {monto_recortar/4:,.0f} esa semana.",
        ],
        "Suscripciones": [
            f"📺 Audita TODAS tus suscripciones. ¿Las usaste últimos 30 días?",
            f"❌ Cancela las que no uses.",
            f"👨‍👩‍👧 Comparte plan familiar con amigos: divide costo entre 4-6.",
        ],
        "Comisiones banco": [
            f"🏦 Cambia a banco sin comisiones (Banco FIE, BCP cuentas básicas).",
            f"💳 Si te cobran por giros, retira más en menos viajes.",
            f"📲 Usa apps gratuitas (Tigo Money) en vez de transferencias.",
        ],
        "Delivery": [
            f"🍳 Cocina los domingos para toda la semana. Inversión 2h, ahorro Bs. {monto_recortar:,.0f}/mes.",
            f"🏪 Pide delivery grupal con compañeros para repartir envío.",
            f"📵 Borra apps de delivery del celular.",
        ],
        "Impulsivos": [
            f"⏰ Regla 24h: si quieres comprar +Bs. 100, espera 1 día.",
            f"📋 Lista de deseos: revísala en 30 días.",
            f"💵 Solo compra con efectivo. Duele más gastar billetes.",
            f"🛒 Borra apps de compras del celular.",
        ],
    }
    return planes.get(categoria, ["Consulta con un asesor financiero."])


# =====================================================
# PDF PROFESIONAL
# =====================================================
def generar_pdf_premium(datos):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'],
        fontSize=28, textColor=colors.HexColor('#7c3aed'),
        spaceAfter=8, alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Heading2'],
        fontSize=16, textColor=colors.HexColor('#1f2937'),
        spaceAfter=10, fontName='Helvetica-Bold',
    )
    section_label = ParagraphStyle(
        'SectionLabel', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#7c3aed'),
        spaceAfter=4, fontName='Helvetica-Bold', leading=12,
    )
    normal_style = ParagraphStyle(
        'Normal', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#374151'),
        spaceAfter=6, leading=14
    )
    callout_style = ParagraphStyle(
        'Callout', parent=styles['Normal'],
        fontSize=11, textColor=colors.HexColor('#1f2937'),
        spaceAfter=6, fontName='Helvetica-Bold', leading=14,
    )

    story = []

    # PORTADA
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("◆ ASESOR FINANCIERO PREMIUM", title_style))
    story.append(Paragraph(
        f"<font color='#6b7280' size='10'>Reporte personal de {datos['usuario']}</font>",
        ParagraphStyle('subt', parent=normal_style, alignment=TA_CENTER)))
    story.append(Paragraph(
        f"<font color='#9ca3af' size='9'>Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</font>",
        ParagraphStyle('date', parent=normal_style, alignment=TA_CENTER)))
    story.append(Spacer(1, 1.5*cm))

    score = datos['score']
    if score >= 80:
        score_color = colors.HexColor('#10b981')
        score_msg = "¡EXCELENCIA FINANCIERA!"
    elif score >= 50:
        score_color = colors.HexColor('#f59e0b')
        score_msg = "BUEN CAMINO, SIGUE OPTIMIZANDO"
    else:
        score_color = colors.HexColor('#ef4444')
        score_msg = "ACCIÓN INMEDIATA REQUERIDA"

    d = Drawing(400, 200)
    d.add(Circle(200, 100, 85, fillColor=colors.HexColor('#f3f4f6'),
                 strokeColor=score_color, strokeWidth=4))
    d.add(String(200, 95, str(score), fontSize=56, fontName='Helvetica-Bold',
                 fillColor=score_color, textAnchor='middle'))
    d.add(String(200, 65, '/100', fontSize=14, fontName='Helvetica',
                 fillColor=colors.HexColor('#9ca3af'), textAnchor='middle'))
    story.append(d)

    story.append(Paragraph(
        f"<b><font color='{score_color.hexval()}' size='14'>{score_msg}</font></b>",
        ParagraphStyle('msg', parent=normal_style, alignment=TA_CENTER)))
    story.append(Paragraph(
        f"<font color='#6b7280' size='11'>{datos['estado_label']}</font>",
        ParagraphStyle('lbl', parent=normal_style, alignment=TA_CENTER)))
    story.append(Spacer(1, 1*cm))

    story.append(Paragraph("Cómo se compone tu Score", section_label))

    breakdown_data = [
        ("Ahorro", min(35, datos.get('f_ahorro', 0)), 35, '#10b981'),
        ("Gastos Fijos", min(25, datos.get('f_fijos', 0)), 25, '#7c3aed'),
        ("Gastos Variables", min(20, datos.get('f_var', 0)), 20, '#06b6d4'),
        ("Control Hormigas", min(15, datos.get('f_hormiga', 0)), 15, '#f59e0b'),
        ("Sostenibilidad", min(5, datos.get('f_sost', 0)), 5, '#ef4444'),
    ]

    bd = Drawing(450, 130)
    y_pos = 110
    for label, val, max_val, color in breakdown_data:
        bd.add(String(5, y_pos, label, fontSize=9, fontName='Helvetica-Bold',
                      fillColor=colors.HexColor('#374151')))
        bd.add(Rect(120, y_pos - 3, 250, 12, fillColor=colors.HexColor('#e5e7eb'),
                    strokeColor=None))
        ancho = (val / max_val) * 250 if max_val > 0 else 0
        bd.add(Rect(120, y_pos - 3, ancho, 12, fillColor=colors.HexColor(color),
                    strokeColor=None))
        bd.add(String(380, y_pos, f"{val:.0f}/{max_val}", fontSize=9,
                      fontName='Helvetica-Bold', fillColor=colors.HexColor(color)))
        y_pos -= 22

    story.append(bd)
    story.append(PageBreak())

    # PÁGINA 2
    story.append(Paragraph("📊 RESUMEN EJECUTIVO", subtitle_style))

    kpi_table_data = [
        ['MÉTRICA', 'VALOR', '% INGRESO', 'IDEAL'],
        ['💵 Ingreso mensual', f"Bs. {datos['ingreso']:,.0f}", '100%', '—'],
        ['🏠 Gastos fijos', f"Bs. {datos['gastos_fijos']:,.0f}",
         f"{datos['pct_fijos']:.1f}%", '≤50%'],
        ['🎉 Gastos variables', f"Bs. {datos['gastos_var']:,.0f}",
         f"{datos['pct_var']:.1f}%", '≤30%'],
        ['🐜 Gastos hormiga', f"Bs. {datos['hormiga']:,.0f}",
         f"{datos['pct_hormiga']:.1f}%", '≤5%'],
        ['💰 Ahorro mensual', f"Bs. {datos['restante']:,.0f}",
         f"{datos['pct_ahorro']:.1f}%", '≥20%'],
        ['🐜 Hormiga al año', f"Bs. {datos['hormiga']*12:,.0f}", '—', '—'],
    ]

    t = Table(kpi_table_data, colWidths=[5*cm, 4.5*cm, 3*cm, 3*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c3aed')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.HexColor('#f9fafb'), colors.white]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.7*cm))

    story.append(Paragraph("🥧 Distribución de tus Gastos", section_label))

    pie_drawing = Drawing(450, 200)
    pie = Pie()
    pie.x = 120; pie.y = 20; pie.width = 160; pie.height = 160

    cat_montos = []; cat_labels = []; cat_colors = []
    if datos['gastos_fijos'] > 0:
        cat_montos.append(datos['gastos_fijos'])
        cat_labels.append(f"Fijos: Bs. {datos['gastos_fijos']:,.0f}")
        cat_colors.append(colors.HexColor('#7c3aed'))
    if datos['gastos_var'] > 0:
        cat_montos.append(datos['gastos_var'])
        cat_labels.append(f"Variables: Bs. {datos['gastos_var']:,.0f}")
        cat_colors.append(colors.HexColor('#06b6d4'))
    if datos['hormiga'] > 0:
        cat_montos.append(datos['hormiga'])
        cat_labels.append(f"Hormiga: Bs. {datos['hormiga']:,.0f}")
        cat_colors.append(colors.HexColor('#ef4444'))
    if datos['restante'] > 0:
        cat_montos.append(datos['restante'])
        cat_labels.append(f"Ahorro: Bs. {datos['restante']:,.0f}")
        cat_colors.append(colors.HexColor('#10b981'))

    pie.data = cat_montos
    pie.labels = None
    pie.slices.strokeWidth = 2
    pie.slices.strokeColor = colors.white

    for i, c in enumerate(cat_colors):
        pie.slices[i].fillColor = c

    pie_drawing.add(pie)

    legend = Legend()
    legend.x = 300; legend.y = 130
    legend.dx = 8; legend.dy = 8
    legend.fontName = 'Helvetica'; legend.fontSize = 9
    legend.boxAnchor = 'nw'; legend.columnMaximum = 4
    legend.colorNamePairs = list(zip(cat_colors, cat_labels))
    pie_drawing.add(legend)

    story.append(pie_drawing)
    story.append(PageBreak())

    # PÁGINA 3: 50/30/20
    story.append(Paragraph("🎯 REGLA 50/30/20 — ¿Cómo te comparas?", subtitle_style))
    story.append(Paragraph(
        "<i>La regla 50/30/20 es un estándar mundial: 50% para necesidades, "
        "30% para deseos, y 20% para ahorro/inversión.</i>", normal_style))
    story.append(Spacer(1, 0.3*cm))

    bar_drawing = Drawing(450, 250)
    bc = VerticalBarChart()
    bc.x = 50; bc.y = 50; bc.height = 180; bc.width = 380
    bc.data = [
        [datos['ingreso'] * 0.50, datos['ingreso'] * 0.30, datos['ingreso'] * 0.20],
        [datos['gastos_fijos'], datos['gastos_var'], max(0, datos['restante'])],
    ]
    bc.categoryAxis.categoryNames = ['Necesidades (50%)', 'Deseos (30%)', 'Ahorro (20%)']
    bc.bars[0].fillColor = colors.HexColor('#10b981')
    bc.bars[1].fillColor = colors.HexColor('#7c3aed')
    bc.bars.strokeWidth = 0
    bc.valueAxis.valueMin = 0
    bc.valueAxis.gridStrokeColor = colors.HexColor('#e5e7eb')
    bc.categoryAxis.labels.fontSize = 9
    bc.valueAxis.labels.fontSize = 8
    bc.barWidth = 25; bc.groupSpacing = 20

    bar_drawing.add(bc)

    bar_drawing.add(Rect(50, 5, 12, 12, fillColor=colors.HexColor('#10b981')))
    bar_drawing.add(String(70, 8, 'Lo IDEAL', fontSize=9, fontName='Helvetica-Bold',
                            fillColor=colors.HexColor('#374151')))
    bar_drawing.add(Rect(150, 5, 12, 12, fillColor=colors.HexColor('#7c3aed')))
    bar_drawing.add(String(170, 8, 'TU situación', fontSize=9, fontName='Helvetica-Bold',
                            fillColor=colors.HexColor('#374151')))

    story.append(bar_drawing)
    story.append(Spacer(1, 0.5*cm))

    diag_data = []
    pct_f = datos['pct_fijos']; pct_v = datos['pct_var']; pct_a = datos['pct_ahorro']

    if pct_f <= 50:
        diag_data.append(['✅', 'Necesidades', f'Vas excelente: {pct_f:.1f}% (meta ≤50%)'])
    else:
        diag_data.append(['⚠️', 'Necesidades', f'Excedes: {pct_f:.1f}% — recorta Bs. {(pct_f-50)*datos["ingreso"]/100:,.0f}'])

    if pct_v <= 30:
        diag_data.append(['✅', 'Deseos', f'Bajo control: {pct_v:.1f}%'])
    else:
        diag_data.append(['⚠️', 'Deseos', f'Excedes: {pct_v:.1f}% — recorta Bs. {(pct_v-30)*datos["ingreso"]/100:,.0f}'])

    if pct_a >= 20:
        diag_data.append(['✅', 'Ahorro', f'Meta cumplida: {pct_a:.1f}%'])
    else:
        diag_data.append(['⚠️', 'Ahorro', f'Por debajo: {pct_a:.1f}% — falta Bs. {(20-pct_a)*datos["ingreso"]/100:,.0f}'])

    diag_table = Table(diag_data, colWidths=[1*cm, 3.5*cm, 12*cm])
    diag_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1f2937')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#374151')),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    story.append(diag_table)

    # PÁGINA 4: Plan
    if datos.get('plan_optimizacion'):
        story.append(PageBreak())
        story.append(Paragraph("⚡ PLAN DE OPTIMIZACIÓN", subtitle_style))

        resultado_box = [[
            Paragraph(
                f"<b><font color='#10b981' size='14'>Bs. {datos['total_recorte']:,.0f}</font></b><br/>"
                f"<font size='9' color='#6b7280'>de ahorro mensual extra</font>",
                ParagraphStyle('rb', parent=normal_style, alignment=TA_CENTER)
            ),
            Paragraph(
                f"<b><font color='#7c3aed' size='14'>Bs. {datos['total_recorte']*12:,.0f}</font></b><br/>"
                f"<font size='9' color='#6b7280'>en un año</font>",
                ParagraphStyle('rb2', parent=normal_style, alignment=TA_CENTER)
            ),
            Paragraph(
                f"<b><font color='#f59e0b' size='14'>{datos['nuevo_pct_ahorro']:.1f}%</font></b><br/>"
                f"<font size='9' color='#6b7280'>nueva tasa de ahorro</font>",
                ParagraphStyle('rb3', parent=normal_style, alignment=TA_CENTER)
            ),
        ]]
        rt = Table(resultado_box, colWidths=[6*cm, 6*cm, 6*cm])
        rt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(rt)
        story.append(Spacer(1, 0.5*cm))

        plan_table_data = [['Categoría', 'Actual', 'Recortar', 'Nuevo', '% Ahorro']]
        for item in datos['plan_optimizacion']:
            plan_table_data.append([
                item['categoria'],
                f"Bs. {item['actual']:,.0f}",
                f"Bs. -{item['recortar']:,.0f}",
                f"Bs. {item['nuevo']:,.0f}",
                f"{item['pct']:.0f}%",
            ])

        pt = Table(plan_table_data, colWidths=[4.5*cm, 3*cm, 3*cm, 3*cm, 2.5*cm])
        pt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c3aed')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.HexColor('#f9fafb'), colors.white]),
            ('TEXTCOLOR', (2, 1), (2, -1), colors.HexColor('#ef4444')),
            ('TEXTCOLOR', (3, 1), (3, -1), colors.HexColor('#10b981')),
            ('FONTNAME', (3, 1), (3, -1), 'Helvetica-Bold'),
        ]))
        story.append(pt)
        story.append(Spacer(1, 0.7*cm))

        story.append(Paragraph("🛠️ Cómo recortar — Pasos concretos", section_label))
        for item in datos['plan_optimizacion'][:5]:
            story.append(Paragraph(
                f"<b>{item['categoria']}</b> → ahorras Bs. {item['recortar']:,.0f}/mes",
                callout_style
            ))
            for accion in item['acciones'][:3]:
                story.append(Paragraph(f"   • {accion}", normal_style))
            story.append(Spacer(1, 0.2*cm))

    # PÁGINA 5: Histórico
    if datos.get('historico') is not None and not datos['historico'].empty:
        story.append(PageBreak())
        story.append(Paragraph("📈 EVOLUCIÓN HISTÓRICA", subtitle_style))

        df_h = datos['historico']
        story.append(Paragraph(
            f"Tienes <b>{len(df_h)} meses</b> de datos registrados. "
            f"Tu ahorro promedio es <b>Bs. {df_h['restante'].mean():,.0f}/mes</b>.",
            normal_style))
        story.append(Spacer(1, 0.4*cm))

        hist_data = [['Mes', 'Ingreso', 'Gastos', 'Ahorro', '% Ahorro']]
        for _, row in df_h.tail(12).iterrows():
            pct = (row['restante']/row['ingreso']*100) if row['ingreso'] > 0 else 0
            hist_data.append([
                row['mes_periodo'],
                f"Bs. {row['ingreso']:,.0f}",
                f"Bs. {row['gastos_total']:,.0f}",
                f"Bs. {row['restante']:,.0f}",
                f"{pct:.1f}%",
            ])

        ht = Table(hist_data, colWidths=[3*cm, 3.5*cm, 3.5*cm, 3.5*cm, 2.5*cm])
        ht.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.HexColor('#f9fafb'), colors.white]),
        ]))
        story.append(ht)

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "<i>Reporte generado por Asesor Financiero Premium · Esta herramienta brinda orientación general; "
        "para decisiones críticas consulta con un asesor financiero certificado.</i>",
        ParagraphStyle('foot', parent=normal_style, fontSize=8,
                       textColor=colors.grey, alignment=TA_CENTER)))

    doc.build(story)
    buffer.seek(0)
    return buffer


# =====================================================
# CSS PRINCIPAL DEL DASHBOARD
# =====================================================
def get_theme_css(score):
    if score < 50:
        primary = "#ff3b3b"; accent = "#ff6b6b"
        bg_grad = "linear-gradient(135deg, #1a0000 0%, #2d0a0a 50%, #1a0000 100%)"
        card_bg = "rgba(255, 59, 59, 0.08)"; card_border = "rgba(255, 59, 59, 0.3)"
        glow = "0 8px 32px rgba(255, 59, 59, 0.2)"; text_accent = "#ff8a8a"
    elif score >= 80:
        primary = "#ffd700"; accent = "#ffb800"
        bg_grad = "linear-gradient(135deg, #1a1400 0%, #2d2410 50%, #1a1400 100%)"
        card_bg = "rgba(255, 215, 0, 0.08)"; card_border = "rgba(255, 215, 0, 0.4)"
        glow = "0 8px 32px rgba(255, 215, 0, 0.25)"; text_accent = "#ffe066"
    else:
        primary = "#7c3aed"; accent = "#a78bfa"
        bg_grad = "linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #0f0f1e 100%)"
        card_bg = "rgba(124, 58, 237, 0.08)"; card_border = "rgba(167, 139, 250, 0.25)"
        glow = "0 8px 32px rgba(124, 58, 237, 0.15)"; text_accent = "#c4b5fd"

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
.stApp {{ background: {bg_grad}; background-attachment: fixed; font-family: 'Inter', sans-serif; }}
header[data-testid="stHeader"] {{
    background: rgba(15, 15, 30, 0.6) !important;
    backdrop-filter: blur(20px); height: 50px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}}
header[data-testid="stHeader"] *, [data-testid="stToolbar"] *,
[data-testid="stDecoration"], [data-testid="stStatusWidget"] * {{
    color: white !important; fill: white !important; stroke: white !important;
}}
header button, [data-testid="stToolbar"] button {{
    background: rgba(255, 255, 255, 0.1) !important; color: white !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 8px !important;
}}
#MainMenu, footer {{ visibility: hidden; }}

.kpi-card {{
    background: {card_bg}; backdrop-filter: blur(20px);
    border: 1px solid {card_border}; border-radius: 15px;
    padding: 24px; box-shadow: {glow}; transition: all 0.3s ease; height: 100%;
}}
.kpi-card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 40px {primary}40; }}
.kpi-label {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px;
    color: {text_accent}; margin-bottom: 8px; font-weight: 500;
    display: flex; align-items: center; gap: 8px;
}}
.kpi-value {{ font-size: 28px; font-weight: 700; color: white; margin: 0; }}
.kpi-delta {{ font-size: 13px; color: {text_accent}; margin-top: 6px; }}
.kpi-delta.positive {{ color: #10b981; }}
.kpi-delta.negative {{ color: #ef4444; }}

.score-container {{
    background: {card_bg}; backdrop-filter: blur(20px);
    border: 1px solid {card_border}; border-radius: 20px;
    padding: 30px; text-align: center; box-shadow: {glow};
}}
.score-number {{
    font-size: 72px; font-weight: 800;
    background: linear-gradient(135deg, {primary}, {accent});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.score-label {{
    font-size: 12px; text-transform: uppercase; letter-spacing: 2px;
    color: {text_accent}; font-weight: 600;
}}
.score-tagline {{ font-size: 14px; color: rgba(255,255,255,0.7); margin-top: 12px; }}

.section-title {{
    font-size: 18px; font-weight: 600; color: white;
    margin: 30px 0 15px 0; display: flex; align-items: center; gap: 10px;
    padding-bottom: 10px; border-bottom: 1px solid {card_border};
}}
.section-title svg {{ color: {primary}; }}

.insight-card {{
    background: {card_bg}; backdrop-filter: blur(20px);
    border: 1px solid {card_border}; border-left: 4px solid {primary};
    border-radius: 12px; padding: 18px 22px; margin: 12px 0;
    color: rgba(255,255,255,0.9); font-size: 14px; line-height: 1.6;
}}
.insight-card.success {{ border-left-color: #10b981; }}
.insight-card.warning {{ border-left-color: #f59e0b; }}
.insight-card.danger {{ border-left-color: #ef4444; }}
.insight-card h4 {{
    color: white; margin: 0 0 10px 0; font-size: 15px;
    display: flex; align-items: center; gap: 8px;
}}

.action-card {{
    background: linear-gradient(135deg, rgba(124,58,237,0.1), rgba(167,139,250,0.05));
    backdrop-filter: blur(20px); border: 1px solid {card_border};
    border-left: 5px solid {primary}; border-radius: 14px;
    padding: 20px 24px; margin: 16px 0; transition: all 0.3s ease;
}}
.action-card:hover {{ transform: translateX(5px); box-shadow: -5px 5px 25px {primary}30; }}
.action-header {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 12px; padding-bottom: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}}
.action-cat {{ font-size: 16px; font-weight: 700; color: white; }}
.action-amount {{ text-align: right; }}
.action-old {{ color: #ef4444; text-decoration: line-through; font-size: 13px; opacity: 0.7; }}
.action-new {{ color: #10b981; font-size: 18px; font-weight: 700; }}
.action-saving {{
    background: linear-gradient(135deg, {primary}, {accent}); color: white;
    padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;
    display: inline-block; margin-top: 4px;
}}
.action-steps {{ list-style: none; padding: 0; margin: 0; }}
.action-steps li {{
    color: rgba(255,255,255,0.85); padding: 8px 0; font-size: 13px;
    border-bottom: 1px dashed rgba(255,255,255,0.08);
}}
.action-steps li:last-child {{ border-bottom: none; }}

.stButton > button {{
    background: linear-gradient(135deg, {primary}, {accent}) !important;
    color: white !important; border: none !important;
    border-radius: 12px !important; padding: 12px 24px !important;
    font-weight: 600 !important; box-shadow: 0 4px 14px {primary}50 !important;
}}
.stDownloadButton > button {{
    background: linear-gradient(135deg, #10b981, #059669) !important;
    color: white !important; border: none !important;
    border-radius: 12px !important; padding: 14px 28px !important;
    font-weight: 700 !important; box-shadow: 0 4px 14px rgba(16,185,129,0.4) !important;
    font-size: 15px !important;
}}

section[data-testid="stSidebar"] {{
    background: rgba(15, 15, 30, 0.85) !important;
    backdrop-filter: blur(30px); border-right: 1px solid {card_border};
}}
section[data-testid="stSidebar"] * {{ color: white !important; }}
section[data-testid="stSidebar"] label {{
    color: rgba(255,255,255,0.85) !important;
    font-size: 12px !important; font-weight: 500 !important;
}}

/* BOTONES +/- DEL SIDEBAR */
section[data-testid="stSidebar"] [data-testid="stNumberInput"] button {{
    background: rgba(124, 58, 237, 0.3) !important;
    border: 1px solid {card_border} !important; color: white !important;
}}
section[data-testid="stSidebar"] [data-testid="stNumberInput"] button:hover {{
    background: {primary} !important;
}}
section[data-testid="stSidebar"] [data-testid="stNumberInput"] button svg,
section[data-testid="stSidebar"] [data-testid="stNumberInput"] button * {{
    fill: white !important; color: white !important;
}}

.stTabs [data-baseweb="tab-list"] {{
    background: {card_bg}; backdrop-filter: blur(20px);
    border-radius: 12px; padding: 6px; gap: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 8px; color: {text_accent} !important; background: transparent;
}}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, {primary}, {accent}) !important; color: white !important;
}}

h1, h2, h3 {{ color: white !important; }}
h1 {{
    background: linear-gradient(135deg, {primary}, {accent});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-weight: 800 !important;
}}
.stCaption, .stMarkdown p {{ color: rgba(255,255,255,0.7) !important; }}

.progress-bar {{
    width: 100%; height: 8px; background: rgba(255,255,255,0.1);
    border-radius: 4px; overflow: hidden; margin-top: 12px;
}}
.progress-fill {{
    height: 100%; background: linear-gradient(90deg, {primary}, {accent});
    border-radius: 4px; transition: width 1s ease;
}}
.icon-md {{ width: 20px; height: 20px; vertical-align: middle; }}
.stDataFrame {{ background: {card_bg}; border-radius: 12px; }}
</style>
"""


ICONS = {
    "wallet": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 12V7H5a2 2 0 010-4h14v4M3 5v14a2 2 0 002 2h16v-5"/><path d="M18 12a2 2 0 100 4h4v-4z"/></svg>',
    "trending_up": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    "trending_down": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>',
    "piggy": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/></svg>',
    "ant": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="6" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="18" r="2"/></svg>',
    "target": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    "shield": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "brain": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 01-4.96.44 2.5 2.5 0 01-2.96-3.08 3 3 0 01-.34-5.58 2.5 2.5 0 011.32-4.24 2.5 2.5 0 014.44-1.04z"/></svg>',
    "calculator": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="4" y="2" width="16" height="20" rx="2"/></svg>',
    "zap": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "alert": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>',
    "check": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>',
    "crystal": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 3h12l4 6-10 13L2 9z"/></svg>',
    "download": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/></svg>',
    "robot": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/></svg>',
    "user": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "history": '<svg class="icon-md" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 12a9 9 0 109-9"/><polyline points="3 5 3 12 10 12"/></svg>',
}

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.markdown(f"""
<div style="background: rgba(124,58,237,0.15); border: 1px solid rgba(167,139,250,0.3);
            border-radius: 12px; padding: 12px; margin-bottom: 16px; text-align: center;">
    <div style="font-size: 11px; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 1px;">Sesión activa</div>
    <div style="font-size: 16px; color: white; font-weight: 700; margin-top: 4px;">👤 {USUARIO}</div>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
    st.session_state.usuario_actual = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### CONFIGURACIÓN")
hoy = date.today()
mes_periodo = st.sidebar.text_input("Período (YYYY-MM)", value=hoy.strftime("%Y-%m"))

st.sidebar.markdown("---")
st.sidebar.markdown("### INGRESO")
ingreso_total = st.sidebar.number_input("Ingreso mensual (Bs.)", min_value=0.0, value=5000.0, step=100.0)

st.sidebar.markdown("### GASTOS FIJOS")
alquiler = st.sidebar.number_input("Alquiler", min_value=0.0, value=1500.0, step=50.0)
luz = st.sidebar.number_input("Luz", min_value=0.0, value=200.0, step=10.0)
internet = st.sidebar.number_input("Internet", min_value=0.0, value=250.0, step=10.0)

st.sidebar.markdown("### GASTOS VARIABLES")
comida = st.sidebar.number_input("Comida", min_value=0.0, value=800.0, step=50.0)
transporte = st.sidebar.number_input("Transporte", min_value=0.0, value=300.0, step=10.0)
salidas = st.sidebar.number_input("Salidas", min_value=0.0, value=400.0, step=50.0)

st.sidebar.markdown("### GASTOS HORMIGA")
cafe_diario = st.sidebar.number_input("Café/snacks diarios", min_value=0.0, value=15.0, step=5.0)
suscripciones = st.sidebar.number_input("Suscripciones", min_value=0.0, value=80.0, step=10.0)
comisiones_banco = st.sidebar.number_input("Comisiones banco", min_value=0.0, value=25.0, step=5.0)
delivery = st.sidebar.number_input("Delivery semanal", min_value=0.0, value=120.0, step=10.0)
impulsivos = st.sidebar.number_input("Impulsivos", min_value=0.0, value=150.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🤖 ASESOR IA (OPCIONAL)")
api_key = st.sidebar.text_input("API Key de Anthropic", type="password",
                                 help="Pega tu API Key para activar el asesor IA")

st.sidebar.markdown("---")
if st.sidebar.button("💾 Guardar mes en histórico", use_container_width=True):
    datos_save = (datetime.now().isoformat(), mes_periodo, ingreso_total,
                  alquiler, luz, internet, comida, transporte, salidas,
                  cafe_diario, suscripciones, comisiones_banco, delivery, impulsivos)
    if guardar_personal(USUARIO, datos_save):
        st.sidebar.success(f"Guardado: {mes_periodo}")

# Cálculos
gastos_fijos = alquiler + luz + internet
gastos_variables = comida + transporte + salidas
gastos_totales = gastos_fijos + gastos_variables
dinero_restante = ingreso_total - gastos_totales
hormiga_mensual = (cafe_diario * 30) + suscripciones + comisiones_banco + (delivery * 4) + impulsivos
hormiga_anual = hormiga_mensual * 12
pct_ahorro = (dinero_restante / ingreso_total * 100) if ingreso_total > 0 else 0
pct_fijos_calc = (gastos_fijos / ingreso_total * 100) if ingreso_total > 0 else 0
pct_var_calc = (gastos_variables / ingreso_total * 100) if ingreso_total > 0 else 0
hormiga_pct = (hormiga_mensual / ingreso_total * 100) if ingreso_total > 0 else 0

score = calcular_score(ingreso_total, gastos_fijos, gastos_variables, hormiga_mensual, dinero_restante)

# === CSS DEL DASHBOARD + CSS UNIVERSAL DE INPUTS ===
st.markdown(get_theme_css(score), unsafe_allow_html=True)
st.markdown(GLOBAL_INPUT_CSS, unsafe_allow_html=True)

# Header
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 20px 0;">
    <div>
        <h1 style="margin: 0; font-size: 36px;">◆ Asesor Financiero Premium</h1>
        <p style="margin: 4px 0 0 0; color: rgba(255,255,255,0.6); font-size: 14px; letter-spacing: 1px;">
            Bienvenido, <b>{USUARIO}</b> · INGENIERÍA FINANCIERA · OPTIMIZACIÓN MATEMÁTICA
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

if score < 50:
    score_label = "ESTADO CRÍTICO"; score_tagline = "Necesitas acción inmediata."
elif score < 70:
    score_label = "ESTADO REGULAR"; score_tagline = "Hay margen de mejora."
elif score < 85:
    score_label = "ESTADO SALUDABLE"; score_tagline = "Buen control financiero."
else:
    score_label = "ESTADO PREMIUM"; score_tagline = "Excelencia financiera."

col_score, col_kpis = st.columns([1, 3])

with col_score:
    st.markdown(f"""
    <div class="score-container">
        <div class="score-label">SCORE DE SALUD</div>
        <div class="score-number">{score}</div>
        <div class="score-label" style="font-size: 11px;">{score_label}</div>
        <div class="progress-bar"><div class="progress-fill" style="width: {score}%;"></div></div>
        <div class="score-tagline">{score_tagline}</div>
    </div>
    """, unsafe_allow_html=True)

with col_kpis:
    k1, k2, k3, k4 = st.columns(4)
    delta_class = "positive" if dinero_restante >= 0 else "negative"
    with k1:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{ICONS['wallet']} INGRESO</div>
        <div class="kpi-value">Bs. {ingreso_total:,.0f}</div><div class="kpi-delta">Mensual</div></div>""",
        unsafe_allow_html=True)
    with k2:
        pct_g = (gastos_totales / ingreso_total * 100) if ingreso_total > 0 else 0
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{ICONS['trending_down']} GASTOS</div>
        <div class="kpi-value">Bs. {gastos_totales:,.0f}</div>
        <div class="kpi-delta">{pct_g:.1f}% del ingreso</div></div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{ICONS['piggy']} AHORRO</div>
        <div class="kpi-value">Bs. {dinero_restante:,.0f}</div>
        <div class="kpi-delta {delta_class}">{pct_ahorro:.1f}% de tasa</div></div>""", unsafe_allow_html=True)
    with k4:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{ICONS['ant']} HORMIGA</div>
        <div class="kpi-value">Bs. {hormiga_mensual:,.0f}</div>
        <div class="kpi-delta">Bs. {hormiga_anual:,.0f}/año</div></div>""", unsafe_allow_html=True)

# TABS
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["DASHBOARD", "PREDICCIÓN 6M", "OPTIMIZADOR", "🤖 ASESOR IA", "📈 MI HISTÓRICO", "📄 REPORTE PDF"]
)

# TAB 1: DASHBOARD
with tab1:
    st.markdown(f"""<div class="section-title">{ICONS['target']} DISTRIBUCIÓN INTELIGENTE DE GASTOS</div>""",
                unsafe_allow_html=True)

    consejos_dict = {
        "Alquiler": "Recomendado: ≤30% del ingreso.",
        "Luz": "Saludable: 3-5% del ingreso.",
        "Internet": "Negocia cada 6 meses.",
        "Comida": "Meta: ≤15% del ingreso.",
        "Transporte": "Si supera 10%, evalúa transporte público.",
        "Salidas": "Regla 24h antes de gastar +Bs.200.",
        "Café/Snacks": "Bs.15/día = Bs.5,400/año.",
        "Suscripciones": "Audita cada 3 meses.",
        "Comisiones banco": "Negocia o cambia de banco.",
        "Delivery": "Cocina los domingos.",
        "Impulsivos": "Lista de deseos 30 días.",
    }

    cat_data = [
        ("Alquiler", alquiler, "Fijo"), ("Luz", luz, "Fijo"), ("Internet", internet, "Fijo"),
        ("Comida", comida, "Variable"), ("Transporte", transporte, "Variable"), ("Salidas", salidas, "Variable"),
        ("Café/Snacks", cafe_diario * 30, "Hormiga"), ("Suscripciones", suscripciones, "Hormiga"),
        ("Comisiones banco", comisiones_banco, "Hormiga"), ("Delivery", delivery * 4, "Hormiga"),
        ("Impulsivos", impulsivos, "Hormiga"),
    ]
    cat_data = [c for c in cat_data if c[1] > 0]

    color_map = {"Fijo": "#7c3aed", "Variable": "#06b6d4", "Hormiga": "#ef4444"}
    if score >= 80:
        color_map = {"Fijo": "#ffd700", "Variable": "#ffb800", "Hormiga": "#ff8c00"}
    elif score < 50:
        color_map = {"Fijo": "#ff6b6b", "Variable": "#ff8a8a", "Hormiga": "#ffaaaa"}

    echarts_data = [{"value": round(m, 2), "name": n, "tipo": t,
                     "itemStyle": {"color": color_map.get(t, "#999")}}
                    for n, m, t in cat_data]

    options_donut = {
        "backgroundColor": "transparent",
        "tooltip": {"trigger": "item", "backgroundColor": "rgba(20, 20, 35, 0.95)",
                    "textStyle": {"color": "#fff"}, "extraCssText": "border-radius: 12px; padding: 14px;",
                    "formatter": "<b>{b}</b><br/>Bs. {c} ({d}%)"},
        "legend": {"orient": "vertical", "right": "5%", "top": "center",
                   "textStyle": {"color": "rgba(255,255,255,0.8)"}, "icon": "circle"},
        "series": [{"name": "Distribución", "type": "pie", "radius": ["50%", "75%"],
                    "center": ["35%", "50%"], "avoidLabelOverlap": True,
                    "itemStyle": {"borderRadius": 8, "borderColor": "rgba(15,15,30,0.8)", "borderWidth": 3},
                    "label": {"show": False},
                    "emphasis": {"label": {"show": True, "fontSize": 16, "fontWeight": "bold",
                                            "color": "#fff", "formatter": "{b}\n{d}%"}},
                    "data": echarts_data}],
    }
    st_echarts(options=options_donut, height="450px", key="donut_main")

    st.caption("Consejos personalizados por categoría:")
    cols_tips = st.columns(3)
    for idx, (nombre, monto, tipo) in enumerate(cat_data):
        with cols_tips[idx % 3]:
            color = color_map.get(tipo, "#999")
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.04); border-left: 3px solid {color};
                        border-radius: 8px; padding: 10px 14px; margin: 6px 0;">
                <div style="font-size: 12px; color: {color}; font-weight: 600; text-transform: uppercase;">{nombre}</div>
                <div style="font-size: 16px; color: white; font-weight: 700; margin: 4px 0;">Bs. {monto:,.0f}</div>
                <div style="font-size: 11px; color: rgba(255,255,255,0.7);">💡 {consejos_dict.get(nombre, "")}</div>
            </div>
            """, unsafe_allow_html=True)

    # RADAR
    st.markdown(f"""<div class="section-title">{ICONS['shield']} RADAR DE EQUILIBRIO 50/30/20</div>""",
                unsafe_allow_html=True)

    radar_color = "#ffd700" if score >= 80 else ("#ff3b3b" if score < 50 else "#7c3aed")

    options_radar = {
        "backgroundColor": "transparent",
        "tooltip": {"backgroundColor": "rgba(20,20,35,0.95)",
                    "textStyle": {"color": "#fff"},
                    "extraCssText": "border-radius: 12px; padding: 12px;"},
        "legend": {"data": ["Tu situación", "Meta 50/30/20"],
                   "textStyle": {"color": "rgba(255,255,255,0.8)"}, "top": 10},
        "radar": {
            "indicator": [
                {"name": "Necesidades (≤50%)", "max": 100},
                {"name": "Deseos (≤30%)", "max": 100},
                {"name": "Ahorro (≥20%)", "max": 100},
                {"name": "Hormigas (≤5%)", "max": 100},
                {"name": "Sostenibilidad", "max": 100},
            ],
            "axisName": {"color": "rgba(255,255,255,0.8)", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.1)"}},
            "splitArea": {"areaStyle": {"color": ["rgba(255,255,255,0.02)", "rgba(255,255,255,0.05)"]}},
            "axisLine": {"lineStyle": {"color": "rgba(255,255,255,0.2)"}},
        },
        "series": [{
            "type": "radar",
            "data": [
                {
                    "value": [
                        round(max(0, 100 - max(0, pct_fijos_calc - 50) * 2), 1),
                        round(max(0, 100 - max(0, pct_var_calc - 30) * 2), 1),
                        round(min(100, max(0, pct_ahorro * 5)), 1),
                        round(max(0, 100 - hormiga_pct * 10), 1),
                        100 if dinero_restante >= 0 else 0,
                    ],
                    "name": "Tu situación",
                    "areaStyle": {"color": radar_color, "opacity": 0.3},
                    "lineStyle": {"color": radar_color, "width": 2},
                    "itemStyle": {"color": radar_color},
                },
                {
                    "value": [100, 100, 100, 100, 100],
                    "name": "Meta 50/30/20",
                    "areaStyle": {"color": "rgba(16, 185, 129, 0.1)"},
                    "lineStyle": {"color": "#10b981", "width": 1, "type": "dashed"},
                    "itemStyle": {"color": "#10b981"},
                },
            ],
        }],
    }
    st_echarts(options=options_radar, height="420px", key="radar_main")

# TAB 2: PREDICCIÓN
with tab2:
    st.markdown(f"""<div class="section-title">{ICONS['crystal']} PROYECCIÓN DE SALDO — PRÓXIMOS 6 MESES</div>""",
                unsafe_allow_html=True)

    df_hist = cargar_historico(USUARIO)
    if len(df_hist) < 2:
        st.markdown(f"""<div class="insight-card warning">
        <h4>{ICONS['alert']} Modo proyección básica</h4>
        Guarda al menos 2 meses para activar regresión lineal real.</div>""", unsafe_allow_html=True)
        meses_futuros = list(range(1, 7))
        saldo_acumulado = [dinero_restante * m for m in meses_futuros]
        saldo_optimista = [dinero_restante * m * 1.15 for m in meses_futuros]
        saldo_pesimista = [dinero_restante * m * 0.75 for m in meses_futuros]
    else:
        df_hist["gastos_total"] = (df_hist["alquiler"] + df_hist["luz"] + df_hist["internet"] +
                                    df_hist["comida"] + df_hist["transporte"] + df_hist["salidas"])
        df_hist["restante"] = df_hist["ingreso"] - df_hist["gastos_total"]
        df_hist = df_hist.sort_values("mes_periodo").reset_index(drop=True)
        df_hist["t"] = range(len(df_hist))
        X = df_hist["t"].values; y = df_hist["restante"].values
        x_mean, y_mean = X.mean(), y.mean()
        a = np.sum((X - x_mean) * (y - y_mean)) / np.sum((X - x_mean) ** 2) if np.sum((X - x_mean) ** 2) > 0 else 0
        b = y_mean - a * x_mean
        ultimo_t = df_hist["t"].iloc[-1]
        meses_futuros = list(range(1, 7))
        ahorro_pred = [a * (ultimo_t + m) + b for m in meses_futuros]
        saldo_actual_total = df_hist["restante"].sum()
        saldo_acumulado = []
        acum = saldo_actual_total
        for ahorro in ahorro_pred:
            acum += ahorro; saldo_acumulado.append(acum)
        residuals = y - (a * X + b)
        std_dev = np.std(residuals) if len(residuals) > 1 else abs(y_mean) * 0.2
        saldo_optimista, saldo_pesimista = [], []
        acum_opt, acum_pes = saldo_actual_total, saldo_actual_total
        for i, ahorro in enumerate(ahorro_pred):
            acum_opt += ahorro + std_dev * (i + 1) * 0.5
            acum_pes += ahorro - std_dev * (i + 1) * 0.5
            saldo_optimista.append(acum_opt); saldo_pesimista.append(acum_pes)

    meses_labels = [f"M+{m}" for m in meses_futuros]
    line_color = "#ffd700" if score >= 80 else ("#ff3b3b" if score < 50 else "#7c3aed")
    options_pred = {
        "backgroundColor": "transparent",
        "tooltip": {"trigger": "axis", "backgroundColor": "rgba(20,20,35,0.95)",
                    "textStyle": {"color": "#fff"}},
        "legend": {"data": ["Optimista", "Proyección", "Pesimista"],
                   "textStyle": {"color": "rgba(255,255,255,0.8)"}, "top": 10},
        "grid": {"left": "5%", "right": "5%", "bottom": "10%", "top": "15%", "containLabel": True},
        "xAxis": {"type": "category", "data": meses_labels,
                  "axisLine": {"lineStyle": {"color": "rgba(255,255,255,0.3)"}},
                  "axisLabel": {"color": "rgba(255,255,255,0.7)"}},
        "yAxis": {"type": "value",
                  "axisLine": {"lineStyle": {"color": "rgba(255,255,255,0.3)"}},
                  "axisLabel": {"color": "rgba(255,255,255,0.7)"},
                  "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.08)"}}},
        "series": [
            {"name": "Optimista", "type": "line", "data": [round(s, 2) for s in saldo_optimista],
             "smooth": True, "lineStyle": {"color": "#10b981", "width": 2, "type": "dashed"},
             "itemStyle": {"color": "#10b981"}},
            {"name": "Proyección", "type": "line", "data": [round(s, 2) for s in saldo_acumulado],
             "smooth": True, "lineStyle": {"color": line_color, "width": 4},
             "itemStyle": {"color": line_color}, "symbolSize": 10,
             "areaStyle": {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                                     "colorStops": [{"offset": 0, "color": line_color + "60"},
                                                    {"offset": 1, "color": line_color + "00"}]}}},
            {"name": "Pesimista", "type": "line", "data": [round(s, 2) for s in saldo_pesimista],
             "smooth": True, "lineStyle": {"color": "#ef4444", "width": 2, "type": "dashed"},
             "itemStyle": {"color": "#ef4444"}},
        ],
    }
    st_echarts(options=options_pred, height="450px", key="pred_chart")

# TAB 3: OPTIMIZADOR
with tab3:
    st.markdown(f"""<div class="section-title">{ICONS['brain']} OPTIMIZADOR DE PRESUPUESTO</div>""",
                unsafe_allow_html=True)

    st.markdown(f"""<div class="insight-card">
    <h4>{ICONS['calculator']} ¿Cómo funciona?</h4>
    Programación lineal con SciPy para encontrar el plan óptimo de recortes.
    </div>""", unsafe_allow_html=True)

    if st.button("⚡ OPTIMIZAR MI PRESUPUESTO", use_container_width=True):
        categorias_opt = {
            "Alquiler": {"actual": alquiler, "max_recorte": 0.10, "prioridad": 1},
            "Luz": {"actual": luz, "max_recorte": 0.20, "prioridad": 2},
            "Internet": {"actual": internet, "max_recorte": 0.25, "prioridad": 2},
            "Comida": {"actual": comida, "max_recorte": 0.30, "prioridad": 3},
            "Transporte": {"actual": transporte, "max_recorte": 0.40, "prioridad": 4},
            "Salidas": {"actual": salidas, "max_recorte": 0.70, "prioridad": 5},
            "Café/Snacks": {"actual": cafe_diario * 30, "max_recorte": 0.80, "prioridad": 6},
            "Suscripciones": {"actual": suscripciones, "max_recorte": 0.90, "prioridad": 7},
            "Comisiones banco": {"actual": comisiones_banco, "max_recorte": 0.70, "prioridad": 6},
            "Delivery": {"actual": delivery * 4, "max_recorte": 0.85, "prioridad": 7},
            "Impulsivos": {"actual": impulsivos, "max_recorte": 0.95, "prioridad": 8},
        }
        cat_names = list(categorias_opt.keys())
        n_vars = len(cat_names)
        c = [-1.0 / categorias_opt[name]["prioridad"] for name in cat_names]
        bounds = [(0, categorias_opt[name]["actual"] * categorias_opt[name]["max_recorte"])
                  for name in cat_names]
        meta_ahorro = ingreso_total * 0.20
        falta_para_meta = max(0, meta_ahorro - dinero_restante)

        if falta_para_meta == 0:
            st.markdown(f"""<div class="insight-card success">
            <h4>{ICONS['check']} Ya estás optimizado</h4>
            Tu ahorro supera la meta del 20%. Invierte el excedente.
            </div>""", unsafe_allow_html=True)
            st.session_state['plan_opt'] = None
        else:
            A_ub = [[-1.0] * n_vars]; b_ub = [-falta_para_meta]
            max_total = sum([categorias_opt[n]["actual"] * categorias_opt[n]["max_recorte"]
                             for n in cat_names])
            if max_total < falta_para_meta:
                st.markdown(f"""<div class="insight-card danger">
                <h4>{ICONS['alert']} Imposible con tu ingreso actual</h4>
                Aumenta tu ingreso.</div>""", unsafe_allow_html=True)
                st.session_state['plan_opt'] = None
            else:
                result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
                if result.success:
                    recortes = result.x
                    total_recorte = sum(recortes)
                    nuevo_ahorro = dinero_restante + total_recorte
                    nuevo_pct = (nuevo_ahorro / ingreso_total * 100)
                    plan_data = []
                    for i, name in enumerate(cat_names):
                        if recortes[i] > 0.01:
                            actual = categorias_opt[name]["actual"]
                            plan_data.append({
                                "categoria": name, "actual": actual,
                                "recortar": recortes[i], "nuevo": actual - recortes[i],
                                "pct": recortes[i] / actual * 100 if actual > 0 else 0,
                                "acciones": generar_plan_accion(name, actual, recortes[i]),
                            })
                    plan_data.sort(key=lambda x: x["recortar"], reverse=True)
                    st.session_state['plan_opt'] = {
                        "plan": plan_data, "total_recorte": total_recorte,
                        "nuevo_ahorro": nuevo_ahorro, "nuevo_pct_ahorro": nuevo_pct,
                    }

    if st.session_state.get('plan_opt'):
        po = st.session_state['plan_opt']

        st.markdown(f"""<div class="insight-card success">
        <h4>{ICONS['zap']} Plan óptimo</h4>
        Recortando <b>Bs. {po['total_recorte']:,.2f}</b>, tu ahorro sube a
        <b>Bs. {po['nuevo_ahorro']:,.2f} ({po['nuevo_pct_ahorro']:.1f}%)</b>.
        En un año = <b>Bs. {po['total_recorte']*12:,.2f}</b>.
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 2fr 1.3fr 1.3fr 1.3fr 1fr;
                    background: linear-gradient(90deg, rgba(124,58,237,0.4), rgba(167,139,250,0.2));
                    padding: 14px 20px; font-weight: 700; font-size: 11px;
                    text-transform: uppercase; letter-spacing: 1.5px; color: white;
                    border-radius: 14px 14px 0 0;">
            <div>📌 Categoría</div><div style="text-align: right;">Actual</div>
            <div style="text-align: right;">↓ Recortar</div>
            <div style="text-align: right;">Nuevo</div>
            <div style="text-align: right;">% Recorte</div>
        </div>
        """, unsafe_allow_html=True)

        for idx, item in enumerate(po['plan']):
            bg = "rgba(255,255,255,0.02)" if idx % 2 == 0 else "rgba(255,255,255,0.04)"
            bar_color = "#ef4444" if item['pct'] >= 70 else ("#f59e0b" if item['pct'] >= 40 else "#10b981")
            st.markdown(f"""
            <div style="display: grid; grid-template-columns: 2fr 1.3fr 1.3fr 1.3fr 1fr;
                        background: {bg}; padding: 14px 20px; align-items: center;
                        border-bottom: 1px solid rgba(255,255,255,0.05);">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 4px; height: 30px; background: {bar_color}; border-radius: 4px;"></div>
                    <span style="color: white; font-weight: 600;">{item['categoria']}</span>
                </div>
                <div style="text-align: right; color: rgba(255,255,255,0.6);
                            text-decoration: line-through;">Bs. {item['actual']:,.0f}</div>
                <div style="text-align: right; color: #ef4444; font-weight: 600;">− Bs. {item['recortar']:,.0f}</div>
                <div style="text-align: right; color: #10b981; font-weight: 700;">Bs. {item['nuevo']:,.0f}</div>
                <div style="text-align: right;">
                    <span style="background: {bar_color}25; color: {bar_color};
                                 padding: 4px 10px; border-radius: 12px; font-size: 12px;
                                 font-weight: 700; border: 1px solid {bar_color}50;">
                        {item['pct']:.0f}%
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 2fr 1.3fr 1.3fr 1.3fr 1fr;
                    background: linear-gradient(90deg, rgba(16,185,129,0.2), rgba(16,185,129,0.05));
                    padding: 16px 20px; align-items: center;
                    border-top: 2px solid rgba(16,185,129,0.4); border-radius: 0 0 14px 14px;
                    margin-bottom: 24px;">
            <div style="color: white; font-weight: 700;">💰 TOTAL AHORRO</div><div></div>
            <div style="text-align: right; color: #10b981; font-weight: 800; font-size: 18px;">
                + Bs. {po['total_recorte']:,.0f}</div>
            <div style="text-align: right; color: rgba(255,255,255,0.7); font-size: 12px;">
                = Bs. {po['total_recorte']*12:,.0f}/año</div>
            <div></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""<div class="section-title">🛠️ Cómo recortar — Pasos concretos</div>""",
                    unsafe_allow_html=True)
        for item in po['plan']:
            steps_html = "".join([f"<li>{accion}</li>" for accion in item['acciones']])
            st.markdown(f"""
            <div class="action-card">
                <div class="action-header">
                    <div>
                        <div class="action-cat">📌 {item['categoria']}</div>
                        <span class="action-saving">Recorta {item['pct']:.0f}% · Bs. {item['recortar']:,.0f}/mes</span>
                    </div>
                    <div class="action-amount">
                        <div class="action-old">Bs. {item['actual']:,.0f}</div>
                        <div class="action-new">→ Bs. {item['nuevo']:,.0f}</div>
                    </div>
                </div>
                <ul class="action-steps">{steps_html}</ul>
            </div>
            """, unsafe_allow_html=True)

# TAB 4: ASESOR IA
with tab4:
    st.markdown(f"""<div class="section-title">{ICONS['robot']} ASESOR IA PERSONALIZADO</div>""",
                unsafe_allow_html=True)

    if not ANTHROPIC_AVAILABLE:
        st.markdown(f"""<div class="insight-card warning">
        <h4>{ICONS['alert']} Librería no instalada</h4>
        Ejecuta: <code>pip install anthropic</code>
        </div>""", unsafe_allow_html=True)
    elif not api_key:
        st.markdown(f"""<div class="insight-card">
        <h4>{ICONS['robot']} Configura tu API Key</h4>
        Crea cuenta en <a href="https://console.anthropic.com" target="_blank" style="color: #a78bfa;">console.anthropic.com</a>,
        carga $5 USD, genera API Key y pégala en el sidebar.
        </div>""", unsafe_allow_html=True)
    else:
        pregunta = st.text_area("Pregúntale a Claude:",
                                 placeholder="Ej: ¿Cómo puedo ahorrar más sin sacrificar mi calidad de vida?",
                                 height=100)
        if st.button("💬 Consultar al Asesor IA", use_container_width=True):
            if pregunta.strip():
                try:
                    client = Anthropic(api_key=api_key)
                    contexto = f"""Eres asesor financiero experto. Analiza y responde concretamente.

DATOS DE {USUARIO}:
- Ingreso: Bs. {ingreso_total:,.0f}
- Gastos fijos: Bs. {gastos_fijos:,.0f} ({pct_fijos_calc:.1f}%)
- Gastos variables: Bs. {gastos_variables:,.0f} ({pct_var_calc:.1f}%)
- Hormiga: Bs. {hormiga_mensual:,.0f} ({hormiga_pct:.1f}%)
- Ahorro: Bs. {dinero_restante:,.0f} ({pct_ahorro:.1f}%)
- Score: {score}/100

PREGUNTA: {pregunta}

Responde en español, máximo 4 párrafos."""
                    with st.spinner("Claude analizando..."):
                        message = client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=1024,
                            messages=[{"role": "user", "content": contexto}]
                        )
                        respuesta = message.content[0].text
                    st.markdown(f"""<div class="insight-card success">
                    <b>🤖 Claude responde:</b><br><br>{respuesta}
                    </div>""", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# TAB 5: HISTÓRICO
with tab5:
    st.markdown(f"""<div class="section-title">{ICONS['history']} TU HISTÓRICO — {USUARIO}</div>""",
                unsafe_allow_html=True)

    df_h = cargar_historico(USUARIO)
    if df_h.empty:
        st.markdown(f"""<div class="insight-card warning">
        <h4>{ICONS['alert']} Aún no tienes histórico</h4>
        Configura tus datos en el sidebar y dale a "💾 Guardar mes en histórico".
        </div>""", unsafe_allow_html=True)
    else:
        df_h["gastos_total"] = (df_h["alquiler"] + df_h["luz"] + df_h["internet"] +
                                  df_h["comida"] + df_h["transporte"] + df_h["salidas"])
        df_h["restante"] = df_h["ingreso"] - df_h["gastos_total"]
        df_h["pct_ahorro"] = (df_h["restante"] / df_h["ingreso"] * 100).round(1)

        kh1, kh2, kh3, kh4 = st.columns(4)
        kh1.markdown(f"""<div class="kpi-card"><div class="kpi-label">📅 Meses</div>
        <div class="kpi-value">{len(df_h)}</div></div>""", unsafe_allow_html=True)
        kh2.markdown(f"""<div class="kpi-card"><div class="kpi-label">💵 Ingreso prom.</div>
        <div class="kpi-value">Bs. {df_h['ingreso'].mean():,.0f}</div></div>""", unsafe_allow_html=True)
        kh3.markdown(f"""<div class="kpi-card"><div class="kpi-label">💰 Ahorro prom.</div>
        <div class="kpi-value">Bs. {df_h['restante'].mean():,.0f}</div></div>""", unsafe_allow_html=True)
        kh4.markdown(f"""<div class="kpi-card"><div class="kpi-label">📊 Tasa prom.</div>
        <div class="kpi-value">{df_h['pct_ahorro'].mean():.1f}%</div></div>""", unsafe_allow_html=True)

        line_color = "#ffd700" if score >= 80 else ("#ff3b3b" if score < 50 else "#7c3aed")
        opt_evo = {
            "backgroundColor": "transparent",
            "tooltip": {"trigger": "axis", "backgroundColor": "rgba(20,20,35,0.95)",
                        "textStyle": {"color": "#fff"}},
            "legend": {"data": ["Ingreso", "Gastos", "Ahorro"],
                       "textStyle": {"color": "rgba(255,255,255,0.8)"}, "top": 10},
            "grid": {"left": "3%", "right": "5%", "bottom": "10%", "top": "15%", "containLabel": True},
            "xAxis": {"type": "category", "data": df_h["mes_periodo"].tolist(),
                      "axisLine": {"lineStyle": {"color": "rgba(255,255,255,0.3)"}},
                      "axisLabel": {"color": "rgba(255,255,255,0.7)"}},
            "yAxis": {"type": "value",
                      "axisLine": {"lineStyle": {"color": "rgba(255,255,255,0.3)"}},
                      "axisLabel": {"color": "rgba(255,255,255,0.7)"},
                      "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.08)"}}},
            "series": [
                {"name": "Ingreso", "type": "line", "data": df_h["ingreso"].tolist(),
                 "smooth": True, "lineStyle": {"color": "#10b981", "width": 3},
                 "itemStyle": {"color": "#10b981"}},
                {"name": "Gastos", "type": "line", "data": df_h["gastos_total"].tolist(),
                 "smooth": True, "lineStyle": {"color": "#ef4444", "width": 3},
                 "itemStyle": {"color": "#ef4444"}},
                {"name": "Ahorro", "type": "line", "data": df_h["restante"].tolist(),
                 "smooth": True, "lineStyle": {"color": line_color, "width": 4},
                 "itemStyle": {"color": line_color},
                 "areaStyle": {"color": line_color + "30"}},
            ],
        }
        st_echarts(options=opt_evo, height="400px", key="hist_evo")

        df_show = df_h[["mes_periodo", "ingreso", "gastos_total", "restante", "pct_ahorro"]].copy()
        df_show.columns = ["Mes", "Ingreso", "Gastos", "Ahorro", "% Ahorro"]
        st.dataframe(df_show.style.format({
            "Ingreso": "Bs. {:,.2f}", "Gastos": "Bs. {:,.2f}",
            "Ahorro": "Bs. {:,.2f}", "% Ahorro": "{:.1f}%"
        }), hide_index=True, use_container_width=True)

        col_exp, col_del = st.columns(2)
        with col_exp:
            csv = df_h.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Descargar CSV", csv,
                               f"historico_{USUARIO}.csv", "text/csv",
                               use_container_width=True)
        with col_del:
            with st.expander("🗑️ Eliminar un mes"):
                mes_borrar = st.selectbox("Mes:", df_h["mes_periodo"].tolist())
                if st.button("Eliminar"):
                    if borrar_registro(USUARIO, mes_borrar):
                        st.success(f"Eliminado: {mes_borrar}")
                        st.rerun()

# TAB 6: PDF
with tab6:
    st.markdown(f"""<div class="section-title">{ICONS['download']} REPORTE PDF PROFESIONAL</div>""",
                unsafe_allow_html=True)

    st.markdown(f"""<div class="insight-card">
    <h4>{ICONS['download']} Reporte de {len(cargar_historico(USUARIO))} meses + análisis actual</h4>
    Genera un PDF profesional de <b>5 páginas</b>:
    <ul>
    <li>📊 Portada con Score gigante y breakdown visual</li>
    <li>📈 Resumen ejecutivo con KPIs y gráfico de pie</li>
    <li>🎯 Análisis 50/30/20 con gráfico de barras</li>
    <li>⚡ Plan de optimización detallado</li>
    <li>📅 Histórico completo</li>
    </ul>
    </div>""", unsafe_allow_html=True)

    if ingreso_total > 0:
        f_ahorro = 35 if pct_ahorro >= 20 else (35*(pct_ahorro/20) if pct_ahorro >= 10 else (15*(pct_ahorro/10) if pct_ahorro >= 0 else 0))
        f_fijos = 25 if pct_fijos_calc <= 50 else (25*(1-(pct_fijos_calc-50)/20) if pct_fijos_calc <= 70 else 0)
        f_var = 20 if pct_var_calc <= 30 else (20*(1-(pct_var_calc-30)/20) if pct_var_calc <= 50 else 0)
        f_hormiga = 15 if hormiga_pct <= 5 else (15*(1-(hormiga_pct-5)/10) if hormiga_pct <= 15 else 0)
        f_sost = 5 if dinero_restante >= 0 else 0
    else:
        f_ahorro = f_fijos = f_var = f_hormiga = f_sost = 0

    df_h = cargar_historico(USUARIO)
    if not df_h.empty:
        df_h["gastos_total"] = (df_h["alquiler"] + df_h["luz"] + df_h["internet"] +
                                  df_h["comida"] + df_h["transporte"] + df_h["salidas"])
        df_h["restante"] = df_h["ingreso"] - df_h["gastos_total"]

    datos_pdf = {
        "usuario": USUARIO,
        "score": score, "estado_label": score_label,
        "f_ahorro": f_ahorro, "f_fijos": f_fijos, "f_var": f_var,
        "f_hormiga": f_hormiga, "f_sost": f_sost,
        "ingreso": ingreso_total, "gastos_fijos": gastos_fijos,
        "gastos_var": gastos_variables, "hormiga": hormiga_mensual,
        "restante": dinero_restante, "pct_ahorro": pct_ahorro,
        "pct_fijos": pct_fijos_calc, "pct_var": pct_var_calc,
        "pct_hormiga": hormiga_pct,
        "historico": df_h if not df_h.empty else None,
    }

    if st.session_state.get('plan_opt'):
        po = st.session_state['plan_opt']
        datos_pdf["plan_optimizacion"] = po['plan']
        datos_pdf["total_recorte"] = po['total_recorte']
        datos_pdf["nuevo_ahorro"] = po['nuevo_ahorro']
        datos_pdf["nuevo_pct_ahorro"] = po['nuevo_pct_ahorro']

    try:
        pdf_buffer = generar_pdf_premium(datos_pdf)
        st.download_button(
            label="📄 DESCARGAR REPORTE PDF PREMIUM",
            data=pdf_buffer,
            file_name=f"reporte_{USUARIO}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Error: {str(e)}")

st.markdown("---")
st.caption(f"◆ Asesor Financiero Premium · {USUARIO} · Score: {score}/100")
