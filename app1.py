import streamlit as st
import math
import numpy as np
import matplotlib.pyplot as plt

# =========================================================
# 1. FUNÇÕES DE CÁLCULO BACKEND
# =========================================================
def calcular_diametro_asme(M_max, T, Se=30000, Sy=60000, ns=2.0):
    """
    Equação de Fadiga ASME / Von Mises (Distorção) para Eixos Rotativos.
    """
    termo_flexao = (M_max / Se) ** 2
    termo_torcao = 0.75 * ((T / Sy) ** 2)
    dentro_raiz = math.sqrt(termo_flexao + termo_torcao)
    d = ((32 * ns / math.pi) * dentro_raiz) ** (1 / 3)
    return d

# =========================================================
# 2. CONFIGURAÇÃO DA INTERFACE DO STREAMLIT
# =========================================================
st.set_page_config(page_title="Dimensionamento de Eixos", layout="wide")
st.title("⚙️ Calculadora Dinâmica de Eixos e Mancais")
st.markdown("Insira os parâmetros na barra lateral para dimensionar o eixo e gerar os diagramas de esforços.")

# --- BARRA LATERAL (Inputs do Usuário) ---
st.sidebar.header("Parâmetros do Motor")
n = st.sidebar.number_input("Rotação (RPM)", min_value=1, value=550, step=10)
P = st.sidebar.number_input("Potência (HP)", min_value=0.1, value=30.0, step=1.0)

st.sidebar.header("Parâmetros da Engrenagem B (z=10)")
num_dentes = st.sidebar.number_input("Número de Dentes (Z)", min_value=10, value=96, step=1)
passo_diametral = st.sidebar.number_input("Passo Diametral (Pd)", min_value=1.0, value=6.0, step=0.5)

st.sidebar.header("Material e Segurança")
material_Sy = st.sidebar.number_input("Limite de Escoamento (Sy - psi)", value=60000)
material_Se = st.sidebar.number_input("Limite de Fadiga (Se - psi)", value=30000)
fator_seg = st.sidebar.number_input("Fator de Segurança (ns)", value=2.0)

# =========================================================
# 3. LÓGICA DE PROCESSAMENTO E ESTÁTICA
# =========================================================
if st.button("Calcular e Gerar Relatório", type="primary"):
    
    # --- A. Torque ---
    T = (P * 63025) / n
    
    # --- B. Geometria e Forças na Engrenagem B (z = 10 pol) ---
    diametro_primitivo = num_dentes / passo_diametral
    R_B = diametro_primitivo / 2.0
    F_tB = T / R_B 
    F_rB = F_tB * math.tan(math.radians(20))
    
    # --- C. Forças na Polia D (z = 26 pol) ---
    R_D = 5.0 # Raio fixo do exercício
    F_tD = T / R_D
    F_D = 1.5 * F_tD
    F_Dx = F_D * math.cos(math.radians(40))
    F_Dy = -F_D * math.sin(math.radians(40))
    
    # --- D. Reações de Apoio (Mancais em z=0 e z=20) ---
    # Plano XZ
    R_Cx = -((F_tB * 10) + (F_Dx * 26)) / 20
    R_Ax = -(F_tB + F_Dx + R_Cx)
    
    # Plano YZ
    R_Cy = -((-F_rB * 10) + (F_Dy * 26)) / 20
    R_Ay = -(-F_rB + F_Dy + R_Cy)
    
    # --- E. Momento Máximo (Seção C, z=20) ---
    M_yC = (R_Ax * 20) + (F_tB * 10)
    M_xC = (-R_Ay * 20) - (F_rB * 10)
    M_max = math.sqrt(M_yC**2 + M_xC**2)
    
    # --- F. Dimensionamento ASME ---
    d_min = calcular_diametro_asme(M_max, T, material_Se, material_Sy, fator_seg)

    # =========================================================
    # 4. EXIBIÇÃO DE RESULTADOS NA TELA
    # =========================================================
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Torque no Eixo", f"{T:.2f} lb.pol")
    col2.metric("Raio da Engrenagem (Rb)", f"{R_B:.2f} pol")
    col3.metric("Momento Fletor Máx", f"{M_max:.2f} lb.pol")
    col4.metric("Diâmetro Mínimo ASME", f"{d_min:.2f} pol")

    st.subheader("📋 Relatório de Reações nos Mancais")
    col_A, col_C = st.columns(2)
    with col_A:
        st.write("**Mancal A (Origem, z = 0 pol):**")
        st.write(f"Reação em X (RAx): `{R_Ax:.2f} lb`")
        st.write(f"Reação em Y (RAy): `{R_Ay:.2f} lb`")
    with col_C:
        st.write("**Mancal C (Apoio, z = 20 pol):**")
        st.write(f"Reação em X (RCx): `{R_Cx:.2f} lb`")
        st.write(f"Reação em Y (RCy): `{R_Cy:.2f} lb`")

    # =========================================================
    # 5. GERADOR DINÂMICO DE GRÁFICOS (Plano XZ)
    # =========================================================
    st.markdown("---")
    st.subheader("📊 Diagramas de Esforços Internos (Plano XZ)")
    
    # Vetor de discretização do comprimento do eixo (de 0 a 26 polegadas)
    z_vals = np.linspace(0, 26.0, 1000)
    
    # Cálculo usando Funções de Singularidade (Macaulay)
    # O Cortante soma as cargas pontuais. O Fletor integra (Força * braço de alavanca)
    V_x = np.zeros_like(z_vals)
    M_y = np.zeros_like(z_vals)
    
    # 1. Contribuição do Mancal A (z=0)
    V_x += R_Ax * (z_vals >= 0)
    M_y += R_Ax * (z_vals - 0) * (z_vals >= 0)
    
    # 2. Contribuição da Engrenagem B (z=10)
    V_x += F_tB * (z_vals >= 10)
    M_y += F_tB * (z_vals - 10) * (z_vals >= 10)
    
    # 3. Contribuição do Mancal C (z=20)
    V_x += R_Cx * (z_vals >= 20)
    M_y += R_Cx * (z_vals - 20) * (z_vals >= 20)
    
    # Criando a figura do Matplotlib
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # Gráfico 1: Cortante
    ax1.plot(z_vals, V_x, color='blue', drawstyle='steps-post')
    ax1.fill_between(z_vals, V_x, step="post", alpha=0.2, color='blue')
    ax1.axhline(0, color='black', linewidth=1)
    ax1.set_ylabel("Força Cortante Vx (lb)")
    ax1.set_title("Diagrama de Esforço Cortante (V)")
    ax1.grid(True, linestyle='--', alpha=0.6)
    
    # Gráfico 2: Fletor
    ax2.plot(z_vals, M_y, color='red')
    ax2.fill_between(z_vals, M_y, alpha=0.2, color='red')
    ax2.axhline(0, color='black', linewidth=1)
    ax2.set_xlabel("Comprimento do Eixo - Eixo Z (pol)")
    ax2.set_ylabel("Momento Fletor My (lb.pol)")
    ax2.set_title("Diagrama de Momento Fletor (M)")
    ax2.grid(True, linestyle='--', alpha=0.6)
    
    # Marcadores de posição dos componentes
    for ax in [ax1, ax2]:
        ax.axvline(10, color='gray', linestyle=':', label='Engrenagem B')
        ax.axvline(20, color='green', linestyle=':', label='Mancal C')
        ax.axvline(26, color='orange', linestyle=':', label='Polia D')
    
    # Legenda apenas no gráfico de baixo para não poluir
    ax2.legend(loc='upper right')
    
    plt.tight_layout()
    st.pyplot(fig)
