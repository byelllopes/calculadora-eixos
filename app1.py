import streamlit as st
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

# =========================================================
# 1. FUNÇÕES MATEMÁTICAS E FÍSICAS BASE
# =========================================================
def calcular_diametro_local(M, T, V, Kt, Se, Sy, ns):
    if M < 1.0 and T < 1.0 and V > 1.0: 
        return math.sqrt((2.94 * Kt * V * ns) / Se)
    termo_flexao = (Kt * M / Se) ** 2
    termo_torcao = 0.75 * ((T / Sy) ** 2)
    return ((32 * ns / math.pi) * math.sqrt(termo_flexao + termo_torcao)) ** (1 / 3)

def gerar_tabela_pontos(z_mesh, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list, Se, Sy, ns):
    dados = []
    for i, z_val in enumerate(z_pontos):
        idx = (np.abs(z_mesh - z_val)).argmin()
        idx_min, idx_max = max(0, idx - 5), min(len(z_mesh)-1, idx + 5)
        
        M_local = max(math.hypot(My[j], Mx[j]) for j in range(idx_min, idx_max+1))
        T_local = max(abs(T_mesh[j]) for j in range(idx_min, idx_max+1))
        V_local = max(math.hypot(Vx[j], Vy[j]) for j in range(idx_min, idx_max+1))
        
        Kt = kt_list[i]
        dados.append({
            "Ponto": nomes[i], "Z (pol)": z_val, "Kt": Kt,
            "Momento M": M_local, "Torque T": T_local, 
            "Cortante V": V_local, "D_min": calcular_diametro_local(M_local, T_local, V_local, Kt, Se, Sy, ns)
        })
    return pd.DataFrame(dados)

def plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes):
    fig, axs = plt.subplots(3, 2, figsize=(14, 12), sharex=True)
    M_res = np.sqrt(My**2 + Mx**2)

    axs[0, 0].plot(z, T_mesh, color='green', drawstyle='steps-post')
    axs[0, 0].fill_between(z, T_mesh, step='post', alpha=0.2, color='green')
    axs[0, 0].set_title("Diagrama de Torque (T)")
    
    axs[1, 0].plot(z, Vx, color='blue', drawstyle='steps-post')
    axs[1, 0].fill_between(z, Vx, step='post', alpha=0.2, color='blue')
    axs[1, 0].set_title("Esforço Cortante (Vx)")

    axs[2, 0].plot(z, My, color='red')
    axs[2, 0].fill_between(z, My, alpha=0.2, color='red')
    axs[2, 0].set_title("Momento Fletor (My)")

    axs[0, 1].plot(z, Vy, color='blue', drawstyle='steps-post')
    axs[0, 1].fill_between(z, Vy, step='post', alpha=0.2, color='blue')
    axs[0, 1].set_title("Esforço Cortante (Vy)")

    axs[1, 1].plot(z, Mx, color='red')
    axs[1, 1].fill_between(z, Mx, alpha=0.2, color='red')
    axs[1, 1].set_title("Momento Fletor (Mx)")

    axs[2, 1].plot(z, M_res, color='purple')
    axs[2, 1].fill_between(z, M_res, alpha=0.2, color='purple')
    axs[2, 1].set_title("Momento Fletor Resultante (M_max)")

    for ax in axs.flat:
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.axhline(0, color='black', linewidth=1)
        for i, zp in enumerate(z_pontos):
            ax.axvline(zp, color='black', linestyle=':', alpha=0.5)

    plt.tight_layout()
    return fig

