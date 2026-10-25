import streamlit as st
import numpy as np
import pandas as pd
import re
from PIL import Image
import pytesseract

st.set_page_config(page_title="Panel Cuantitativo Aviator", layout="wide")

# Inicialización de estado
if 'balance' not in st.session_state:
    st.session_state.balance = 50000.0
if 'historial' not in st.session_state:
    st.session_state.historial = []

st.sidebar.header("⚙️ Configuración de Banca")
banca_inicial = st.sidebar.number_input("Banca Inicial (COP):", value=50000.0, step=1000.0)
riesgo_pct = st.sidebar.slider("Riesgo por ronda (%):", min_value=0.5, max_value=5.0, value=1.5, step=0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (% pérdida):", min_value=5, max_value=50, value=20)
take_profit_pct = st.sidebar.slider("Take Profit (% ganancia):", min_value=10, max_value=100, value=25)

piso_sl = banca_inicial * (1 - stop_loss_pct / 100)
techo_tp = banca_inicial * (1 + take_profit_pct / 100)
apuesta_sug = st.session_state.balance * (riesgo_pct / 100)

tabs = st.tabs(["🟢 Panel en Vivo", "📷 Escanear Historial", "🧪 Monte Carlo"])

# TAB 1: Panel en Vivo
with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Banca Actual", f"${st.session_state.balance:,.2f} COP")
    col2.metric("Apuesta Sugerida", f"${apuesta_sug:,.2f} COP")
    col3.metric("Piso Stop Loss", f"${piso_sl:,.2f} COP")
    col4.metric("Techo Take Profit", f"${techo_tp:,.2f} COP")

    if st.session_state.balance <= piso_sl:
        st.error("🛑 STOP LOSS ALCANZADO: Cierra la sesión inmediatamente.")
    elif st.session_state.balance >= techo_tp:
        st.success("🎯 TAKE PROFIT ALCANZADO: Retira tus ganancias y finaliza.")

# TAB 2: Escaneo de Captura y Análisis de Rachas
with tabs[1]:
    st.subheader("Análisis de Rachas y Detección de Multiplicadores")
    st.write("Sube una captura de la barra superior de Aviator para calcular la frecuencia de 1.40x y rachas frías/moradas.")
    
    uploaded_file = st.file_uploader("Subir captura de pantalla", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Captura cargada", use_container_width=True)
        
        # Procesamiento OCR para extraer números tipo "1.40x", "2.10x"
        texto_extraido = pytesseract.image_to_string(image)
        # Extraer números decimales acompañados o no de 'x'
        matches = re.findall(r"(\d+[\.,]\d+)x?", texto_extraido)
        
        multiplicadores = []
        for m in matches:
            val = float(m.replace(",", "."))
            if 1.0 <= val <= 1000.0:  # Filtro de rango válido
                multiplicadores.append(val)
        
        if multiplicadores:
            st.success(f"Se detectaron {len(multiplicadores)} multiplicadores en el historial.")
            st.write(f"**Valores leídos:** {multiplicadores}")
            
            # Métricas sobre el umbral 1.40x
            exitos_140 = sum(1 for x in multiplicadores if x >= 1.40)
            tasa_exito = (exitos_140 / len(multiplicadores)) * 100
            
            # Análisis de los últimos 5 tiros
            ultimos_5 = multiplicadores[:5] if len(multiplicadores) >= 5 else multiplicadores
            crashes_bajos_5 = sum(1 for x in ultimos_5 if x < 1.40)
            
            col_a, col_b = st.columns(2)
            col_a.metric("Frecuencia > 1.40x en historial", f"{tasa_exito:.1f}%", f"{exitos_140}/{len(multiplicadores)}")
            col_b.metric("Crashes < 1.40x en últimos 5", f"{crashes_bajos_5} de {len(ultimos_5)}")
            
            # Semáforo de decisión
            if crashes_bajos_5 >= 3:
                st.warning("⚠️ Racha Fría Activa: Alta concentración de cortes antes de 1.40x. Conviene esperar 2 rondas neutras.")
            elif crashes_bajos_5 == 0:
                st.info("🟣 Racha Morada / Alta Densidad: El flujo reciente supera 1.40x de forma consecutiva.")
            else:
                st.success("✅ Entorno Estable: Frecuencia dentro del promedio estadístico.")
        else:
            st.warning("No se detectaron multiplicadores legibles. Puedes ingresarlos manualmente abajo.")
            
    manual_input = st.text_input("O escribe los multiplicadores separados por coma (ej: 1.19, 2.41, 1.37, 4.87):")
    if manual_input:
        valores_man = [float(v.strip()) for v in manual_input.split(",") if v.strip()]
        if valores_man:
            exitos = sum(1 for x in valores_man if x >= 1.40)
            st.write(f"**Efectividad sobre 1.40x:** {(exitos/len(valores_man))*100:.1f}% ({exitos} de {len(valores_man)} rondas)")

# TAB 3: Simulación Monte Carlo
with tabs[2]:
    st.subheader("Laboratorio Monte Carlo (RTP 97%)")
    rondas = st.slider("Número de rondas:", 50, 500, 100)
    cashout = st.number_input("Auto Cash-out:", value=1.40, step=0.05)
    
    if st.button("Ejecutar Simulación"):
        banca_sim = banca_inicial
        camino = [banca_sim]
        for _ in range(rondas):
            # Generador provably fair aproximado (RTP 97%)
            r = np.random.uniform(0, 1)
            crash = 0.97 / (1.0 - r)
            crash = max(1.0, np.floor(crash * 100) / 100)
            
            apuesta = banca_sim * (riesgo_pct / 100)
            if crash >= cashout:
                banca_sim += apuesta * (cashout - 1)
            else:
                banca_sim -= apuesta
            camino.append(banca_sim)
        
        st.line_chart(pd.DataFrame({"Banca": camino}))
        st.write(f"Banca final simulada: **${banca_sim:,.2f} COP**")
        
