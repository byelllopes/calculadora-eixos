import streamlit as st
import math
import numpy as np
import matplotlib.pyplot as plt

# =========================================================
# 1. FUNÇÃO ADMISSÍVEL ASME (VON MISES / FADIGA)
# =========================================================
def calcular_diametro_asme(M_max, T, Se=30000, Sy=60000, ns=2.0):
    termo_flexao = (M_max / Se) ** 2
    termo_torcao = 0.75 * ((T / Sy) ** 2)
    dentro_raiz = math.sqrt(termo_flexao + termo_torcao)
    d = ((32 * ns / math.pi) * dentro_raiz) ** (1 / 3)
    return d

# =========================================================
# 2. CONFIGURAÇÃO DA PÁGINA E MENU LATERAL
# =========================================================
st.set_page_config(page_title="Software de Eixos - UESC", layout="wide")

st.sidebar.markdown("# 🎓 UESC - Engenharia Mecânica")
st.sidebar.markdown("### Disciplina: Elementos de Máquinas I")
st.sidebar.markdown("**Prof.: Dr. José Carlos de Camargo**")
st.sidebar.markdown("---")

# Seletor central de Exercícios
exercicio = st.sidebar.selectbox(
    "Selecione o Exercício da Lista:",
    ["Exercício 1", "Exercício 2", "Exercício 3", "Exercício 4"]
)

# =========================================================
# 3. INTERFACE E LÓGICA DO EXERCÍCIO 1 & 2
# =========================================================
if exercicio in ["Exercício 1", "Exercício 2"]:
    st.title(f"⚙️ Resolução Automatizada - {exercicio}")
    st.markdown("Dimensionamento do eixo rotativo com engrenagem de dentes retos e polia em V.")
    
    # Configurações padrão mudam conforme o exercício selecionado
    if exercicio == "Exercício 1":
        default_n, default_P, default_Z, default_D_polia = 550, 30.0, 96, 10.0
    else:
        default_n, default_P, default_Z, default_D_polia = 750, 20.0, 100, 9.0

    # Inputs na barra lateral
    st.sidebar.header("Parâmetros de Entrada")
    n = st.sidebar.number_input("Rotação (RPM)", min_value=1, value=default_n)
    P = st.sidebar.number_input("Potência Total (HP)", min_value=0.1, value=default_P)
    Z = st.sidebar.number_input("Número de Dentes da Engrenagem B", min_value=1, value=default_Z)
    Pd = st.sidebar.number_input("Passo Diametral (Pd)", min_value=1.0, value=6.0)
    D_polia = st.sidebar.number_input("Diâmetro da Polia D (pol)", min_value=1.0, value=default_D_polia)
    
    st.sidebar.header("Propriedades do Material")
    Sy = st.sidebar.number_input("Limite de Escoamento (Sy - psi)", value=60000)
    Se = st.sidebar.number_input("Limite de Fadiga (Se - psi)", value=30000)
    ns = st.sidebar.number_input("Fator de Segurança (ns)", value=2.0)

    if st.button("Executar Análise Completa", type="primary"):
        # 1. Torque
        T = (P * 63025) / n
        
        # 2. Forças Engrenagem B (z = 10 pol)
        R_B = (Z / Pd) / 2.0
        F_tB = T / R_B
        F_rB = F_tB * math.tan(math.radians(20))
        
        # 3. Forças Polia D (z = 26 pol)
        R_D = D_polia / 2.0
        F_tD = T / R_D
        F_D = 1.5 * F_tD
        F_Dx = F_D * math.cos(math.radians(40))
        F_Dy = -F_D * math.sin(math.radians(40))
        
        # 4. Equilíbrio Estático (Mancais A em z=0 e C em z=20)
        R_Cx = -((F_tB * 10) + (F_Dx * 26)) / 20
        R_Ax = -(F_tB + F_Dx + R_Cx)
        
        R_Cy = -((-F_rB * 10) + (F_Dy * 26)) / 20
        R_Ay = -(-F_rB + F_Dy + R_Cy)
        
        # Seção Crítica C (z = 20 pol)
        M_yC = (R_Ax * 20) + (F_tB * 10)
        M_xC = (-R_Ay * 20) - (F_rB * 10)
        M_max = math.sqrt(M_yC**2 + M_xC**2)
        
        # Dimensionamento
        d_min = calcular_diametro_asme(M_max, T, Se, Sy, ns)
        
        # Exibição de Resultados
        st.markdown("---")
        metrics = st.columns(4)
        metrics[0].metric("Torque Nominal", f"{T:.1f} lb.pol")
        metrics[1].metric("Força Tangencial FtB", f"{F_tB:.1f} lb")
        metrics[2].metric("Momento Resultante Máx", f"{M_max:.1f} lb.pol")
        metrics[3].metric("Diâmetro Mínimo Requerido", f"{d_min:.3f} pol")
        
        # Relatório de Reações
        st.subheader("📋 Reações de Apoio nos Rolamentos")
        cols = st.columns(2)
        cols[0].info(f"**Mancal A (z = 0 pol):**\n\nReação X: {R_Ax:.2f} lb\n\nReação Y: {R_Ay:.2f} lb")
        cols[1].info(f"**Mancal C (z = 20 pol):**\n\nReação X: {R_Cx:.2f} lb\n\nReação Y: {R_Cy:.2f} lb")
        
       # Gráficos usando Macaulay
        st.subheader("📊 Diagramas de Esforços Solicitantes (Plano XZ)")
        z_mesh = np.linspace(0, 26.0, 1000)
        Vx = R_Ax*(z_mesh>=0) + F_tB*(z_mesh>=10) + R_Cx*(z_mesh>=20)
        My = R_Ax*z_mesh*(z_mesh>=0) + F_tB*(z_mesh-10)*(z_mesh>=10) + R_Cx*(z_mesh-20)*(z_mesh>=20)
        
        # Pontos exatos onde os elementos estão instalados
        z_pontos = [0, 10, 20, 26]
        # Valores de momento fletor exatos nesses pontos
        m_pontos = [0, (R_Ax*10), (R_Ax*20 + F_tB*10), 0]
        nomes_pontos = ["A (Mancal)", "B (Pinhão)", "C (Mancal)", "D (Polia)"]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
        
        # --- Gráfico de Esforço Cortante ---
        ax1.plot(z_mesh, Vx, color='blue', drawstyle='steps-post')
        ax1.fill_between(z_mesh, Vx, step='post', alpha=0.15, color='blue')
        ax1.set_ylabel("Cortante V (lb)")
        ax1.grid(True, linestyle='--')
        
        # --- Gráfico de Momento Fletor ---
        ax2.plot(z_mesh, My, color='red')
        ax2.fill_between(z_mesh, My, alpha=0.15, color='red')
        ax2.set_xlabel("Posição z ao longo do eixo (pol)")
        ax2.set_ylabel("Momento M (lb.pol)")
        ax2.grid(True, linestyle='--')
        
        # Adicionando Linhas, Pontos e Textos
        for i, z in enumerate(z_pontos):
            # Linha vertical pontilhada nos dois gráficos
            ax1.axvline(x=z, color='black', linestyle=':', alpha=0.5)
            ax2.axvline(x=z, color='black', linestyle=':', alpha=0.5)
            
            # Bolinha preta no gráfico de Momento e nome do elemento
            ax2.plot(z, m_pontos[i], 'ko') 
            ax1.text(z, ax1.get_ylim()[1], f" {nomes_pontos[i]}", rotation=90, va='top', ha='right', alpha=0.6)
            
            # Escrevendo o valor do momento fletor do lado do ponto (evitando sobrepor o zero)
            if m_pontos[i] != 0:
                ax2.text(z, m_pontos[i], f" {m_pontos[i]:.1f} lb.pol", va='bottom', ha='left', fontsize=10, fontweight='bold')

        st.pyplot(fig)