# =========================================================
# 2. MOTORES DE RESOLUÇÃO DOS EXERCÍCIOS
# =========================================================
def resolver_ex1_2(n, P, Z, Pd, D_polia, Se, Sy, ns):
    T = (P * 63025) / n
    F_tB, F_rB = T / ((Z / Pd) / 2.0), (T / ((Z / Pd) / 2.0)) * math.tan(math.radians(20))
    F_D = 1.5 * (T / (D_polia / 2.0))
    F_Dx, F_Dy = F_D * math.cos(math.radians(40)), -F_D * math.sin(math.radians(40))
    
    R_Cx, R_Cy = -((F_tB * 10) + (F_Dx * 26)) / 20, -((-F_rB * 10) + (F_Dy * 26)) / 20
    R_Ax, R_Ay = -(F_tB + F_Dx + R_Cx), -(-F_rB + F_Dy + R_Cy)
    
    z = np.linspace(0, 26.0, 1000)
    Vx = R_Ax*(z>=0) + F_tB*(z>=10) + R_Cx*(z>=20) + F_Dx*(z>=26)
    Vy = R_Ay*(z>=0) - F_rB*(z>=10) + R_Cy*(z>=20) + F_Dy*(z>=26)
    My = R_Ax*z*(z>=0) + F_tB*(z-10)*(z>=10) + R_Cx*(z-20)*(z>=20) + F_Dx*(z-26)*(z>=26)
    Mx = R_Ay*z*(z>=0) - F_rB*(z-10)*(z>=10) + R_Cy*(z-20)*(z>=20) + F_Dy*(z-26)*(z>=26)
    T_mesh = T * ((z >= 10) & (z <= 26))
    
    z_pontos, nomes, kt_list = [0, 10, 20, 26], ["Mancal A", "Engrenagem B", "Mancal C", "Polia D"], [2.5, 2.0, 2.5, 2.0]
    return T, z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list

# =========================================================
# 3. GERADOR DO SUPER PDF (TEORIA + CÓDIGO + CÁLCULOS)
# =========================================================
def gerar_relatorio_integrado(exercicio, material, df_tabela, fig):
    pdf = FPDF()
    pdf.add_page()
    
    # CABEÇALHO
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"RELATORIO INTEGRADO DE ENGENHARIA", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, f"Referencia: {exercicio} | Material: {material}", ln=True, align='C')
    pdf.ln(5)
    
    # 1. FUNDAMENTAÇÃO TEÓRICA
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. Fundamentacao Teorica", ln=True)
    pdf.set_font("Arial", '', 10)
    teoria_eixos = (
        "O dimensionamento a fadiga do eixo foi realizado utilizando a equacao ASME, "
        "que e uma adaptacao conservadora baseada na teoria da energia de distorcao (Von Mises). "
        "Conforme a literatura da disciplina, os fatores de concentracao de tensao (Kt) sao "
        "cruciais em mudancas de secao transversal, sendo aplicados valores especificos para "
        "ressaltos de rolamentos e rasgos de chaveta."
    )
    pdf.multi_cell(0, 6, teoria_eixos)
    pdf.ln(2)
    
    teoria_engrenagens = (
        "Para os elementos transmissores, as forcas geradas pelo engrenamento incluem uma "
        "componente tangencial (responsavel pela transmissao do torque puro) e uma componente "
        "radial (que afasta os eixos e gera momento fletor). A relacao vetorial entre elas "
        "foi calculada utilizando o angulo de pressao padrao de 20 graus."
    )
    pdf.multi_cell(0, 6, teoria_engrenagens)
    pdf.ln(5)

    # 2. METODOLOGIA COMPUTACIONAL
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. Explicacao do Codigo Fonte", ln=True)
    pdf.set_font("Arial", '', 10)
    metodologia = (
        "O script Python estrutura a solucao em duas etapas. Primeiro, o equilibrio estatico "
        "(somatorio de forcas e momentos) e resolvido algebricamente para encontrar as reacoes "
        "nos mancais. Em seguida, a biblioteca Numpy aplica Funcoes de Macaulay para varrer o eixo "
        "discretizado e plotar os diagramas de esforcos internos em todos os planos."
    )
    pdf.multi_cell(0, 6, metodologia)
    pdf.ln(5)

    # 3. RESULTADOS E TABELA
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "3. Analise de Diametros Escalonados (Ponto a Ponto)", ln=True)
    pdf.set_font("Arial", 'B', 9)
    cols = [30, 15, 15, 30, 30, 30, 30]
    headers = ["Elemento", "Z", "Kt", "Momento M", "Torque T", "Cortante V", "D_min (pol)"]
    for i in range(len(cols)):
        pdf.cell(cols[i], 10, headers[i], border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 9)
    for i in range(len(df_tabela)):
        pdf.cell(cols[0], 10, str(df_tabela.iloc[i, 0]), border=1, align='C')
        pdf.cell(cols[1], 10, str(df_tabela.iloc[i, 1]), border=1, align='C')
        pdf.cell(cols[2], 10, str(df_tabela.iloc[i, 2]), border=1, align='C')
        pdf.cell(cols[3], 10, f"{df_tabela.iloc[i, 3]:.1f}", border=1, align='C')
        pdf.cell(cols[4], 10, f"{df_tabela.iloc[i, 4]:.1f}", border=1, align='C')
        pdf.cell(cols[5], 10, f"{df_tabela.iloc[i, 5]:.1f}", border=1, align='C')
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(cols[6], 10, f"{df_tabela.iloc[i, 6]:.3f}", border=1, align='C')
        pdf.set_font("Arial", '', 9)
        pdf.ln()
    
    # 4. GRÁFICOS
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "4. Diagramas de Esforcos Solicitantes", ln=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, format="png", bbox_inches="tight")
        pdf.image(tmp.name, x=10, y=pdf.get_y(), w=190)

    return pdf.output(dest="S").encode("latin-1", errors="replace")

