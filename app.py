import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Gestor Cuantitativo & Simulador - Aviator",
    page_icon="✈️",
    layout="wide"
)

# --- INICIALIZACIÓN DE VARIABLES DE ESTADO ---
if "banca_inicial" not in st.session_state:
    st.session_state.banca_inicial = 100.0
if "banca_actual" not in st.session_state:
    st.session_state.banca_actual = 100.0
if "historial_balance" not in st.session_state:
    st.session_state.historial_balance = [100.0]
if "historial_rondas" not in st.session_state:
    st.session_state.historial_rondas = []

# --- PANEL LATERAL: CONFIGURACIÓN GLOBAL ---
with st.sidebar:
    st.header("⚙️ Parámetros de Capital")
    
    banca_in = st.number_input(
        "Banca Inicial ($):", 
        min_value=10.0, 
        value=st.session_state.banca_inicial, 
        step=10.0
    )
    if banca_in != st.session_state.banca_inicial:
        st.session_state.banca_inicial = banca_in
        st.session_state.banca_actual = banca_in
        st.session_state.historial_balance = [banca_in]
        st.session_state.historial_rondas = []
        st.rerun()

    pct_riesgo = st.slider(
        "Riesgo por ronda (% banca):", 
        min_value=0.5, 
        max_value=5.0, 
        value=1.5, 
        step=0.5,
        help="Recomendado: 1% a 2% para absorber la varianza y evitar la ruina."
    )

    st.subheader("Límites de Seguridad (Stop)")
    stop_loss_pct = st.slider("Stop Loss (% pérdida máxima):", min_value=5, max_value=50, value=20)
    take_profit_pct = st.slider("Take Profit (% ganancia meta):", min_value=5, max_value=100, value=25)

    limite_piso = st.session_state.banca_inicial * (1 - stop_loss_pct / 100)
    limite_techo = st.session_state.banca_inicial * (1 + take_profit_pct / 100)

    if st.button("🔄 Reiniciar Sesión en Vivo"):
        st.session_state.banca_actual = st.session_state.banca_inicial
        st.session_state.historial_balance = [st.session_state.banca_inicial]
        st.session_state.historial_rondas = []
        st.rerun()

# --- EVALUACIÓN DE LÍMITES EN VIVO ---
bloqueo = False
alerta_texto = ""

if st.session_state.banca_actual <= limite_piso:
    bloqueo = True
    alerta_texto = f"🛑 STOP LOSS ALCANZADO (${st.session_state.banca_actual:.2f} <= ${limite_piso:.2f}). Detén la sesión inmediatamente."
elif st.session_state.banca_actual >= limite_techo:
    bloqueo = True
    alerta_texto = f"🎯 TAKE PROFIT ALCANZADO (${st.session_state.banca_actual:.2f} >= ${limite_techo:.2f}). Meta de ganancia alcanzada. Retira beneficios."

st.title("✈️ Analítica Cuantitativa & Simulación - Aviator")

# --- NAVEGACIÓN EN PESTAÑAS ---
tab_vivo, tab_simulador, tab_probabilidades = st.tabs([
    "🟢 Panel de Juego en Vivo", 
    "🧪 Simulador Monte Carlo (500 Rondas)", 
    "📊 Curva Teórica de Probabilidades"
])