# =========================================================
# 4. INTERFACE E LÓGICA DO EXERCÍCIO 3
# =========================================================
elif exercicio == "Exercício 3":
    st.title("⚙️ Resolução Automatizada - Exercício 3")
    st.markdown("Análise dinâmica de eixo com 3 elementos: Polia plana (A), Engrenagem (C) e Corrente dentada (D). Apoios em B e E.")
    
    st.sidebar.header("Parâmetros do Sistema")
    n = st.sidebar.number_input("Rotação (RPM)", min_value=1, value=200)
    P_entrada = st.sidebar.number_input("Potência de Entrada Polia A (HP)", value=10.0)
    P_saida_C = st.sidebar.number_input("Potência de Saída Engrenagem C (HP)", value=6.0)
    P_saida_D = st.sidebar.number_input("Potência de Saída Corrente D (HP)", value=4.0)

    if st.button("Executar Análise Completa", type="primary"):
        T_A = (P_entrada * 63025) / n
        T_C = (P_saida_C * 63025) / n
        T_D = (P_saida_D * 63025) / n
        
        # Forças nos Componentes
        F_tA = T_A / 10.0  # Raio de 10 pol
        F_A = 2.0 * F_tA   # Força descendente vertical (-Y)
        
        F_tC = T_C / 5.0   # Raio de 5 pol
        F_rC = F_tC * math.tan(math.radians(20)) # +Y
        
        F_D = T_D / 3.0    # Raio de 3 pol (+Y)
        
        # Equilíbrio Estático em relação a B (z=6)
        R_Ex = -(F_tC * 6) / 20
        R_Bx = -(F_tC + R_Ex)
        
        R_Ey = -((-F_A * -6) + (F_rC * 6) + (F_D * 16)) / 20
        R_By = -(-F_A + F_rC + F_D + R_Ey)
        
        # Seção Crítica (z=12 pol)
        M_yC = R_Ex * 14
        M_xC = R_Ey * 14
        M_max = math.sqrt(M_yC**2 + M_xC**2)
        
        d_min = calcular_diametro_asme(M_max, T_A, 30000, 60000, 2.0)
        
        # Exibição
        st.markdown("---")
        metrics = st.columns(4)
        metrics[0].metric("Torque de Entrada", f"{T_A:.1f} lb.pol")
        metrics[1].metric("Força na Corrente D", f"{F_D:.1f} lb")
        metrics[2].metric("Momento Fletor Máx", f"{M_max:.1f} lb.pol")
        metrics[3].metric("Diâmetro Mínimo", f"{d_min:.3f} pol")
        
        st.subheader("📋 Reações de Apoio nos Rolamentos (B e E)")
        cols = st.columns(2)
        cols[0].success(f"**Mancal B (z = 6 pol):**\n\nRx = {R_Bx:.2f} lb\n\nRy = {R_By:.2f} lb")
        cols[1].success(f"**Mancal E (z = 26 pol):**\n\nRx = {R_Ex:.2f} lb\n\nRy = {R_Ey:.2f} lb")

