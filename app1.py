import streamlit as st
import math
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

# =========================================================
# 1. FUNÇÕES DE CÁLCULO E GERADOR DE PDF
# =========================================================
def calcular_diametro_asme(M_max, T, Se=30000, Sy=60000, ns=2.0):
    termo_flexao = (M_max / Se) ** 2
    termo_torcao = 0.75 * ((T / Sy) ** 2)
    dentro_raiz = math.sqrt(termo_flexao + termo_torcao)
    d = ((32 * ns / math.pi) * dentro_raiz) ** (1 / 3)
    return d

def gerar_relatorio_pdf(exercicio, material, n, P, T, M_max, d_min, fig=None):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Relatorio de Dimensionamento de Eixo", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, f"Referencia: {exercicio}", ln=True, align='C')
    pdf.ln(10)
    
    # Corpo do Texto
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Material Especificado: {material}", ln=True)
    pdf.cell(0, 8, f"Rotacao Nominal: {n} RPM", ln=True)
    pdf.cell(0, 8, f"Potencia Total Transmitida: {P} HP", ln=True)
    pdf.cell(0, 8, f"Torque Calculado no Eixo: {T:.2f} lb.pol", ln=True)
    pdf.cell(0, 8, f"Momento Fletor Resultante Maximo: {M_max:.2f} lb.pol", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"DIAMETRO MINIMO ADMISSIVEL (ASME): {d_min:.3f} pol", ln=True)
    pdf.ln(5)
    
    # Inserindo o Gráfico (se existir)
    if fig is not None:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Diagramas de Esforcos Internos", ln=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.savefig(tmp.name, format="png", bbox_inches="tight")
            pdf.image(tmp.name, x=10, y=pdf.get_y(), w=190)

    # Evita erros de encoding substituindo caracteres especiais
    return pdf.output(dest="S").encode("latin-1", errors="replace")

# =========================================================
# 2. CONFIGURAÇÃO DA PÁGINA E MENU LATERAL
# =========================================================
st.set_page_config(page_title="Software de Eixos - UESC", layout="wide")

st.sidebar.markdown("# 🎓 UESC - Eng. Mecânica")
st.sidebar.markdown("### Elementos de Máquinas I")
st.sidebar.markdown("**Prof.: Dr. José Carlos de Camargo**")
st.sidebar.markdown("---")

exercicio = st.sidebar.selectbox(
    "Selecione o Exercício da Lista:",
    ["Exercício 1", "Exercício 2", "Exercício 3", "Exercício 4"]
)