# ==========================================
# PESTAÑA 1: PANEL EN VIVO
# ==========================================
with tab_vivo:
    c1, c2, c3, c4 = st.columns(4)
    apuesta_actual = round(st.session_state.banca_actual * (pct_riesgo / 100), 2) if not bloqueo else 0.0
    rendimiento = ((st.session_state.banca_actual - st.session_state.banca_inicial) / st.session_state.banca_inicial) * 100

    with c1:
        st.metric("Banca Actual", f"${st.session_state.banca_actual:.2f}", delta=f"{rendimiento:+.2f}%")
    with c2:
        st.metric("Apuesta Sugerida", f"${apuesta_actual:.2f}", help=f"Exactamente el {pct_riesgo}% de tu banca.")
    with c3:
        st.metric("Piso Stop Loss", f"${limite_piso:.2f}")
    with c4:
        st.metric("Techo Take Profit", f"${limite_techo:.2f}")

    if bloqueo:
        st.error(alerta_texto)

    st.write("---")

    col_izq, col_der = st.columns([1, 1])

    with col_izq:
        st.subheader("🎯 Calculadora de Entrada en Vivo")
        objetivo_mult = st.slider("Objetivo de retiro planeado (x):", min_value=1.10, max_value=5.00, value=1.40, step=0.05)
        
        prob_exito = min(100.0, (0.97 / objetivo_mult) * 100)
        prob_fallo = 100.0 - prob_exito

        m1, m2 = st.columns(2)
        m1.metric("Probabilidad de éxito", f"{prob_exito:.2f}%")
        m2.metric("Riesgo de crash previo", f"{prob_fallo:.2f}%")

        ev = (prob_exito / 100 * (objetivo_mult - 1)) - (prob_fallo / 100 * 1)
        st.caption(f"Valor Esperado (EV): **{ev:.3f}** por dólar apostado (Margen de la casa: -3%).")

    with col_der:
        st.subheader("📝 Registrar Ronda Jugada")
        with st.form("form_registro_vivo"):
            resultado = st.radio("Desenlace:", ["Cobro exitoso (Gané)", "El avión cayó antes (Perdí)"])
            mult_salida = st.number_input("Multiplicador al que cobraste:", min_value=1.01, value=objetivo_mult, step=0.05)
            crash_real = st.number_input("Multiplicador en el que cayó el avión:", min_value=1.00, value=1.50, step=0.01)
            btn_submit = st.form_submit_button("Actualizar Saldo", disabled=bloqueo)

            if btn_submit and not bloqueo:
                if "Gané" in resultado:
                    beneficio = round(apuesta_actual * (mult_salida - 1.0), 2)
                    st.session_state.banca_actual = round(st.session_state.banca_actual + beneficio, 2)
                else:
                    st.session_state.banca_actual = round(st.session_state.banca_actual - apuesta_actual, 2)
                
                st.session_state.historial_balance.append(st.session_state.banca_actual)
                st.session_state.historial_rondas.append(crash_real)
                st.rerun()

        st.caption("Evolución de la banca en vivo:")
        st.line_chart(st.session_state.historial_balance)

