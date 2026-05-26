import streamlit as st
import math
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

# =========================================================
# 1. FUNÇÕES DE CÁLCULO E GERADOR DE PDF E GRÁFICOS
# =========================================================
def calcular_diametro_asme(M_max, T, Se=30000, Sy=60000, ns=2.0):
    termo_flexao = (M_max / Se) ** 2
    termo_torcao = 0.75 * ((T / Sy) ** 2)
    dentro_raiz = math.sqrt(termo_flexao + termo_torcao)
    d = ((32 * ns / math.pi) * dentro_raiz) ** (1 / 3)
    return d

def plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes):
    """Gera um painel com 6 gráficos completos de esforços solicitantes."""
    fig, axs = plt.subplots(3, 2, figsize=(14, 12), sharex=True)
    M_res = np.sqrt(My**2 + Mx**2)

    # 1. Torque (T)
    axs[0, 0].plot(z, T_mesh, color='green', drawstyle='steps-post')
    axs[0, 0].fill_between(z, T_mesh, step='post', alpha=0.2, color='green')
    axs[0, 0].set_title("Diagrama de Torque (T)")
    axs[0, 0].set_ylabel("lb.pol")
    
    # 2. Cortante XZ (Vx)
    axs[1, 0].plot(z, Vx, color='blue', drawstyle='steps-post')
    axs[1, 0].fill_between(z, Vx, step='post', alpha=0.2, color='blue')
    axs[1, 0].set_title("Esforço Cortante Plano XZ (Vx)")
    axs[1, 0].set_ylabel("lb")

    # 3. Fletor XZ (My)
    axs[2, 0].plot(z, My, color='red')
    axs[2, 0].fill_between(z, My, alpha=0.2, color='red')
    axs[2, 0].set_title("Momento Fletor Plano XZ (My)")
    axs[2, 0].set_ylabel("lb.pol")
    axs[2, 0].set_xlabel("Eixo Z (polegadas)")

    # 4. Cortante YZ (Vy)
    axs[0, 1].plot(z, Vy, color='blue', drawstyle='steps-post')
    axs[0, 1].fill_between(z, Vy, step='post', alpha=0.2, color='blue')
    axs[0, 1].set_title("Esforço Cortante Plano YZ (Vy)")

    # 5. Fletor YZ (Mx)
    axs[1, 1].plot(z, Mx, color='red')
    axs[1, 1].fill_between(z, Mx, alpha=0.2, color='red')
    axs[1, 1].set_title("Momento Fletor Plano YZ (Mx)")

    # 6. Momento Resultante (M_res)
    axs[2, 1].plot(z, M_res, color='purple')
    axs[2, 1].fill_between(z, M_res, alpha=0.2, color='purple')
    axs[2, 1].set_title("Momento Fletor Resultante (M_max)")
    axs[2, 1].set_xlabel("Eixo Z (polegadas)")

    # Configurações visuais (grids, marcadores e textos)
    for ax in axs.flat:
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.axhline(0, color='black', linewidth=1)
        for i, zp in enumerate(z_pontos):
            ax.axvline(zp, color='black', linestyle=':', alpha=0.5)
            if ax == axs[0, 0]: # Colocar o nome do elemento só no topo
                ax.text(zp, ax.get_ylim()[1], f" {nomes[i]}", rotation=90, va='top', ha='right', alpha=0.7)

    plt.tight_layout()
    return fig