# =========================================================
# 5. INTERFACE E LÓGICA DO EXERCÍCIO 4
# =========================================================
elif exercicio == "Exercício 4":
    st.title("⚙️ Resolução Automatizada - Exercício 4")
    st.markdown("Análise complexa: Entrada por Corrente C com angulação de 15°. Saídas por Pinhão B e duas Polias em V (D e E, E com 30° de inclinação). Apoios nas extremidades (A e F).")
    
    st.sidebar.header("Dados Globais")
    n = st.sidebar.number_input("Rotação do Eixo (RPM)", value=480)
    
    if st.button("Executar Análise Completa", type="primary"):
        T_C = (11 * 63025) / n # Entrada
        T_B = (5 * 63025) / n  # Saída Pinhão
        T_D = (3 * 63025) / n  # Saída Polia D
        T_E = (3 * 63025) / n  # Saída Polia E
        
        # Decomposição Vetorial Avançada das Forças
        F_tB = T_B / 1.5
        F_rB = F_tB * math.tan(math.radians(20))
        
        F_C = T_C / 5.0
        F_Cx = -F_C * math.sin(math.radians(15))
        F_Cy = -F_C * math.cos(math.radians(15))
        
        F_tD = T_D / 2.0
        F_D = 1.5 * F_tD
        
        F_tE = T_E / 2.0
        F_E = 1.5 * F_tE
        F_Ex = F_E * math.cos(math.radians(30))
        F_Ey = F_E * math.sin(math.radians(30))
        
        # Equilíbrio de Momentos em A (z=0) para achar reações em F (z=24)
        R_Fx = -((F_tB * 4) + (F_Cx * 10) + (F_Ex * 20)) / 24
        R_Ax = -(F_tB + F_Cx + F_Ex + R_Fx)
        
        R_Fy = -((F_rB * 4) + (F_Cy * 10) + (F_D * 16) + (F_Ey * 20)) / 24
        R_Ay = -(F_rB + F_Cy + F_D + F_Ey + R_Fy)
        
        # Seção Crítica D (z = 16 pol)
        M_yD = (R_Fx * 8) + (F_Ex * 4)
        M_xD = (R_Fy * 8) + (F_Ey * 4)
        M_max = math.sqrt(M_yD**2 + M_xD**2)
        
        d_min = calcular_diametro_asme(M_max, T_C, 30000, 60000, 2.0)
        
        # Resultados na Tela
        st.markdown("---")
        metrics = st.columns(4)
        metrics[0].metric("Torque de Entrada (C)", f"{T_C:.1f} lb.pol")
        metrics[1].metric("Força Resultante FE", f"{F_E:.1f} lb")
        metrics[2].metric("Momento Combinado Máx", f"{M_max:.1f} lb.pol")
        metrics[3].metric("Diâmetro Mínimo Requerido", f"{d_min:.3f} pol")
        
        st.subheader("📋 Reações Vetoriais nos Mancais das Extremidades")
        cols = st.columns(2)
        cols[0].warning(f"**Mancal A (z = 0 pol):**\n\nRx = {R_Ax:.2f} lb\n\nRy = {R_Ay:.2f} lb")
        cols[1].warning(f"**Mancal F (z = 24 pol):**\n\nRx = {R_Fx:.2f} lb\n\nRy = {R_Fy:.2f} lb")