# =========================================================
# 4. ESTRUTURA DO SITE E MENU
# =========================================================
st.set_page_config(page_title="Software de Eixos", layout="wide")
st.sidebar.markdown("# 🎓 UESC - Eng. Mecânica")
st.sidebar.markdown("### Elementos de Máquinas I")
st.sidebar.markdown("---")

menu = st.sidebar.selectbox("Navegação:", ["Exercício 1", "Exercício 2", "Gerador de Relatório Final"])

# =========================================================
# INTERFACE PADRÃO (Apenas Visualização)
# =========================================================
if menu in ["Exercício 1", "Exercício 2"]:
    st.title(f"⚙️ Análise Visual - {menu}")
    n = st.sidebar.number_input("Rotação (RPM)", value=550 if menu == "Exercício 1" else 750)
    P = st.sidebar.number_input("Potência (HP)", value=30.0 if menu == "Exercício 1" else 20.0)
    
    if st.button("Analisar Esforços"):
        T, z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list = resolver_ex1_2(n, P, 96, 6.0, 10.0, 30000, 60000, 2.0)
        df_tabela = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list, 30000, 60000, 2.0)
        
        st.dataframe(df_tabela.style.format({"Momento M": "{:.1f}", "Torque T": "{:.1f}", "Cortante V": "{:.1f}", "D_min": "{:.3f}"}), use_container_width=True)
        st.pyplot(plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes))

# =========================================================
# INTERFACE UNIFICADA DE RELATÓRIO
# =========================================================
elif menu == "Gerador de Relatório Final":
    st.title("📄 Central de Geração de Relatórios Integrados")
    st.markdown("Esta interface compila a fundamentação teórica, a metodologia do código e as memórias de cálculo em um documento profissional unificado.")
    
    ex_escolhido = st.selectbox("Selecione qual exercício deseja anexar à memória de cálculo do relatório:", ["Exercício 1", "Exercício 2"])
    material = st.text_input("Especifique o material para o laudo:", "Aço SAE 1040 Estirado a Frio")
    
    if st.button("Gerar Relatório Completo (PDF)", type="primary"):
        # Roda a matemática em background
        n, P = (550, 30.0) if ex_escolhido == "Exercício 1" else (750, 20.0)
        T, z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list = resolver_ex1_2(n, P, 96, 6.0, 10.0, 30000, 60000, 2.0)
        
        # Gera Tabela e Gráfico silenciosamente
        df_tabela = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list, 30000, 60000, 2.0)
        fig = plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes)
        
        # Constrói o Super PDF
        pdf_bytes = gerar_relatorio_integrado(ex_escolhido, material, df_tabela, fig)
        
        st.success("Documento gerado com sucesso! Contém citações teóricas, explicações do algoritmo e diagramas.")
        st.download_button(
            label="📥 Baixar Laudo de Engenharia (PDF)",
            data=pdf_bytes,
            file_name=f"Laudo_UESC_{ex_escolhido.replace(' ', '')}.pdf",
            mime="application/pdf"
        )
