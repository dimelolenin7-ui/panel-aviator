import streamlit as st
import numpy as np
import pandas as pd
import re
import sqlite3
import json
import hashlib
from PIL import Image
import pytesseract

st.set_page_config(page_title="AeroMetrics Pro | Terminal Cuantitativa", layout="wide", page_icon="⚡")

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
            historial_balance TEXT
        )
    ''')
    conn.commit()
    conn.close()

def registrar_usuario(username, email, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO usuarios (username, email, password, balance, banca_inicial, historial_balance)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, make_hashes(password), 50000.0, 50000.0, json.dumps([50000.0])))
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
        SELECT username, password, balance, banca_inicial, historial_balance 
        FROM usuarios 
        WHERE username = ? OR email = ?
    ''', (identificador, identificador))
    data = c.fetchone()
    conn.close()
    if data and check_hashes(password, data[1]):
        return {
            "username": data[0],
            "balance": data[2],
            "banca_inicial": data[3],
            "historial_balance": json.loads(data[4])
        }
    return None

def guardar_datos_usuario(username, balance, banca_inicial, historial):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE usuarios 
        SET balance = ?, banca_inicial = ?, historial_balance = ?
        WHERE username = ?
    ''', (balance, banca_inicial, json.dumps(historial), username))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# PANTALLA DE ACCESO (BRANDING & LOGIN)
# ==========================================
if 'logged_user' not in st.session_state:
    st.session_state.logged_user = None

if not st.session_state.logged_user:
    logo_svg = """
    <div style="text-align: center; margin-bottom: 25px;">
        <svg width="100" height="100" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="planeGrad" x1="0%" y1="100%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#ff0055" />
                    <stop offset="50%" stop-color="#9900ef" />
                    <stop offset="100%" stop-color="#00f2fe" />
                </linearGradient>
                <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#ff0055" stop-opacity="0.8"/>
                    <stop offset="100%" stop-color="#9900ef" stop-opacity="0.1"/>
                </linearGradient>
            </defs>
            <circle cx="50" cy="50" r="44" stroke="url(#ringGrad)" stroke-width="2.5" stroke-dasharray="6 4"/>
            <circle cx="50" cy="50" r="32" stroke="#222736" stroke-width="1.5"/>
            <path d="M50 18 L68 74 L50 63 L32 74 Z" fill="url(#planeGrad)" filter="drop-shadow(0px 0px 8px rgba(255, 0, 85, 0.6))"/>
            <circle cx="50" cy="63" r="3" fill="#00f2fe"/>
        </svg>
        <h1 style="color: #ffffff; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; letter-spacing: 2px; margin-top: 10px; margin-bottom: 0px;">
            AEROMETRICS <span style="color: #ff0055;">PRO</span>
        </h1>
        <p style="color: #94a3b8; font-size: 13px; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 5px;">
            Terminal Cuantitativa & Motor Anti-Trampa
        </p>
    </div>
    """
    st.markdown(logo_svg, unsafe_allow_html=True)

    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        tab_login, tab_registro = st.tabs(["🔑 Iniciar Sesión", "📝 Registro"])

        with tab_login:
            identificador = st.text_input("Correo electrónico o Usuario:", key="login_id")
            password_login = st.text_input("Contraseña:", type="password", key="login_pass")
            
            if st.button("Acceder a la Terminal", use_container_width=True):
                if identificador and password_login:
                    usuario_data = autenticar_usuario(identificador.strip().lower(), password_login)
                    if usuario_data:
                        st.session_state.logged_user = usuario_data["username"]
                        st.session_state.balance = usuario_data["balance"]
                        st.session_state.banca_inicial = usuario_data["banca_inicial"]
                        st.session_state.historial_balance = usuario_data["historial_balance"]
                        st.success("Acceso autorizado.")
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas.")
                else:
                    st.warning("Completa todos los campos.")

        with tab_registro:
            nuevo_email = st.text_input("Correo electrónico:", key="reg_email", placeholder="ejemplo@gmail.com")
            nuevo_usuario = st.text_input("Nombre de usuario:", key="reg_user")
            nuevo_pass = st.text_input("Contraseña:", type="password", key="reg_pass")
            nuevo_pass_conf = st.text_input("Confirmar contraseña:", type="password", key="reg_pass_conf")
            
            if st.button("Crear Cuenta", use_container_width=True):
                if nuevo_email and nuevo_usuario and nuevo_pass:
                    if nuevo_pass != nuevo_pass_conf:
                        st.error("Las contraseñas no coinciden.")
                    elif len(nuevo_pass) < 4:
                        st.error("La contraseña debe tener mínimo 4 caracteres.")
                    else:
                        if registrar_usuario(nuevo_usuario.strip().lower(), nuevo_email.strip().lower(), nuevo_pass):
                            st.success("Cuenta creada. Ahora puedes iniciar sesión.")
                        else:
                            st.error("El usuario ya existe.")
                else:
                    st.warning("Por favor llena todos los campos.")

    st.stop()

# ==========================================
# TERMINAL AUTENTICADA
# ==========================================
username = st.session_state.logged_user
st.sidebar.markdown(f"### ⚡ **AEROMETRICS PRO**")
st.sidebar.caption(f"Operador activo: **@{username}**")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_user = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configuración")

banca_inicial_guardada = getattr(st.session_state, 'banca_inicial', 50000.0)
banca_inicial = st.sidebar.number_input("Banca Inicial ($ COP):", value=float(banca_inicial_guardada), step=1000.0)
riesgo_pct = st.sidebar.slider("Riesgo total por ronda (%):", min_value=0.5, max_value=6.0, value=4.0, step=0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (% pérdida):", min_value=5, max_value=50, value=20)
take_profit_pct = st.sidebar.slider("Take Profit (% ganancia):", min_value=10, max_value=100, value=25)

if st.sidebar.button("🔄 Reiniciar Balance"):
    st.session_state.balance = float(banca_inicial)
    st.session_state.banca_inicial = float(banca_inicial)
    st.session_state.historial_balance = [float(banca_inicial)]
    guardar_datos_usuario(username, float(banca_inicial), float(banca_inicial), [float(banca_inicial)])
    st.rerun()

piso_sl = banca_inicial * (1 - stop_loss_pct / 100)
techo_tp = banca_inicial * (1 + take_profit_pct / 100)

# Redondeo a múltiplos de 100 COP para Apuesta Simple
apuesta_calc_simple = st.session_state.balance * (riesgo_pct / 100)
apuesta_sug_simple = max(500.0, float(int(apuesta_calc_simple // 100) * 100))

tabs = st.tabs([
    "🟢 Apuesta Simple", 
    "🛡️ Doble Apuesta (Estrategia 3:1)", 
    "📷 Escáner y Patrones", 
    "🧪 Monte Carlo"
])

# ==========================================
# PESTAÑA 1: APUESTA SIMPLE
# ==========================================
with tabs[0]:
    st.title("🎯 Modo Entrada Simple")
    
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Banca Guardada")
        dif_pct = ((st.session_state.balance - banca_inicial) / banca_inicial) * 100
        st.subheader(f"${st.session_state.balance:,.2f}")
        st.markdown(f"<span style='color: {'#00cc96' if dif_pct >= 0 else '#ff4b4b'}; font-weight: bold;'>{'↑' if dif_pct >= 0 else '↓'} {dif_pct:+.2f}%</span>", unsafe_allow_html=True)

    with col2:
        st.caption("Apuesta Sugerida (Redondeada a $100)")
        st.subheader(f"${apuesta_sug_simple:,.0f} COP")

    col3, col4 = st.columns(2)
    with col3:
        st.caption("Piso Stop Loss")
        st.subheader(f"${piso_sl:,.2f}")
    with col4:
        st.caption("Techo Take Profit")
        st.subheader(f"${techo_tp:,.2f}")

    st.markdown("---")

    if st.session_state.balance <= piso_sl:
        st.error("🛑 STOP LOSS ALCANZADO: Cierra la sesión inmediatamente.")
    elif st.session_state.balance >= techo_tp:
        st.success("🎯 TAKE PROFIT ALCANZADO: Retira y finaliza la sesión.")

    st.subheader("🎯 Calculadora en Vivo")
    objetivo_x = st.slider("Objetivo de retiro planeado (x):", min_value=1.05, max_value=5.00, value=1.40, step=0.01)
    
    prob_exito = (0.97 / objetivo_x) * 100
    riesgo_crash = 100.0 - prob_exito

    c_prob1, c_prob2 = st.columns(2)
    c_prob1.metric("Probabilidad teórica", f"{prob_exito:.2f}%")
    c_prob2.metric("Riesgo de crash previo", f"{riesgo_crash:.2f}%")

    st.markdown("---")
    st.subheader("📝 Registrar Ronda Simple")
    col_reg1, col_reg2, col_reg3 = st.columns([2, 1, 1])
    
    with col_reg1:
        apuesta_real = st.number_input("Monto apostado ($):", value=float(apuesta_sug_simple), step=100.0, key="apuesta_simple_input")
    with col_reg2:
        st.write("")
        st.write("")
        if st.button("✅ Ganada", use_container_width=True, key="btn_gana_simple"):
            st.session_state.balance += apuesta_real * (objetivo_x - 1.0)
            st.session_state.historial_balance.append(st.session_state.balance)
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance)
            st.rerun()
    with col_reg3:
        st.write("")
        st.write("")
        if st.button("❌ Perdida", use_container_width=True, key="btn_pierde_simple"):
            st.session_state.balance -= apuesta_real
            st.session_state.historial_balance.append(st.session_state.balance)
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance)
            st.rerun()

    if len(st.session_state.historial_balance) > 1:
        st.line_chart(pd.DataFrame({"Balance": st.session_state.historial_balance}))

# ==========================================
# PESTAÑA 2: DOBLE APUESTA 3:1 MODIFICABLE
# ==========================================
with tabs[1]:
    st.title("🛡️ Cobertura Avanzada 3:1 (Ganancia Asegurada)")
    st.write("Configuración recomendada: Casilla 1 en **1.50x** y Casilla 2 en **2.00x**.")

    # CÁLCULO CON ESCALONES EXACTOS DE $100 COP (Sin decimales)
    apuesta_doble_total = st.session_state.balance * (riesgo_pct / 100)
    
    calc_c1 = apuesta_doble_total * 0.75
    calc_c2 = apuesta_doble_total * 0.25
    
    # Redondeo estricto hacia abajo a múltiplos de 100 (mínimos 1500 y 500)
    sug_c1 = max(1500.0, float(int(calc_c1 // 100) * 100))
    sug_c2 = max(500.0, float(int(calc_c2 // 100) * 100))

    col_d1, col_d2 = st.columns(2)
    col_d1.metric("Banca Actual", f"${st.session_state.balance:,.2f} COP")
    col_d2.metric("Inversión Total Redondeada", f"${(sug_c1 + sug_c2):,.0f} COP")

    st.markdown("### ✏️ Configuración Manual")
    col_inp1, col_inp2 = st.columns(2)
    with col_inp1:
        monto_c1 = st.number_input("Casilla 1 - Cobertura ($ COP):", value=float(sug_c1), step=100.0)
        auto_cash_c1 = st.number_input("Auto Cash-out Casilla 1 (x):", value=1.50, step=0.05)
    with col_inp2:
        monto_c2 = st.number_input("Casilla 2 - Multiplicador ($ COP):", value=float(sug_c2), step=100.0)
        auto_cash_c2 = st.number_input("Auto Cash-out Casilla 2 (x):", value=2.00, step=0.05)

    ganancia_c1_sola = (monto_c1 * (auto_cash_c1 - 1.0)) - monto_c2
    ganancia_ambas = (monto_c1 * (auto_cash_c1 - 1.0)) + (monto_c2 * (auto_cash_c2 - 1.0))
    perdida_total = monto_c1 + monto_c2

    st.markdown("#### 📊 Proyección de la Ronda:")
    st.info(f"- **Si cae entre {auto_cash_c1:.2f}x y {auto_cash_c2 - 0.01:.2f}x:** Ganancia de **+${ganancia_c1_sola:,.2f} COP**\n"
            f"- **Si supera {auto_cash_c2:.2f}x (Ambas cobradas):** Ganancia de **+${ganancia_ambas:,.2f} COP**\n"
            f"- **Si cae antes de {auto_cash_c1:.2f}x:** Pérdida total de **-${perdida_total:,.2f} COP**")

    st.markdown("---")
    st.subheader("📝 Registrar Resultado Doble")
    col_b1, col_b2, col_b3 = st.columns(3)
    
    with col_b1:
        if st.button(f"🏆 Superó {auto_cash_c2:.2f}x (Ambas)", use_container_width=True):
            st.session_state.balance += ganancia_ambas
            st.session_state.historial_balance.append(st.session_state.balance)
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance)
            st.rerun()
            
    with col_b2:
        if st.button(f"🛡️ Entre {auto_cash_c1:.2f}x y {auto_cash_c2:.2f}x", use_container_width=True):
            st.session_state.balance += ganancia_c1_sola
            st.session_state.historial_balance.append(st.session_state.balance)
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance)
            st.rerun()
            
    with col_b3:
        if st.button(f"💥 Menor a {auto_cash_c1:.2f}x (Pérdida)", use_container_width=True):
            st.session_state.balance -= perdida_total
            st.session_state.historial_balance.append(st.session_state.balance)
            guardar_datos_usuario(username, st.session_state.balance, banca_inicial, st.session_state.historial_balance)
            st.rerun()

    if len(st.session_state.historial_balance) > 1:
        st.caption("Evolución de la Banca")
        st.line_chart(pd.DataFrame({"Balance": st.session_state.historial_balance}))

# ==========================================
# PESTAÑA 3: ESCÁNER Y DETECTOR DE PATRONES
# ==========================================
with tabs[2]:
    st.subheader("📷 Escáner y Detector de Patrones (Filtro Anti-Trampa)")
    st.write("Sube la captura de la ventana de historial. El sistema reconoce la lectura natural de Aviator: arriba a la izquierda es la ronda actual.")
    
    uploaded_file = st.file_uploader("Subir captura del historial", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Historial cargado", use_container_width=True)
        
        texto_extraido = pytesseract.image_to_string(image)
        lineas_limpias = []
        for line in texto_extraido.split("\n"):
            if any(palabra in line.upper() for palabra in ["COP", "SALDO", "APUESTA", "GANANCIA", "HISTORIAL"]):
                continue
            lineas_limpias.append(line)
        texto_filtrado = "\n".join(lineas_limpias)

        matches = re.findall(r"(\d+[\.,]\d{1,2})\s*x?", texto_filtrado)
        
        multiplicadores = []
        for m in matches:
            try:
                val = float(m.replace(",", "."))
                if 1.00 <= val <= 999.0:
                    if val in [50.0, 500.0, 1500.0, 5000.0, 10000.0, 50000.0]:
                        continue
                    multiplicadores.append(val)
            except ValueError:
                continue
        
        if multiplicadores:
            r1_actual = multiplicadores[0]
            r2_anterior = multiplicadores[1] if len(multiplicadores) >= 2 else None
            r3_antepasada = multiplicadores[2] if len(multiplicadores) >= 3 else None

            n_muestra = min(6, len(multiplicadores))
            sub_muestra = multiplicadores[:n_muestra]
            crono_orden = list(reversed(sub_muestra))

            etiquetas_crono = [
                f"🟣 +{x:.2f}x" if x >= 2.00 else f"🔵 -{x:.2f}x" 
                for x in crono_orden
            ]

            st.markdown("### 🧩 Lectura Cronológica de Secuencia")
            st.write(f"**Camino recorrido (Pasado ➔ Ronda Actual que acaba de cerrar):**")
            st.subheader(" ➔ ".join(etiquetas_crono))
            
            st.markdown("---")
            
            actual_es_pos = r1_actual >= 2.00
            ant_es_pos = (r2_anterior is not None) and (r2_anterior >= 2.00)

            azules_previos = 0
            for x in multiplicadores[1:]:
                if x < 2.00:
                    azules_previos += 1
                else:
                    break

            if actual_es_pos and ant_es_pos:
                st.success(f"🟢 LUZ VERDE CONFIRMADA: Racha Positiva Sólida (+ / +)")
                st.write(f"**Diagnóstico:** El tiro actual fue **+{r1_actual:.2f}x** y el anterior **+{r2_anterior:.2f}x**. Se confirmó el ciclo morado. **Entra con la Doble Apuesta 3:1.**")

            elif actual_es_pos and not ant_es_pos:
                if azules_previos >= 3:
                    st.error(f"🛑 TRAMPA DE ABSORCIÓN DETECTADA: Morado Aislado tras {azules_previos} Azules (+{r1_actual:.2f}x)")
                    st.write(f"**Estrategia:** Venía un bloque denso de absorción ({azules_previos} caídas seguidas). Este primer morado suele ser un rebote en falso. **NO APOSTAR:** Espera obligatoriamente a que confirme un segundo morado consecutivo.")
                elif r1_actual >= 2.50:
                    st.success(f"🟢 ENTRADA MODERADA: Quiebre Fuerte (+{r1_actual:.2f}x)")
                    st.write(f"**Estrategia:** La fase fría previa fue corta ({azules_previos} azules) y el quiebre superó 2.50x. Hay probabilidad de continuación. **Entra con Doble Apuesta 3:1.**")
                else:
                    st.warning(f"🟡 PRECAUCIÓN: Morado Débil (+{r1_actual:.2f}x)")
                    st.write(f"**Estrategia:** El multiplicador apenas superó 2.00x (**+{r1_actual:.2f}x**). Riesgo elevado de falso quiebre. Espera 1 tiro de confirmación.")

            elif not actual_es_pos and ant_es_pos:
                if r1_actual >= 1.50:
                    st.warning(f"⚠️ FRENO DE EMERGENCIA: Azul Amortiguado (-{r1_actual:.2f}x)")
                    st.write(f"**Estrategia:** El tiro actual cayó en **{r1_actual:.2f}x** tras el morado anterior (+{r2_anterior:.2f}x). La Casilla 1 cobró (+250 COP), pero el flujo positivo se cortó. **Suspende inmediatamente las apuestas.**")
                else:
                    st.error(f"🔴 BLOQUEO TOTAL: Falso Quiebre Confirmado (-{r1_actual:.2f}x)")
                    st.write(f"**Estrategia:** El tiro actual cayó en **-{r1_actual:.2f}x** tras el morado anterior (+{r2_anterior:.2f}x). El morado fue una trampa de absorción. **Detén la operativa en seco**.")

            elif not actual_es_pos and not ant_es_pos:
                st.error(f"🔴 MANTENERSE QUIETO: Fase Fría Activa (- / -)")
                st.write(f"**Estrategia:** El algoritmo está en absorción activa (**-{r1_actual:.2f}x** y **-{r2_anterior:.2f}x**). No pongas apuestas.")

            st.markdown("---")
            total_r = len(multiplicadores)
            exitos_140 = sum(1 for x in multiplicadores if x >= 1.40)
            exitos_150 = sum(1 for x in multiplicadores if x >= 1.50)
            exitos_200 = sum(1 for x in multiplicadores if x >= 2.00)

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Frecuencia > 1.40x", f"{(exitos_140/total_r)*100:.1f}%")
            col_m2.metric("Frecuencia > 1.50x", f"{(exitos_150/total_r)*100:.1f}%")
            col_m3.metric("Frecuencia Positivos (≥ 2.00x)", f"{(exitos_200/total_r)*100:.1f}%")
            st.caption(f"Valores leídos del historial: {multiplicadores}")
        else:
            st.warning("No se detectaron multiplicadores legibles. Recorta solo la franja superior de números.")

# ==========================================
# PESTAÑA 4: MONTE CARLO
# ==========================================
with tabs[3]:
    st.subheader("🧪 Simulación Monte Carlo (500 Rondas)")
    banca_sim_input = st.number_input("Banca para simular ($):", value=float(banca_inicial), step=1000.0)
    rondas_sim = st.slider("Número de rondas:", min_value=10, max_value=500, value=50, step=10)
    cashout_sim = st.slider("Objetivo Cash-out (x):", min_value=1.05, max_value=5.00, value=1.40, step=0.01)
    
    estrategia = st.selectbox(
        "Estrategia de apuesta:",
        ["Porcentaje Fijo de Banca (Compounding)", "Monto Fijo (Flat Betting)", "Martingala (Doblar tras fallo)"]
    )
    
    if st.button("🚀 Ejecutar Simulación"):
        banca_actual = banca_sim_input
        registro = [banca_actual]
        apuesta_base = banca_sim_input * (riesgo_pct / 100)
        apuesta_actual = apuesta_base
        
        for _ in range(rondas_sim):
            if banca_actual <= 0:
                break
            
            r = np.random.uniform(0, 1)
            crash = max(1.0, np.floor((0.97 / (1.0 - r)) * 100) / 100)
            monto_a_jugar = min(apuesta_actual, banca_actual)
            
            if crash >= cashout_sim:
                banca_actual += monto_a_jugar * (cashout_sim - 1.0)
                if estrategia == "Martingala (Doblar tras fallo)":
                    apuesta_actual = apuesta_base
                elif estrategia == "Porcentaje Fijo de Banca (Compounding)":
                    apuesta_actual = banca_actual * (riesgo_pct / 100)
            else:
                banca_actual -= monto_a_jugar
                if estrategia == "Martingala (Doblar tras fallo)":
                    apuesta_actual = monto_a_jugar * 2.0
                elif estrategia == "Porcentaje Fijo de Banca (Compounding)":
                    apuesta_actual = banca_actual * (riesgo_pct / 100)
                    
            registro.append(banca_actual)
            
        st.line_chart(pd.DataFrame({"Balance": registro}))
        st.write(f"Resultado final: **${banca_actual:,.2f}**")
