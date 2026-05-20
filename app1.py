import streamlit as st
import math
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# 1. FUNÇÕES DE CÁLCULO (Seu backend)
# ---------------------------------------------------------
def calcular_diametro_asme(M_max, T, Se=30000, Sy=60000, ns=2.0):
    termo_flexao = (M_max / Se) ** 2
    termo_torcao = 0.75 * ((T / Sy) ** 2)
    dentro_raiz = math.sqrt(termo_flexao + termo_torcao)
    d = ((32 * ns / math.pi) * dentro_raiz) ** (1 / 3)
    return d

# ---------------------------------------------------------
# 2. INTERFACE DE USUÁRIO (Frontend Streamlit)
# ---------------------------------------------------------
st.set_page_config(page_title="Dimensionamento de Eixos", layout="wide")
st.title("⚙️ Calculadora de Eixos Rotativos e Mancais")
st.markdown("Insira os parâmetros abaixo para gerar o relatório de reações e os gráficos de esforços.")

# Barra lateral para Inputs
st.sidebar.header("Parâmetros de Entrada")
n = st.sidebar.number_input("Rotação (RPM)", min_value=1, value=550, step=10)
P = st.sidebar.number_input("Potência (HP)", min_value=0.1, value=30.0, step=1.0)
material_Sy = st.sidebar.number_input("Limite de Escoamento (Sy - psi)", value=60000)
material_Se = st.sidebar.number_input("Limite de Fadiga (Se - psi)", value=30000)
fator_seg = st.sidebar.number_input("Fator de Segurança (ns)", value=2.0)

# ---------------------------------------------------------
# 3. PROCESSAMENTO E RELATÓRIO
# ---------------------------------------------------------
if st.button("Calcular e Gerar Relatório"):
    # Lógica baseada no seu "Exercício 1"
    T = (P * 63025) / n
    
    # Exibindo resultados em colunas para ficar elegante
    col1, col2, col3 = st.columns(3)
    col1.metric("Torque Nominal", f"{T:.2f} lb.pol")
    
    # --- Aqui você insere as suas lógicas de cálculo de reações (RAx, RCx, etc) ---
    # Para simplificar o exemplo, vamos estipular valores fictícios baseados na sua lógica
    R_Ax, R_Ay = 150.5, -50.2 
    R_Cx, R_Cy = -300.0, 120.4
    M_max = 4500.0 # Valor calculado da seção crítica
    
    col2.metric("Momento Fletor Máximo", f"{M_max:.2f} lb.pol")
    
    d_min = calcular_diametro_asme(M_max, T, material_Se, material_Sy, fator_seg)
    col3.metric("Diâmetro Mínimo (ASME)", f"{d_min:.2f} pol")

    st.subheader("📋 Relatório de Reações nos Mancais")
    st.write(f"**Mancal A (z=0):** Rx = {R_Ax:.2f} lb | Ry = {R_Ay:.2f} lb")
    st.write(f"**Mancal C (z=20):** Rx = {R_Cx:.2f} lb | Ry = {R_Cy:.2f} lb")

# ---------------------------------------------------------
# 4. GERANDO OS GRÁFICOS (Momento Fletor e Esforço Cortante)
# ---------------------------------------------------------
    st.subheader("📊 Diagramas de Esforços Internos")
    
    # Para traçar o gráfico, você precisa criar um vetor de posições (z)
    comprimento_eixo = 26.0
    z = np.linspace(0, comprimento_eixo, 500)
    
    # LÓGICA DO GRÁFICO (Exemplo genérico - Você precisará usar as funções de Macaulay)
    # Aqui criamos um vetor de momento fletor fictício para demonstração
    momento_y = np.piecewise(z, [z < 10, (z >= 10) & (z < 20), z >= 20], 
                             [lambda z: 15*z, lambda z: 150 - 5*(z-10), lambda z: 100 - 10*(z-20)])
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(z, momento_y, label="Momento Fletor (Plano XZ)", color='red')
    ax.fill_between(z, momento_y, alpha=0.2, color='red')
    ax.axhline(0, color='black', linewidth=1)
    ax.set_xlabel("Comprimento do Eixo (pol)")
    ax.set_ylabel("Momento (lb.pol)")
    ax.set_title("Diagrama de Momento Fletor")
    ax.legend()
    ax.grid(True)
    
    # Renderiza o gráfico no Streamlit
    st.pyplot(fig)