# =========================================================
# 3. INTERFACE EXERCÍCIO 1 & 2 (Com Gráficos)
# =========================================================
if exercicio in ["Exercício 1", "Exercício 2"]:
    st.title(f"⚙️ Resolução Automatizada - {exercicio}")
    st.markdown("Dimensionamento do eixo rotativo com engrenagem de dentes retos e polia em V.")
    
    if exercicio == "Exercício 1":
        default_n, default_P, default_Z, default_D_polia = 550, 30.0, 96, 10.0
    else:
        default_n, default_P, default_Z, default_D_polia = 750, 20.0, 100, 9.0

    st.sidebar.header("Parâmetros de Entrada")
    n = st.sidebar.number_input("Rotação (RPM)", min_value=1, value=default_n)
    P = st.sidebar.number_input("Potência Total (HP)", min_value=0.1, value=default_P)
    Z = st.sidebar.number_input("Número de Dentes (Engrenagem)", min_value=1, value=default_Z)
    Pd = st.sidebar.number_input("Passo Diametral (Pd)", min_value=1.0, value=6.0)
    D_polia = st.sidebar.number_input("Diâmetro da Polia (pol)", min_value=1.0, value=default_D_polia)
    
    st.sidebar.header("Material e Segurança")
    material_nome = st.sidebar.text_input("Material", value="Aco SAE 1040 (Estirado a frio)")
    Sy = st.sidebar.number_input("Limite de Escoamento (Sy - psi)", value=60000)
    Se = st.sidebar.number_input("Limite de Fadiga (Se - psi)", value=30000)
    ns = st.sidebar.number_input("Fator de Segurança (ns)", value=2.0)

    if st.button("Executar Análise Completa", type="primary"):
        # Cálculos de Forças
        T = (P * 63025) / n
        R_B = (Z / Pd) / 2.0
        F_tB = T / R_B
        F_rB = F_tB * math.tan(math.radians(20))
        R_D = D_polia / 2.0
        F_tD = T / R_D
        F_D = 1.5 * F_tD
        F_Dx = F_D * math.cos(math.radians(40))
        F_Dy = -F_D * math.sin(math.radians(40))
        
        # Equilíbrio
        R_Cx = -((F_tB * 10) + (F_Dx * 26)) / 20
        R_Ax = -(F_tB + F_Dx + R_Cx)
        R_Cy = -((-F_rB * 10) + (F_Dy * 26)) / 20
        R_Ay = -(-F_rB + F_Dy + R_Cy)
        
        # Momento Máximo
        M_yC = (R_Ax * 20) + (F_tB * 10)
        M_xC = (-R_Ay * 20) - (F_rB * 10)
        M_max = math.sqrt(M_yC**2 + M_xC**2)
        d_min = calcular_diametro_asme(M_max, T, Se, Sy, ns)
        
        # Interface de Resultados
        st.markdown("---")
        metrics = st.columns(4)
        metrics[0].metric("Torque Nominal", f"{T:.1f} lb.pol")
        metrics[1].metric("Força Tangencial FtB", f"{F_tB:.1f} lb")
        metrics[2].metric("Momento Resultante Máx", f"{M_max:.1f} lb.pol")
        metrics[3].metric("Diâmetro Mínimo", f"{d_min:.3f} pol")
        
        # Gráficos de Macaulay com Marcadores
        st.subheader("📊 Diagramas de Esforços Solicitantes (Plano XZ)")
        z_mesh = np.linspace(0, 26.0, 1000)
        Vx = R_Ax*(z_mesh>=0) + F_tB*(z_mesh>=10) + R_Cx*(z_mesh>=20)
        My = R_Ax*z_mesh*(z_mesh>=0) + F_tB*(z_mesh-10)*(z_mesh>=10) + R_Cx*(z_mesh-20)*(z_mesh>=20)
        
        z_pontos = [0, 10, 20, 26]
        m_pontos = [0, (R_Ax*10), (R_Ax*20 + F_tB*10), 0]
        nomes = ["A (Mancal)", "B (Engrenagem)", "C (Mancal)", "D (Polia)"]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
        ax1.plot(z_mesh, Vx, color='blue', drawstyle='steps-post')
        ax1.fill_between(z_mesh, Vx, step='post', alpha=0.15, color='blue')
        ax1.set_ylabel("Cortante V (lb)")
        ax1.grid(True, linestyle='--')
        
        ax2.plot(z_mesh, My, color='red')
        ax2.fill_between(z_mesh, My, alpha=0.15, color='red')
        ax2.set_xlabel("Posição z ao longo do eixo (pol)")
        ax2.set_ylabel("Momento Fletor M (lb.pol)")
        ax2.grid(True, linestyle='--')
        
        # Desenhando linhas e textos
        for i, z in enumerate(z_pontos):
            ax1.axvline(x=z, color='black', linestyle=':', alpha=0.5)
            ax2.axvline(x=z, color='black', linestyle=':', alpha=0.5)
            ax2.plot(z, m_pontos[i], 'ko') 
            ax1.text(z, ax1.get_ylim()[1], f" {nomes[i]}", rotation=90, va='top', ha='right', alpha=0.6)
            if m_pontos[i] != 0:
                ax2.text(z, m_pontos[i], f" {m_pontos[i]:.1f}", va='bottom', ha='left', fontsize=10, fontweight='bold')

        st.pyplot(fig)
        
        # Gerar e baixar PDF
        pdf_bytes = gerar_relatorio_pdf(exercicio, material_nome, n, P, T, M_max, d_min, fig)
        st.markdown("---")
        st.download_button(label="📥 Baixar Relatório Completo em PDF", data=pdf_bytes, file_name=f"Relatorio_{exercicio.replace(' ', '_')}.pdf", mime="application/pdf", type="primary")

