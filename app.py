import streamlit as st
import numpy as np
import pandas as pd
import re
import sqlite3
import json
import hashlib
from PIL import Image
import pytesseract

st.set_page_config(page_title="AeroMetrics Pro", layout="wide", page_icon="⚡", initial_sidebar_state="collapsed")

# ==========================================
# CSS PARA PANTALLA DIVIDIDA / MÓVIL
# ==========================================
st.markdown("""
<style>
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 0.8rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    .stButton>button {
        padding: 0.35rem 0.5rem !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# BASE DE DATOS LOCAL
# ==========================================
DB_FILE = "aviator_data.db"

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY,
            email TEXT,
            password TEXT,
            balance REAL,
            banca_inicial REAL,
            historial_balance TEXT,
            historial_multiplicadores TEXT
        )
    ''')
    conn.commit()
    conn.close()

def registrar_usuario(username, email, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO usuarios (username, email, password, balance, banca_inicial, historial_balance, historial_multiplicadores)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, make_hashes(password), 62000.0, 62000.0, json.dumps([62000.0]), json.dumps([])))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def autenticar_usuario(identificador, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT username, password, balance, banca_inicial, historial_balance, historial_multiplicadores 
        FROM usuarios 
        WHERE username = ? OR email = ?
    ''', (identificador, identificador))
    data = c.fetchone()
    conn.close()
    if data and check_hashes(password, data[1]):
        hist_mult = json.loads(data[5]) if len(data) > 5 and data[5] else []
        return {
            "username": data[0],
            "balance": data[2],
            "banca_inicial": data[3],
            "historial_balance": json.loads(data[4]),
            "historial_mult": hist_mult
        }
    return None

def guardar_datos_usuario(username, balance, banca_inicial, historial_bal, historial_mult):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE usuarios 
        SET balance = ?, banca_inicial = ?, historial_balance = ?, historial_multiplicadores = ?
        WHERE username = ?
    ''', (balance, banca_inicial, json.dumps(historial_bal), json.dumps(historial_mult), username))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# ACCESO (LOGIN / REGISTRO)
# ==========================================
if 'logged_user' not in st.session_state:
    st.session_state.logged_user = None

if not st.session_state.logged_user:
    st.markdown("<h2 style='text-align: center; color: #ff0055; margin-bottom: 0px;'>AEROMETRICS PRO</h2>", unsafe_allow_html=True)
    st.caption("<p style='text-align: center; color: #94a3b8; margin-top: 0px;'>Terminal Cuantitativa</p>", unsafe_allow_html=True)

    tab_login, tab_registro = st.tabs(["🔑 Iniciar Sesión", "📝 Registro"])
    with tab_login:
        identificador = st.text_input("Usuario o Correo:", key="login_id")
        password_login = st.text_input("Contraseña:", type="password", key="login_pass")
        if st.button("Entrar", use_container_width=True):
            if identificador and password_login:
                usuario_data = autenticar_usuario(identificador.strip().lower(), password_login)
                if usuario_data:
                    st.session_state.logged_user = usuario_data["username"]
                    st.session_state.balance = usuario_data["balance"]
                    st.session_state.banca_inicial = usuario_data["banca_inicial"]
                    st.session_state.historial_balance = usuario_data["historial_balance"]
                    st.session_state.historial_mult = usuario_data["historial_mult"]
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")
    with tab_registro:
        nuevo_email = st.text_input("Email:", key="reg_email")
        nuevo_usuario = st.text_input("Usuario:", key="reg_user")
        nuevo_pass = st.text_input("Clave:", type="password", key="reg_pass")
        if st.button("Registrar", use_container_width=True):
            if nuevo_email and nuevo_usuario and nuevo_pass:
                if registrar_usuario(nuevo_usuario.strip().lower(), nuevo_email.strip().lower(), nuevo_pass):
                    st.success("Cuenta creada exitosamente.")
                else:
                    st.error("El usuario ya existe.")
    st.stop()

# ==========================================
# GESTIÓN DE ESTADO ACTIVO
# ==========================================
username = st.session_state.logged_user
if 'historial_mult' not in st.session_state:
    st.session_state.historial_mult = []

# Sidebar
st.sidebar.markdown(f"**Operador:** `@{username}`")
banca_inicial = st.sidebar.number_input("Banca Inicial ($ COP):", value=float(st.session_state.banca_inicial), step=1000.0)
riesgo_pct = st.sidebar.slider("Riesgo por ronda (%):", min_value=1.0, max_value=8.0, value=4.0, step=0.5)
stop_loss_pct = st.sidebar.slider("Stop Loss (% pérdida):", min_value=5, max_value=50, value=20)
take_profit_pct = st.sidebar.slider("Take Profit (% ganancia):", min_value=10, max_value=100, value=25)

piso_sl = banca_inicial * (1 - stop_loss_pct / 100)
techo_tp = banca_inicial * (1 + take_profit_pct / 100)

if st.sidebar.button("🔄 Reiniciar Banca"):
    st.session_state.balance = float(banca_inicial)
    st.session_state.historial_balance = [float(banca_inicial)]
    st.session_state.historial_mult = []
    guardar_datos_usuario(username, float(banca_inicial), float(banca_inicial), [float(banca_inicial)], [])
    st.rerun()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_user = None
    st.rerun()

# Alertas de SL / TP
if st.session_state.balance <= piso_sl:
    st.error("🛑 STOP LOSS ALCANZADO: Cierra sesión de inmediato.")
elif st.session_state.balance >= techo_tp:
    st.success("🎯 TAKE PROFIT ALCANZADO: Sesión ganada, retira utilidades.")

# ==========================================
# LÓGICA DE DETECCIÓN Y SEMÁFORO
# ==========================================
def diagnosticar_secuencia(multiplicadores):
    if not multiplicadores:
        return "SIN_DATOS", "Esperando lecturas...", 0
    
    r1_actual = multiplicadores[0]
    r2_anterior = multiplicadores[1] if len(multiplicadores) >= 2 else None
    
    azules_previos = 0
    for x in multiplicadores[1:]:
        if x < 2.00:
            azules_previos += 1
        else:
            break
            
    actual_pos = r1_actual >= 2.00
    ant_pos = (r2_anterior is not None) and (r2_anterior >= 2.00)

    if actual_pos and ant_pos:
        return "VERDE", f"🟢 RACHA CONFIRMADA (+{r1_actual:.2f}x / +{r2_anterior:.2f}x)", azules_previos
    elif actual_pos and not ant_pos:
        if azules_previos >= 3:
            return "ROJO", f"🛑 TRAMPA: Aislado tras {azules_previos} azules (+{r1_actual:.2f}x)", azules_previos
        elif r1_actual >= 2.50:
            return "VERDE", f"🟢 QUIEBRE FUERTE (+{r1_actual:.2f}x)", azules_previos
        else:
            return "AMARILLO", f"🟡 MORADO DÉBIL (+{r1_actual:.2f}x) - Esperar", azules_previos
    elif not actual_pos and ant_pos:
        if r1_actual >= 1.50:
            return "AMARILLO", f"⚠️ FRENO: Azul Amortiguado (-{r1_actual:.2f}x)", azules_previos
        else:
            return "ROJO", f"🔴 BLOQUEO: Falso Quiebre (-{r1_actual:.2f}x)", azules_previos
    else:
        return "ROJO", f"🔴 FASE FRÍA ACTIVA (-{r1_actual:.2f}x)", azules_previos

# ==========================================
# PESTAÑAS PRINCIPALES
# ==========================================
tabs = st.tabs([
    "🛡️ Doble Apuesta (3:1)", 
    "🟢 Apuesta Simple", 
    "📷 Escáner & Rápido", 
    "🧪 Monte Carlo"
])

# ------------------------------------------
# TAB 1: DOBLE APUESTA 3:1
# ------------------------------------------
with tabs[0]:
    apuesta_total_raw = st.session_state.balance * (riesgo_pct / 100)
    sug_c1 = max(1500.0, float(int((apuesta_total_raw * 0.75) // 100) * 100))
    sug_c2 = max(500.0, float(int((apuesta_total_raw * 0.25) // 100) * 100))

    c_top1, c_top2 = st.columns(2)
    c_top1.metric("Banca", f"${st.session_state.balance:,.0f} COP")
    c_top2.metric("Inversión 3:1", f"${(sug_c1 + sug_c2):,.0f} COP")

    estado, mensaje, _ = diagnosticar_secuencia(st.session_state.historial_mult)
    if estado == "VERDE":
        st.success(f"**{mensaje}**\n\n👉 **Casilla 1:** ${sug_c1:,.0f} a **1.50x** | **Casilla 2:** ${sug_c2:,.0f} a **2.00x**")
    elif estado == "ROJO":
        st.error(f"**{mensaje}**\n\n⛔ **QUIETO:** No entrar. Freno de absorción activado.")
    elif estado == "AMARILLO":
        st.warning(f"**{mensaje}**\n\n✋ **PRECAUCIÓN:** Esperar siguiente tiro sin arriesgar.")
    else:
        st.info("Registra tiros en la pestaña Escáner para activar las señales.")

    st.markdown("#### 📝 Registrar Resultado")
    c_res1, c_res2, c_res3 = st.columns(3)
    gan_ambas = (sug_c1 * 0.5) + (sug_c2 * 1.0)
    gan_c1 = (sug_c1 * 0.5) - sug_c2
    perd_total = sug_c1 + sug_c2

    with c_res1:
        if st.button(f"🏆 ≥ 2.00x\n(+${gan_ambas:,.0f})", use_container_width=True):
            st.session_state.balance += gan_ambas
            st.session_state.historial_balance.append(st.session_state.balance)
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance, st.session_state.historial_mult)
            st.rerun()
    with c_res2:
        if st.button(f"🛡️ 1.50x\n(+${gan_c1:,.0f})", use_container_width=True):
            st.session_state.balance += gan_c1
            st.session_state.historial_balance.append(st.session_state.balance)
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance, st.session_state.historial_mult)
            st.rerun()
    with c_res3:
        if st.button(f"💥 < 1.50x\n(-${perd_total:,.0f})", use_container_width=True):
            st.session_state.balance -= perd_total
            st.session_state.historial_balance.append(st.session_state.balance)
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance, st.session_state.historial_mult)
            st.rerun()

# ------------------------------------------
# TAB 2: APUESTA SIMPLE (RESTAURADA)
# ------------------------------------------
with tabs[1]:
    st.subheader("🎯 Modo Entrada Simple")

    apuesta_simple_raw = st.session_state.balance * (riesgo_pct / 100)
    apuesta_sug_simple = max(500.0, float(int(apuesta_simple_raw // 100) * 100))

    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Banca Actual", f"${st.session_state.balance:,.0f} COP")
    col_s2.metric("Sugerida (Redondeada)", f"${apuesta_sug_simple:,.0f} COP")

    objetivo_x = st.slider("Objetivo Cash-out (x):", min_value=1.10, max_value=3.50, value=1.50, step=0.05)
    prob_exito = (0.97 / objetivo_x) * 100
    st.caption(f"Probabilidad estadística estimada: **{prob_exito:.1f}%**")

    st.markdown("---")
    monto_apuesta_s = st.number_input("Monto a jugar ($ COP):", value=float(apuesta_sug_simple), step=100.0)

    ganancia_potencial = monto_apuesta_s * (objetivo_x - 1.0)
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button(f"✅ Ganada (+${ganancia_potencial:,.0f})", use_container_width=True):
            st.session_state.balance += ganancia_potencial
            st.session_state.historial_balance.append(st.session_state.balance)
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance, st.session_state.historial_mult)
            st.rerun()
    with c_btn2:
        if st.button(f"❌ Perdida (-${monto_apuesta_s:,.0f})", use_container_width=True):
            st.session_state.balance -= monto_apuesta_s
            st.session_state.historial_balance.append(st.session_state.balance)
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance, st.session_state.historial_mult)
            st.rerun()

# ------------------------------------------
# TAB 3: ESCÁNER Y ENTRADA RÁPIDA
# ------------------------------------------
with tabs[2]:
    st.subheader("⚡ Entrada Rápida de Multiplicador")
    st.write("Escribe el valor que acaba de cerrar para actualizar el semáforo:")
    
    col_in1, col_in2 = st.columns([2, 1])
    with col_in1:
        nuevo_mult = st.number_input("Multiplicador:", min_value=1.00, max_value=500.0, value=2.00, step=0.05, label_visibility="collapsed")
    with col_in2:
        if st.button("➕ Cargar", use_container_width=True):
            st.session_state.historial_mult.insert(0, nuevo_mult)
            if len(st.session_state.historial_mult) > 20:
                st.session_state.historial_mult.pop()
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance, st.session_state.historial_mult)
            st.rerun()

    if st.session_state.historial_mult:
        muestra = st.session_state.historial_mult[:8]
        etiquetas = [f"🟣 +{x:.2f}x" if x >= 2.00 else f"🔵 -{x:.2f}x" for x in reversed(muestra)]
        st.markdown("**Secuencia (Pasado ➔ Reciente):**")
        st.write(" ➔ ".join(etiquetas))
        
        if st.button("🗑️ Borrar Historial de Tiros", use_container_width=True):
            st.session_state.historial_mult = []
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance, [])
            st.rerun()

    st.markdown("---")
    st.subheader("📷 Subir Captura de Historial")
    uploaded_file = st.file_uploader("Subir imagen de rondas", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        ocr_text = pytesseract.image_to_string(img)
        
        lineas = [l for l in ocr_text.split("\n") if not any(p in l.upper() for p in ["COP", "SALDO", "APUESTA", "GANANCIA"])]
        matches = re.findall(r"(\d+[\.,]\d{1,2})\s*x?", "\n".join(lineas))
        
        mults_detectados = []
        for m in matches:
            try:
                v = float(m.replace(",", "."))
                if 1.00 <= v <= 999.0 and v not in [50.0, 500.0, 1500.0, 50000.0]:
                    mults_detectados.append(v)
            except ValueError:
                continue
                
        if mults_detectados:
            st.session_state.historial_mult = mults_detectados[:15]
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance, st.session_state.historial_mult)
            st.success(f"Cargados {len(mults_detectados)} multiplicadores.")
            st.rerun()

# ------------------------------------------
# TAB 4: MONTE CARLO
# ------------------------------------------
with tabs[3]:
    st.subheader("🧪 Simulación de Riesgo")
    rondas_sim = st.slider("Número de Rondas:", min_value=10, max_value=300, value=50, step=10)
    cashout_sim = st.slider("Objetivo Cash-out (x):", min_value=1.10, max_value=3.00, value=1.50, step=0.05)
    
    if st.button("🚀 Ejecutar Simulación", use_container_width=True):
        banca_actual = st.session_state.balance
        registro = [banca_actual]
        apuesta_base = banca_actual * (riesgo_pct / 100)
        
        for _ in range(rondas_sim):
            if banca_actual <= 0:
                break
            r = np.random.uniform(0, 1)
            crash = max(1.0, np.floor((0.97 / (1.0 - r)) * 100) / 100)
            monto = min(apuesta_base, banca_actual)
            
            if crash >= cashout_sim:
                banca_actual += monto * (cashout_sim - 1.0)
            else:
                banca_actual -= monto
            registro.append(banca_actual)
            
        st.line_chart(pd.DataFrame({"Balance": registro}))
        st.write(f"Balance proyectado: **${banca_actual:,.2f} COP**")
