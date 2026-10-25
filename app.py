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
riesgo_pct = st.sidebar.slider("Riesgo por ronda (%):", min_value=0.5, max_value=5.0, value=1.5, step=0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (% pérdida):", min_value=5, max_value=50, value=20)
take_profit_pct = st.sidebar.slider("Take Profit (% ganancia):", min_value=10, max_value=100, value=25)

if st.sidebar.button("Reiniciar Banca"):
    st.session_state.balance = float(banca_inicial)
    st.session_state.historial_balance = [float(banca_inicial)]
    st.rerun()

piso_sl = banca_inicial * (1 - stop_loss_pct / 100)
techo_tp = banca_inicial * (1 + take_profit_pct / 100)
apuesta_sug = st.session_state.balance * (riesgo_pct / 100)

tabs = st.tabs(["🟢 Panel en Vivo", "📷 Escáner y Semáforo de Entrada", "🧪 Monte Carlo"])

# ==========================================
# PESTAÑA 1: PANEL EN VIVO
# ==========================================
with tabs[0]:
    st.title("✈️ Analítica Cuantitativa & Simulación - Aviator")
    
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Banca Actual")
        dif_pct = ((st.session_state.balance - banca_inicial) / banca_inicial) * 100
        st.subheader(f"${st.session_state.balance:,.2f}")
        st.markdown(f"<span style='color: {'#00cc96' if dif_pct >= 0 else '#ff4b4b'}; font-weight: bold;'>{'↑' if dif_pct >= 0 else '↓'} {dif_pct:+.2f}%</span>", unsafe_allow_html=True)

    with col2:
        st.caption("Apuesta Sugerida")
        st.subheader(f"${apuesta_sug:,.2f}")

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

    # Calculadora en Vivo
    st.subheader("🎯 Calculadora de Entrada en Vivo")
    objetivo_x = st.slider("Objetivo de retiro planeado (x):", min_value=1.05, max_value=5.00, value=1.40, step=0.01)
    
    prob_exito = (0.97 / objetivo_x) * 100
    riesgo_crash = 100.0 - prob_exito

    c_prob1, c_prob2 = st.columns(2)
    c_prob1.metric("Probabilidad teórica", f"{prob_exito:.2f}%")
    c_prob2.metric("Riesgo de crash previo", f"{riesgo_crash:.2f}%")

    st.markdown("---")
    
    # Registro de rondas
    st.subheader("📝 Registrar Resultado de Ronda")
    col_reg1, col_reg2, col_reg3 = st.columns([2, 1, 1])
    
    with col_reg1:
        apuesta_real = st.number_input("Monto apostado ($):", value=float(round(apuesta_sug, 2)), step=10.0)
    with col_reg2:
        st.write("")
        st.write("")
        if st.button("✅ Ganada", use_container_width=True):
            st.session_state.balance += apuesta_real * (objetivo_x - 1.0)
            st.session_state.historial_balance.append(st.session_state.balance)
            st.rerun()
    with col_reg3:
        st.write("")
        st.write("")
        if st.button("❌ Perdida", use_container_width=True):
            st.session_state.balance -= apuesta_real
            st.session_state.historial_balance.append(st.session_state.balance)
            st.rerun()

    if len(st.session_state.historial_balance) > 1:
        st.line_chart(pd.DataFrame({"Balance": st.session_state.historial_balance}))

# ==========================================
# PESTAÑA 2: ESCÁNER Y SEMÁFORO ENTRADA
# ==========================================
with tabs[1]:
    st.subheader("📷 Semáforo de Decisión según Historial")
    st.write("Sube la captura recortada del historial de rondas para recibir la señal del próximo turno.")
    
    uploaded_file = st.file_uploader("Subir captura de pantalla", type=["png", "jpg", "jpeg"])
    
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
            tasa_exito = (exitos_140 / total_rondas) * 100
            
            # Los últimos tiros del historial
            ultimos_3 = multiplicadores[-3:] if len(multiplicadores) >= 3 else multiplicadores
            crashes_ultimos_3 = sum(1 for x in ultimos_3 if x < 1.40)
            
            st.markdown("---")
            
            # LÓGICA DEL SEMÁFORO
            if crashes_ultimos_3 >= 2 or tasa_exito < 65.0:
                st.error("🔴 NO APOSTAR (ALTO RIESGO)")
                st.write(f"**Razón:** Concentración de caídas tempranas ({crashes_ultimos_3} de los últimos 3 tiros cayeron antes de 1.40x). Espera 1 o 2 tiros neutros.")
            else:
                st.success("🟢 SEÑAL VERDE: ENTRADA FAVORABLE A 1.40x")
                st.write(f"**Razón:** Racha estable. El {tasa_exito:.1f}% del historial superó el 1.40x y no hay cortes tempranos consecutivos.")

            st.markdown("---")
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Frecuencia > 1.40x", f"{tasa_exito:.1f}%", f"{exitos_140}/{total_rondas}")
            col_m2.metric("Fallos < 1.40x en últimos 3 tiros", f"{crashes_ultimos_3} de {len(ultimos_3)}")
            st.caption(f"Valores leídos: {multiplicadores}")
        else:
            st.warning("No se detectaron multiplicadores legibles. Asegúrate de recortar solo la franja superior de números.")

# ==========================================
# PESTAÑA 3: MONTE CARLO
# ==========================================
with tabs[2]:
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
            
        st.line_chart(pd.DataFrame({"Banca": registro}))
        st.write(f"Resultado final: **${banca_actual:,.2f}**")
        