# =========================================================
# 4. INTERFACE EXERCÍCIO 3
# =========================================================
elif exercicio == "Exercício 3":
    st.title("⚙️ Resolução Automatizada - Exercício 3")
    st.markdown("Análise dinâmica de eixo com 3 elementos: Polia plana (A), Engrenagem (C) e Corrente dentada (D). Apoios em B e E.")
    
    st.sidebar.header("Parâmetros do Sistema")
    n = st.sidebar.number_input("Rotação (RPM)", min_value=1, value=200)
    P_entrada = st.sidebar.number_input("Potência de Entrada Polia A (HP)", value=10.0)
    P_saida_C = st.sidebar.number_input("Potência de Saída Engrenagem C (HP)", value=6.0)
    P_saida_D = st.sidebar.number_input("Potência de Saída Corrente D (HP)", value=4.0)
    material_nome = st.sidebar.text_input("Material", value="Aco SAE 1117 (Estirado a frio)")

    if st.button("Executar Análise Completa", type="primary"):
        T_A = (P_entrada * 63025) / n
        T_C = (P_saida_C * 63025) / n
        T_D = (P_saida_D * 63025) / n
        
        F_tA = T_A / 10.0  
        F_A = 2.0 * F_tA   
        F_tC = T_C / 5.0   
        F_rC = F_tC * math.tan(math.radians(20)) 
        F_D = T_D / 3.0    
        
        R_Ex = -(F_tC * 6) / 20
        R_Bx = -(F_tC + R_Ex)
        R_Ey = -((-F_A * -6) + (F_rC * 6) + (F_D * 16)) / 20
        R_By = -(-F_A + F_rC + F_D + R_Ey)
        
        M_yC = R_Ex * 14
        M_xC = R_Ey * 14
        M_max = math.sqrt(M_yC**2 + M_xC**2)
        d_min = calcular_diametro_asme(M_max, T_A, 30000, 60000, 2.0)
        
        st.markdown("---")
        metrics = st.columns(4)
        metrics[0].metric("Torque de Entrada", f"{T_A:.1f} lb.pol")
        metrics[1].metric("Força na Corrente D", f"{F_D:.1f} lb")
        metrics[2].metric("Momento Fletor Máx", f"{M_max:.1f} lb.pol")
        metrics[3].metric("Diâmetro Mínimo", f"{d_min:.3f} pol")
        
        st.subheader("📋 Reações de Apoio nos Rolamentos")
        cols = st.columns(2)
        cols[0].success(f"**Mancal B (z = 6 pol):**\n\nRx = {R_Bx:.2f} lb\n\nRy = {R_By:.2f} lb")
        cols[1].success(f"**Mancal E (z = 26 pol):**\n\nRx = {R_Ex:.2f} lb\n\nRy = {R_Ey:.2f} lb")
        
        pdf_bytes = gerar_relatorio_pdf(exercicio, material_nome, n, P_entrada, T_A, M_max, d_min)
        st.markdown("---")
        st.download_button(label="📥 Baixar Relatório em PDF", data=pdf_bytes, file_name="Relatorio_Ex3.pdf", mime="application/pdf", type="primary")

# =========================================================
# 5. INTERFACE EXERCÍCIO 4
# =========================================================
elif exercicio == "Exercício 4":
    st.title("⚙️ Resolução Automatizada - Exercício 4")
    st.markdown("Análise complexa: Entrada por Corrente C. Saídas por Pinhão B e duas Polias em V (D e E).")
    
    st.sidebar.header("Dados Globais")
    n = st.sidebar.number_input("Rotação do Eixo (RPM)", value=480)
    material_nome = st.sidebar.text_input("Material", value="Aco SAE 1137 OQT 1300")
    
    if st.button("Executar Análise Completa", type="primary"):
        T_C = (11 * 63025) / n 
        T_B = (5 * 63025) / n  
        T_D = (3 * 63025) / n  
        T_E = (3 * 63025) / n  
        
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
        
        R_Fx = -((F_tB * 4) + (F_Cx * 10) + (F_Ex * 20)) / 24
        R_Ax = -(F_tB + F_Cx + F_Ex + R_Fx)
        R_Fy = -((F_rB * 4) + (F_Cy * 10) + (F_D * 16) + (F_Ey * 20)) / 24
        R_Ay = -(F_rB + F_Cy + F_D + F_Ey + R_Fy)
        
        M_yD = (R_Fx * 8) + (F_Ex * 4)
        M_xD = (R_Fy * 8) + (F_Ey * 4)
        M_max = math.sqrt(M_yD**2 + M_xD**2)
        d_min = calcular_diametro_asme(M_max, T_C, 30000, 60000, 2.0)
        
        st.markdown("---")
        metrics = st.columns(4)
        metrics[0].metric("Torque de Entrada (C)", f"{T_C:.1f} lb.pol")
        metrics[1].metric("Força Resultante FE", f"{F_E:.1f} lb")
        metrics[2].metric("Momento Combinado Máx", f"{M_max:.1f} lb.pol")
        metrics[3].metric("Diâmetro Mínimo", f"{d_min:.3f} pol")
        
        st.subheader("📋 Reações Vetoriais nos Mancais das Extremidades")
        cols = st.columns(2)
        cols[0].warning(f"**Mancal A (z = 0 pol):**\n\nRx = {R_Ax:.2f} lb\n\nRy = {R_Ay:.2f} lb")
        cols[1].warning(f"**Mancal F (z = 24 pol):**\n\nRx = {R_Fx:.2f} lb\n\nRy = {R_Fy:.2f} lb")
        
        pdf_bytes = gerar_relatorio_pdf(exercicio, material_nome, n, 11, T_C, M_max, d_min)
        st.markdown("---")
        st.download_button(label="📥 Baixar Relatório em PDF", data=pdf_bytes, file_name="Relatorio_Ex4.pdf", mime="application/pdf", type="primary")