def gerar_relatorio_pdf(exercicio, material, n, P, T, M_max, d_min, fig=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Relatorio de Dimensionamento de Eixo", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, f"Referencia: {exercicio}", ln=True, align='C')
    pdf.ln(10)
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
    
    if fig is not None:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Diagramas de Esforcos Internos", ln=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.savefig(tmp.name, format="png", bbox_inches="tight")
            pdf.image(tmp.name, x=10, y=pdf.get_y(), w=190)

    return pdf.output(dest="S").encode("latin-1", errors="replace")

# =========================================================
# 2. CONFIGURAÇÃO DA PÁGINA E MENU LATERAL
# =========================================================
st.set_page_config(page_title="Software de Eixos - UESC", layout="wide")
st.sidebar.markdown("# 🎓 UESC - Eng. Mecânica")
st.sidebar.markdown("### Elementos de Máquinas I")
st.sidebar.markdown("**Prof.: Dr. José Carlos de Camargo**")
st.sidebar.markdown("---")

exercicio = st.sidebar.selectbox("Selecione o Exercício:", ["Exercício 1", "Exercício 2", "Exercício 3", "Exercício 4"])

# =========================================================
# 3. INTERFACE EXERCÍCIO 1 & 2
# =========================================================
if exercicio in ["Exercício 1", "Exercício 2"]:
    st.title(f"⚙️ Resolução Automatizada - {exercicio}")
    
    if exercicio == "Exercício 1":
        default_n, default_P, default_Z, default_D_polia = 550, 30.0, 96, 10.0
    else:
        default_n, default_P, default_Z, default_D_polia = 750, 20.0, 100, 9.0

    st.sidebar.header("Parâmetros de Entrada")
    n = st.sidebar.number_input("Rotação (RPM)", min_value=1, value=default_n)
    P = st.sidebar.number_input("Potência Total (HP)", min_value=0.1, value=default_P)
    Z = st.sidebar.number_input("Dentes da Engrenagem", min_value=1, value=default_Z)
    Pd = st.sidebar.number_input("Passo Diametral (Pd)", min_value=1.0, value=6.0)
    D_polia = st.sidebar.number_input("Diâmetro da Polia (pol)", min_value=1.0, value=default_D_polia)
    
    st.sidebar.header("Material e Segurança")
    material_nome = st.sidebar.text_input("Material", value="Aco SAE 1040")
    Sy = st.sidebar.number_input("Sy (psi)", value=60000)
    Se = st.sidebar.number_input("Se (psi)", value=30000)
    ns = st.sidebar.number_input("ns", value=2.0)

    if st.button("Executar Análise Completa", type="primary"):
        T = (P * 63025) / n
        R_B = (Z / Pd) / 2.0
        F_tB = T / R_B
        F_rB = F_tB * math.tan(math.radians(20))
        R_D = D_polia / 2.0
        F_tD = T / R_D
        F_D = 1.5 * F_tD
        F_Dx = F_D * math.cos(math.radians(40))
        F_Dy = -F_D * math.sin(math.radians(40))
        
        R_Cx = -((F_tB * 10) + (F_Dx * 26)) / 20
        R_Ax = -(F_tB + F_Dx + R_Cx)
        R_Cy = -((-F_rB * 10) + (F_Dy * 26)) / 20
        R_Ay = -(-F_rB + F_Dy + R_Cy)
        
        M_yC = (R_Ax * 20) + (F_tB * 10)
        M_xC = (-R_Ay * 20) - (F_rB * 10)
        M_max = math.sqrt(M_yC**2 + M_xC**2)
        d_min = calcular_diametro_asme(M_max, T, Se, Sy, ns)
        
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Torque Nominal", f"{T:.1f} lb.pol")
        m2.metric("Momento Máximo", f"{M_max:.1f} lb.pol")
        m3.metric("Diâmetro Crítico", f"{d_min:.3f} pol")
        
        st.subheader("📊 Diagramas de Esforços Solicitantes Completos")
        z = np.linspace(0, 26.0, 1000)
        Vx = R_Ax*(z>=0) + F_tB*(z>=10) + R_Cx*(z>=20) + F_Dx*(z>=26)
        Vy = R_Ay*(z>=0) - F_rB*(z>=10) + R_Cy*(z>=20) + F_Dy*(z>=26)
        My = R_Ax*z*(z>=0) + F_tB*(z-10)*(z>=10) + R_Cx*(z-20)*(z>=20) + F_Dx*(z-26)*(z>=26)
        Mx = R_Ay*z*(z>=0) - F_rB*(z-10)*(z>=10) + R_Cy*(z-20)*(z>=20) + F_Dy*(z-26)*(z>=26)
        T_mesh = T * ((z >= 10) & (z <= 26))
        
        fig = plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, [0, 10, 20, 26], ["Mancal A", "Engrenagem B", "Mancal C", "Polia D"])
        st.pyplot(fig)
        
        st.download_button("📥 Baixar Relatório em PDF", gerar_relatorio_pdf(exercicio, material_nome, n, P, T, M_max, d_min, fig), f"Relatorio_{exercicio[:4]}.pdf", "application/pdf")

# =========================================================
# 4. INTERFACE EXERCÍCIO 3
# =========================================================
elif exercicio == "Exercício 3":
    st.title("⚙️ Resolução Automatizada - Exercício 3")
    st.sidebar.header("Parâmetros do Sistema")
    n = st.sidebar.number_input("Rotação (RPM)", min_value=1, value=200)
    P_entrada = st.sidebar.number_input("Potência Polia A (HP)", value=10.0)
    P_saida_C = st.sidebar.number_input("Potência Engrenagem C (HP)", value=6.0)
    P_saida_D = st.sidebar.number_input("Potência Corrente D (HP)", value=4.0)
    material_nome = st.sidebar.text_input("Material", value="Aco SAE 1117")

    if st.button("Executar Análise Completa", type="primary"):
        T_A, T_C, T_D = (P_entrada*63025)/n, (P_saida_C*63025)/n, (P_saida_D*63025)/n
        F_tA, F_A = T_A / 10.0, 2.0 * (T_A / 10.0)
        F_tC, F_rC = T_C / 5.0, (T_C / 5.0) * math.tan(math.radians(20))
        F_D = T_D / 3.0
        
        R_Ex = -(F_tC * 6) / 20
        R_Bx = -(F_tC + R_Ex)
        R_Ey = -((-F_A * -6) + (F_rC * 6) + (F_D * 16)) / 20
        R_By = -(-F_A + F_rC + F_D + R_Ey)
        
        M_yC, M_xC = R_Ex * 14, R_Ey * 14
        M_max = math.sqrt(M_yC**2 + M_xC**2)
        d_min = calcular_diametro_asme(M_max, T_A)
        
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Torque Máx (A)", f"{T_A:.1f} lb.pol")
        m2.metric("Momento Máximo", f"{M_max:.1f} lb.pol")
        m3.metric("Diâmetro Crítico", f"{d_min:.3f} pol")
        
        st.subheader("📊 Diagramas de Esforços Solicitantes Completos")
        z = np.linspace(0, 26.0, 1000)
        Vx = R_Bx*(z>=6) + F_tC*(z>=12) + R_Ex*(z>=26)
        Vy = -F_A*(z>=0) + R_By*(z>=6) + F_rC*(z>=12) + F_D*(z>=22) + R_Ey*(z>=26)
        My = R_Bx*(z-6)*(z>=6) + F_tC*(z-12)*(z>=12) + R_Ex*(z-26)*(z>=26)
        Mx = -F_A*z*(z>=0) + R_By*(z-6)*(z>=6) + F_rC*(z-12)*(z>=12) + F_D*(z-22)*(z>=22) + R_Ey*(z-26)*(z>=26)
        T_mesh = T_A*((z>=0)&(z<12)) + T_D*((z>=12)&(z<=22))
        
        fig = plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, [0, 6, 12, 22, 26], ["Polia A", "Mancal B", "Engrenagem C", "Corrente D", "Mancal E"])
        st.pyplot(fig)
        st.download_button("📥 Baixar Relatório", gerar_relatorio_pdf(exercicio, material_nome, n, P_entrada, T_A, M_max, d_min, fig), "Relatorio_Ex3.pdf")