# ==========================================
# PESTAÑA 2: SIMULADOR MONTE CARLO
# ==========================================
with tab_simulador:
    st.subheader("🧪 Simulación de Monte Carlo (Generador Real Aviator - RTP 97%)")
    st.write(
        "Esta simulación genera 500 rondas utilizando el algoritmo oficial de Aviator. "
        "Permite comprobar matemáticamente cómo impactan la varianza, el margen del casino y las distintas estrategias en tu balance."
    )

    col_sim_cfg1, col_sim_cfg2, col_sim_cfg3 = st.columns(3)
    
    with col_sim_cfg1:
        sim_banca_ini = st.number_input("Banca para simular ($):", min_value=50.0, value=200.0, step=50.0)
        sim_num_rondas = st.slider("Número de rondas:", min_value=100, max_value=2000, value=500, step=50)

    with col_sim_cfg2:
        sim_objetivo = st.slider("Objetivo de Auto Cash-out (x):", min_value=1.10, max_value=5.00, value=1.35, step=0.05)
        sim_estrategia = st.selectbox(
            "Estrategia de apuesta:",
            [
                "Monto Fijo (Flat Betting)", 
                "Porcentaje Fijo de Banca (Compounding)", 
                "Martingala (Doblar tras fallo)"
            ]
        )

    with col_sim_cfg3:
        sim_apuesta_base = st.number_input("Apuesta inicial / base ($):", min_value=0.5, value=2.0, step=0.5)
        aplicar_stops = st.checkbox("Activar Stop Loss / Take Profit en la simulación", value=True)

    if st.button("🚀 Ejecutar Simulación"):
        u = np.random.uniform(0.0, 1.0, sim_num_rondas)
        denominador = 1.0 - u
        multiplicadores_sim = np.floor((0.97 / denominador) * 100) / 100
        multiplicadores_sim = np.maximum(1.00, multiplicadores_sim)

        banca = sim_banca_ini
        balance_hist = [banca]
        apuesta_actual_sim = sim_apuesta_base
        ganadas = 0
        perdidas = 0
        ronda_parada = sim_num_rondas
        motivo_parada = "Simulación completada con éxito."

        sim_stop_loss = sim_banca_ini * (1 - stop_loss_pct / 100)
        sim_take_profit = sim_banca_ini * (1 + take_profit_pct / 100)

        for i, crash in enumerate(multiplicadores_sim):
            if banca <= 0.5:
                ronda_parada = i
                motivo_parada = f"🛑 Quiebra total de la banca en la ronda {i+1}."
                break

            if aplicar_stops:
                if banca <= sim_stop_loss:
                    ronda_parada = i
                    motivo_parada = f"🛑 Stop Loss alcanzado en la ronda {i+1} (${banca:.2f})."
                    break
                elif banca >= sim_take_profit:
                    ronda_parada = i
                    motivo_parada = f"🎯 Take Profit alcanzado en la ronda {i+1} (${banca:.2f})."
                    break

            if sim_estrategia == "Monto Fijo (Flat Betting)":
                apuesta = min(sim_apuesta_base, banca)
            elif sim_estrategia == "Porcentaje Fijo de Banca (Compounding)":
                apuesta = min(round(banca * (pct_riesgo / 100), 2), banca)
            elif sim_estrategia == "Martingala (Doblar tras fallo)":
                apuesta = min(apuesta_actual_sim, banca)

            if crash >= sim_objetivo:
                ganadas += 1
                banca += apuesta * (sim_objetivo - 1.0)
                if sim_estrategia == "Martingala (Doblar tras fallo)":
                    apuesta_actual_sim = sim_apuesta_base
            else:
                perdidas += 1
                banca -= apuesta
                if sim_estrategia == "Martingala (Doblar tras fallo)":
                    apuesta_actual_sim *= 2

            banca = round(banca, 2)
            balance_hist.append(banca)

        st.write("---")
        st.subheader("Resultados de la Simulación")
        
        if banca > sim_banca_ini:
            st.success(f"{motivo_parada} Saldo final: **${banca:.2f}**")
        else:
            st.warning(f"{motivo_parada} Saldo final: **${banca:.2f}**")

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Saldo Inicial", f"${sim_banca_ini:.2f}")
        sc2.metric("Saldo Final", f"${banca:.2f}", delta=f"{((banca - sim_banca_ini)/sim_banca_ini)*100:+.2f}%")
        sc3.metric("Rondas Jugadas", f"{ronda_parada} de {sim_num_rondas}")
        tasa_acierto = (ganadas / (ganadas + perdidas)) * 100 if (ganadas + perdidas) > 0 else 0
        sc4.metric("Tasa de Aciertos Real", f"{tasa_acierto:.2f}%", help=f"Esperada teórica: {(0.97/sim_objetivo)*100:.2f}%")

        st.line_chart(balance_hist)

# ==========================================
# PESTAÑA 3: CURVA TEÓRICA DE PROBABILIDAD
# ==========================================
with tab_probabilidades:
    st.subheader("📊 Tabla Teórica y Curva de Probabilidad (RTP 97%)")
    st.write("Muestra la probabilidad matemática de que el avión alcance cada multiplicador sin caer antes:")

    multiplicadores_ref = [1.05, 1.10, 1.20, 1.30, 1.40, 1.50, 1.75, 2.00, 2.50, 3.00, 5.00, 10.00]
    datos_tabla = []
    for m in multiplicadores_ref:
        p = (0.97 / m) * 100
        datos_tabla.append({
            "Multiplicador": f"{m:.2f}x",
            "Probabilidad (%)": round(p, 2),
            "Riesgo de Crash previo (%)": round(100 - p, 2),
            "Frecuencia media": f"1 vez cada {(100/p):.1f} rondas"
        })

    df_p = pd.DataFrame(datos_tabla)
    st.dataframe(df_p, use_container_width=True)

    curva_x = np.linspace(1.05, 5.0, 50)
    curva_y = (0.97 / curva_x) * 100
    df_curva = pd.DataFrame({"Multiplicador": curva_x, "Probabilidad (%)": curva_y}).set_index("Multiplicador")
    st.line_chart(df_curva)
                  
