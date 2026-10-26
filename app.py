import streamlit as st
import numpy as np
import pandas as pd
import re
from PIL import Image
import pytesseract

st.set_page_config(page_title="Analítica Cuantitativa & Simulación - Aviator", layout="wide")

# Inicialización de variables
if 'balance' not in st.session_state:
    st.session_state.balance = 50000.0
if 'historial_balance' not in st.session_state:
    st.session_state.historial_balance = [50000.0]

# Barra lateral de configuración
st.sidebar.header("⚙️ Configuración de Parámetros")
banca_inicial = st.sidebar.number_input("Banca Inicial ($ / COP):", value=50000.0, step=1000.0)
riesgo_pct = st.sidebar.slider("Riesgo total por ronda (%):", min_value=0.5, max_value=6.0, value=4.0, step=0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (% pérdida):", min_value=5, max_value=50, value=20)
take_profit_pct = st.sidebar.slider("Take Profit (% ganancia):", min_value=10, max_value=100, value=25)

if st.sidebar.button("Reiniciar Banca"):
    st.session_state.balance = float(banca_inicial)
    st.session_state.historial_balance = [float(banca_inicial)]
    st.rerun()

piso_sl = banca_inicial * (1 - stop_loss_pct / 100)
techo_tp = banca_inicial * (1 + take_profit_pct / 100)
apuesta_sug_simple = st.session_state.balance * (riesgo_pct / 100)

# Pestañas de navegación
tabs = st.tabs([
    "🟢 Apuesta Simple", 
    "🛡️ Doble Apuesta (Estrategia 3:1)", 
    "📷 Escáner y Semáforos", 
    "🧪 Monte Carlo"
])

# ==========================================
# PESTAÑA 1: APUESTA SIMPLE EN VIVO
# ==========================================
with tabs[0]:
    st.title("✈️ Modo Apuesta Simple")
    
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Banca Actual")
        dif_pct = ((st.session_state.balance - banca_inicial) / banca_inicial) * 100
        st.subheader(f"${st.session_state.balance:,.2f}")
        st.markdown(f"<span style='color: {'#00cc96' if dif_pct >= 0 else '#ff4b4b'}; font-weight: bold;'>{'↑' if dif_pct >= 0 else '↓'} {dif_pct:+.2f}%</span>", unsafe_allow_html=True)

    with col2:
        st.caption("Apuesta Sugerida")
        st.subheader(f"${apuesta_sug_simple:,.2f}")

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

    st.subheader("🎯 Calculadora Simple en Vivo")
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
        apuesta_real = st.number_input("Monto apostado ($):", value=float(round(apuesta_sug_simple, 2)), step=50.0, key="apuesta_simple_input")
    with col_reg2:
        st.write("")
        st.write("")
        if st.button("✅ Ganada", use_container_width=True, key="btn_gana_simple"):
            st.session_state.balance += apuesta_real * (objetivo_x - 1.0)
            st.session_state.historial_balance.append(st.session_state.balance)
            st.rerun()
    with col_reg3:
        st.write("")
        st.write("")
        if st.button("❌ Perdida", use_container_width=True, key="btn_pierde_simple"):
            st.session_state.balance -= apuesta_real
            st.session_state.historial_balance.append(st.session_state.balance)
            st.rerun()

    if len(st.session_state.historial_balance) > 1:
        st.line_chart(pd.DataFrame({"Balance": st.session_state.historial_balance}))

# ==========================================
# PESTAÑA 2: DOBLE APUESTA 3:1 MODIFICABLE
# ==========================================
with tabs[1]:
    st.title("🛡️ Estrategia Doble Apuesta 3:1 (Ganancia Asegurada)")
    st.write("Configuración recomendada: Casilla 1 en **1.50x** y Casilla 2 en **2.00x**. Puedes modificar los montos manualmente según el saldo disponible.")

    # Cálculo automático proporcional 3:1 por defecto (3/4 y 1/4)
    apuesta_doble_total = st.session_state.balance * (riesgo_pct / 100)
    sug_c1 = round((apuesta_doble_total * 0.75), 2)
    sug_c2 = round((apuesta_doble_total * 0.25), 2)

    col_d1, col_d2 = st.columns(2)
    col_d1.metric("Banca Actual", f"${st.session_state.balance:,.2f} COP")
    col_d2.metric("Inversión Sugerida Total", f"${(sug_c1 + sug_c2):,.2f} COP")

    st.markdown("### ✏️ Configuración Manual de Apuestas")
    col_inp1, col_inp2 = st.columns(2)
    with col_inp1:
        monto_c1 = st.number_input("Casilla 1 - Cobertura ($ COP):", value=float(sug_c1 if sug_c1 > 0 else 1500.0), step=100.0)
        auto_cash_c1 = st.number_input("Auto Cash-out Casilla 1 (x):", value=1.50, step=0.05)
    with col_inp2:
        monto_c2 = st.number_input("Casilla 2 - Multiplicador ($ COP):", value=float(sug_c2 if sug_c2 > 0 else 500.0), step=100.0)
        auto_cash_c2 = st.number_input("Auto Cash-out Casilla 2 (x):", value=2.00, step=0.05)

    # Cálculo de ganancias proyectadas
    ganancia_c1_sola = (monto_c1 * (auto_cash_c1 - 1.0)) - monto_c2
    ganancia_ambas = (monto_c1 * (auto_cash_c1 - 1.0)) + (monto_c2 * (auto_cash_c2 - 1.0))
    perdida_total = monto_c1 + monto_c2

    st.markdown("#### 📊 Proyección con los valores actuales:")
    st.info(f"- **Si cae entre {auto_cash_c1:.2f}x y {auto_cash_c2 - 0.01:.2f}x:** Ganancia neta de **+${ganancia_c1_sola:,.2f} COP**\n"
            f"- **Si supera {auto_cash_c2:.2f}x (Ambas cobradas):** Ganancia neta de **+${ganancia_ambas:,.2f} COP**\n"
            f"- **Si cae antes de {auto_cash_c1:.2f}x:** Pérdida total de **-${perdida_total:,.2f} COP**")

    st.markdown("---")
    st.subheader("📝 Registrar Resultado de la Ronda Doble")
    
    col_b1, col_b2, col_b3 = st.columns(3)
    
    with col_b1:
        if st.button(f"🏆 Superó {auto_cash_c2:.2f}x (Ambas)", use_container_width=True):
            st.session_state.balance += ganancia_ambas
            st.session_state.historial_balance.append(st.session_state.balance)
            st.rerun()
            
    with col_b2:
        if st.button(f"🛡️ Entre {auto_cash_c1:.2f}x y {auto_cash_c2:.2f}x", use_container_width=True):
            st.session_state.balance += ganancia_c1_sola
            st.session_state.historial_balance.append(st.session_state.balance)
            st.rerun()
            
    with col_b3:
        if st.button(f"💥 Menor a {auto_cash_c1:.2f}x (Pérdida)", use_container_width=True):
            st.session_state.balance -= perdida_total
            st.session_state.historial_balance.append(st.session_state.balance)
            st.rerun()

    if len(st.session_state.historial_balance) > 1:
        st.caption("Evolución de la Banca")
        st.line_chart(pd.DataFrame({"Balance": st.session_state.historial_balance}))

# ==========================================
# PESTAÑA 3: ESCÁNER Y SEMÁFOROS
# ==========================================
with tabs[2]:
    st.subheader("📷 Semáforos de Entrada Inteligentes")
    st.write("Sube la captura recortada del historial de Aviator para evaluar las condiciones de entrada.")
    
    uploaded_file = st.file_uploader("Subir captura del historial", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Historial cargado", use_container_width=True)
        
        texto_extraido = pytesseract.image_to_string(image)
        matches = re.findall(r"(\d+[\.,]\d+)x?", texto_extraido)
        
        multiplicadores = []
        for m in matches:
            val = float(m.replace(",", "."))
            if 1.0 <= val <= 1000.0:
                multiplicadores.append(val)
        
        if multiplicadores:
            total_rondas = len(multiplicadores)
            exitos_140 = sum(1 for x in multiplicadores if x >= 1.40)
            tasa_140 = (exitos_140 / total_rondas) * 100
            
            exitos_150 = sum(1 for x in multiplicadores if x >= 1.50)
            tasa_150 = (exitos_150 / total_rondas) * 100
            
            exitos_200 = sum(1 for x in multiplicadores if x >= 2.00)
            tasa_200 = (exitos_200 / total_rondas) * 100
            
            ultimos_3 = multiplicadores[-3:] if len(multiplicadores) >= 3 else multiplicadores
            crashes_ultimos_3 = sum(1 for x in ultimos_3 if x < 1.40)
            crashes_150_ultimos_3 = sum(1 for x in ultimos_3 if x < 1.50)

            st.markdown("---")
            col_sem1, col_sem2 = st.columns(2)
            
            with col_sem1:
                st.markdown("#### 🎯 Para Apuesta Simple (1.40x)")
                if crashes_ultimos_3 >= 2 or tasa_140 < 65.0:
                    st.error("🔴 NO APOSTAR (Alto Riesgo)")
                    st.caption("Cortes rápidos inmediatos detectados.")
                else:
                    st.success("🟢 LUZ VERDE SIMPLE")
                    st.caption(f"Frecuencia > 1.40x: {tasa_140:.1f}%. Flujo estable.")

            with col_sem2:
                st.markdown("#### 🛡️ Para Doble Apuesta (1.50x / 2.00x)")
                if crashes_150_ultimos_3 >= 2 or tasa_150 < 60.0:
                    st.error("🔴 ESPERAR PARA DOBLE APUESTA")
                    st.caption("Racha fría con caídas antes de 1.50x. Espera 1 o 2 rondas neutras.")
                else:
                    st.success("🟢 LUZ VERDE DOBLE APUESTA")
                    st.caption(f"Frecuencia > 1.50x: {tasa_150:.1f}% | Frecuencia > 2.00x: {tasa_200:.1f}%.")

            st.markdown("---")
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Frecuencia > 1.40x", f"{tasa_140:.1f}%")
            col_m2.metric("Frecuencia > 1.50x", f"{tasa_150:.1f}%")
            col_m3.metric("Frecuencia > 2.00x", f"{tasa_200:.1f}%")
            st.caption(f"Valores leídos: {multiplicadores}")
        else:
            st.warning("No se detectaron multiplicadores legibles. Recorta solo la franja superior.")

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