# =========================================================
# 5. INTERFACE EXERCÍCIO 4
# =========================================================
elif exercicio == "Exercício 4":
    st.title("⚙️ Resolução Automatizada - Exercício 4")
    st.sidebar.header("Dados Globais")
    n = st.sidebar.number_input("Rotação do Eixo (RPM)", value=480)
    material_nome = st.sidebar.text_input("Material", value="Aco SAE 1137")
    
    if st.button("Executar Análise Completa", type="primary"):
        T_C, T_B, T_D, T_E = (11*63025)/n, (5*63025)/n, (3*63025)/n, (3*63025)/n
        F_tB, F_rB = T_B/1.5, (T_B/1.5)*math.tan(math.radians(20))
        F_C = T_C / 5.0
        F_Cx, F_Cy = -F_C * math.sin(math.radians(15)), -F_C * math.cos(math.radians(15))
        F_D = 1.5 * (T_D / 2.0)
        F_E = 1.5 * (T_E / 2.0)
        F_Ex, F_Ey = F_E * math.cos(math.radians(30)), F_E * math.sin(math.radians(30))
        
        R_Fx = -((F_tB * 4) + (F_Cx * 10) + (F_Ex * 20)) / 24
        R_Ax = -(F_tB + F_Cx + F_Ex + R_Fx)
        R_Fy = -((F_rB * 4) + (F_Cy * 10) + (F_D * 16) + (F_Ey * 20)) / 24
        R_Ay = -(F_rB + F_Cy + F_D + F_Ey + R_Fy)
        
        M_yD, M_xD = (R_Fx * 8) + (F_Ex * 4), (R_Fy * 8) + (F_Ey * 4)
        M_max = math.sqrt(M_yD**2 + M_xD**2)
        d_min = calcular_diametro_asme(M_max, T_C)
        
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Torque Máx (C)", f"{T_C:.1f} lb.pol")
        m2.metric("Momento Máximo", f"{M_max:.1f} lb.pol")
        m3.metric("Diâmetro Crítico", f"{d_min:.3f} pol")
        
        st.subheader("📊 Diagramas de Esforços Solicitantes Completos")
        z = np.linspace(0, 24.0, 1000)
        Vx = R_Ax*(z>=0) + F_tB*(z>=4) + F_Cx*(z>=10) + F_Ex*(z>=20) + R_Fx*(z>=24)
        Vy = R_Ay*(z>=0) + F_rB*(z>=4) + F_Cy*(z>=10) + F_D*(z>=16) + F_Ey*(z>=20) + R_Fy*(z>=24)
        My = R_Ax*z*(z>=0) + F_tB*(z-4)*(z>=4) + F_Cx*(z-10)*(z>=10) + F_Ex*(z-20)*(z>=20) + R_Fx*(z-24)*(z>=24)
        Mx = R_Ay*z*(z>=0) + F_rB*(z-4)*(z>=4) + F_Cy*(z-10)*(z>=10) + F_D*(z-16)*(z>=16) + F_Ey*(z-20)*(z>=20) + R_Fy*(z-24)*(z>=24)
        T_mesh = T_B*((z>=4)&(z<10)) + (T_D+T_E)*((z>=10)&(z<16)) + T_E*((z>=16)&(z<=20))
        
        fig = plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, [0, 4, 10, 16, 20, 24], ["Mancal A", "Pinhão B", "Corrente C", "Polia D", "Polia E", "Mancal F"])
        st.pyplot(fig)
        st.download_button("📥 Baixar Relatório", gerar_relatorio_pdf(exercicio, material_nome, n, 11, T_C, M_max, d_min, fig), "Relatorio_Ex4.pdf")
