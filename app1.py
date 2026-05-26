import streamlit as st
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

# =========================================================
# 1. MATEMÁTICA E DIMENSIONAMENTO DE FADIGA
# =========================================================
def calcular_diametro_local(M, T, V, Kt, Se, Sy, ns):
    """Calcula o diâmetro pela teoria de falha de Fadiga ASME (Von Mises)."""
    if M < 1.0 and T < 1.0 and V > 1.0: 
        return math.sqrt((2.94 * Kt * V * ns) / Se)
    termo_flexao = (Kt * M / Se) ** 2
    termo_torcao = 0.75 * ((T / Sy) ** 2)
    return ((32 * ns / math.pi) * math.sqrt(termo_flexao + termo_torcao)) ** (1 / 3)

def gerar_tabela_pontos(z_mesh, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list, Se, Sy, ns):
    """Escaneia os gráficos e gera os diâmetros escalonados (D1, D2, D3...)."""
    dados = []
    for i, z_val in enumerate(z_pontos):
        idx = (np.abs(z_mesh - z_val)).argmin()
        idx_min, idx_max = max(0, idx - 5), min(len(z_mesh)-1, idx + 5)
        
        M_local = max(math.hypot(My[j], Mx[j]) for j in range(idx_min, idx_max+1))
        T_local = max(abs(T_mesh[j]) for j in range(idx_min, idx_max+1))
        V_local = max(math.hypot(Vx[j], Vy[j]) for j in range(idx_min, idx_max+1))
        
        Kt = kt_list[i]
        D_min = calcular_diametro_local(M_local, T_local, V_local, Kt, Se, Sy, ns)
        
        dados.append({
            "Ponto": nomes[i], "Z (pol)": z_val, "Kt": Kt,
            "Momento M": M_local, "Torque T": T_local, 
            "Cortante V": V_local, "D_min": D_min
        })
    return pd.DataFrame(dados)

def plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes):
    """Gera o painel 3x2 com todos os diagramas solicitantes."""
    fig, axs = plt.subplots(3, 2, figsize=(14, 12), sharex=True)
    M_res = np.sqrt(My**2 + Mx**2)

    axs[0, 0].plot(z, T_mesh, color='green', drawstyle='steps-post')
    axs[0, 0].fill_between(z, T_mesh, step='post', alpha=0.2, color='green')
    axs[0, 0].set_title("Diagrama de Torque (T) [lb.pol]")
    
    axs[1, 0].plot(z, Vx, color='blue', drawstyle='steps-post')
    axs[1, 0].fill_between(z, Vx, step='post', alpha=0.2, color='blue')
    axs[1, 0].set_title("Esforço Cortante XZ (Vx) [lb]")

    axs[2, 0].plot(z, My, color='red')
    axs[2, 0].fill_between(z, My, alpha=0.2, color='red')
    axs[2, 0].set_title("Momento Fletor XZ (My) [lb.pol]")

    axs[0, 1].plot(z, Vy, color='blue', drawstyle='steps-post')
    axs[0, 1].fill_between(z, Vy, step='post', alpha=0.2, color='blue')
    axs[0, 1].set_title("Esforço Cortante YZ (Vy) [lb]")

    axs[1, 1].plot(z, Mx, color='red')
    axs[1, 1].fill_between(z, Mx, alpha=0.2, color='red')
    axs[1, 1].set_title("Momento Fletor YZ (Mx) [lb.pol]")

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
# 2. MOTORES DE RESOLUÇÃO (Background)
# =========================================================
def motor_ex1_2(n, P, Z_dentes, Pd, D_polia):
    T = (P * 63025) / n
    F_tB, F_rB = T / ((Z_dentes / Pd) / 2.0), (T / ((Z_dentes / Pd) / 2.0)) * math.tan(math.radians(20))
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
    return z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list

def motor_ex3(n, P_entrada, P_saida_C, P_saida_D):
    T_A, T_C, T_D = (P_entrada*63025)/n, (P_saida_C*63025)/n, (P_saida_D*63025)/n
    F_tA, F_A = T_A / 10.0, 2.0 * (T_A / 10.0)
    F_tC, F_rC = T_C / 5.0, (T_C / 5.0) * math.tan(math.radians(20))
    F_D = T_D / 3.0
    
    R_Ex = -(F_tC * 6) / 20
    R_Bx = -(F_tC + R_Ex)
    R_Ey = -((-F_A * -6) + (F_rC * 6) + (F_D * 16)) / 20
    R_By = -(-F_A + F_rC + F_D + R_Ey)
    
    z = np.linspace(0, 26.0, 1000)
    Vx = R_Bx*(z>=6) + F_tC*(z>=12) + R_Ex*(z>=26)
    Vy = -F_A*(z>=0) + R_By*(z>=6) + F_rC*(z>=12) + F_D*(z>=22) + R_Ey*(z>=26)
    My = R_Bx*(z-6)*(z>=6) + F_tC*(z-12)*(z>=12) + R_Ex*(z-26)*(z>=26)
    Mx = -F_A*z*(z>=0) + R_By*(z-6)*(z>=6) + F_rC*(z-12)*(z>=12) + F_D*(z-22)*(z>=22) + R_Ey*(z-26)*(z>=26)
    T_mesh = T_A*((z>=0)&(z<12)) + T_D*((z>=12)&(z<=22))
    
    z_pontos, nomes, kt_list = [0, 6, 12, 22, 26], ["Polia A", "Mancal B", "Engrenagem C", "Corrente D", "Mancal E"], [2.0, 2.5, 2.0, 2.0, 2.5]
    return z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list

def motor_ex4(n):
    T_C, T_B, T_D, T_E = (11*63025)/n, (5*63025)/n, (3*63025)/n, (3*63025)/n
    F_tB, F_rB = T_B/1.5, (T_B/1.5)*math.tan(math.radians(20))
    F_C = T_C / 5.0
    F_Cx, F_Cy = -F_C * math.sin(math.radians(15)), -F_C * math.cos(math.radians(15))
    F_D, F_E = 1.5 * (T_D / 2.0), 1.5 * (T_E / 2.0)
    F_Ex, F_Ey = F_E * math.cos(math.radians(30)), F_E * math.sin(math.radians(30))
    
    R_Fx = -((F_tB * 4) + (F_Cx * 10) + (F_Ex * 20)) / 24
    R_Ax = -(F_tB + F_Cx + F_Ex + R_Fx)
    R_Fy = -((F_rB * 4) + (F_Cy * 10) + (F_D * 16) + (F_Ey * 20)) / 24
    R_Ay = -(F_rB + F_Cy + F_D + F_Ey + R_Fy)
    
    z = np.linspace(0, 24.0, 1000)
    Vx = R_Ax*(z>=0) + F_tB*(z>=4) + F_Cx*(z>=10) + F_Ex*(z>=20) + R_Fx*(z>=24)
    Vy = R_Ay*(z>=0) + F_rB*(z>=4) + F_Cy*(z>=10) + F_D*(z>=16) + F_Ey*(z>=20) + R_Fy*(z>=24)
    My = R_Ax*z*(z>=0) + F_tB*(z-4)*(z>=4) + F_Cx*(z-10)*(z>=10) + F_Ex*(z-20)*(z>=20) + R_Fx*(z-24)*(z>=24)
    Mx = R_Ay*z*(z>=0) + F_rB*(z-4)*(z>=4) + F_Cy*(z-10)*(z>=10) + F_D*(z-16)*(z>=16) + F_Ey*(z-20)*(z>=20) + R_Fy*(z-24)*(z>=24)
    T_mesh = T_B*((z>=4)&(z<10)) + (T_D+T_E)*((z>=10)&(z<16)) + T_E*((z>=16)&(z<=20))
    
    z_pontos, nomes, kt_list = [0, 4, 10, 16, 20, 24], ["Mancal A", "Pinhão B", "Corrente C", "Polia D", "Polia E", "Mancal F"], [2.5, 2.0, 2.0, 2.0, 2.0, 2.5]
    return z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list

# =========================================================
# 3. GERADOR DO SUPER PDF (TEORIA + CÓDIGO + CÁLCULOS)
# =========================================================
def gerar_relatorio_integrado(exercicio, material, df_tabela, fig):
    pdf = FPDF()
    pdf.add_page()
    
    # --- CABEÇALHO ---
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"LAUDO DE PROJETO DE EIXOS - UESC", ln=True, align='C')
    pdf.set_font("Arial", 'I', 11)
    pdf.cell(0, 6, f"Disciplina: CET 948 - Elementos de Maquinas I | Prof. Dr. Jose Carlos de Camargo", ln=True, align='C')
    pdf.cell(0, 6, f"Referencia: Lista 02 - {exercicio} | Material Base: {material}", ln=True, align='C')
    pdf.ln(5)
    
    # --- 1. FUNDAMENTAÇÃO TEÓRICA ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "1. Fundamentacao Teorica Aplicada", ln=True)
    pdf.set_font("Arial", '', 10)
    teoria = (
        f"A resolucao do {exercicio} baseia-se nos conceitos abordados nos slides da disciplina. "
        "O dimensionamento do eixo a fadiga foi realizado utilizando a equacao ASME (baseada na "
        "teoria da Energia de Distorcao / Von Mises) para compor os estados de flexo-torcao.\n\n"
        "A cinematica das engrenagens e polias foi decomposta vetorialmente. Para as engrenagens de "
        "dentes retos, utilizou-se o angulo de pressao padrao de 20 graus (que afasta os eixos e gera a forca radial). "
        "Conforme exigido pelo professor, a analise considera diametros escalonados atraves dos Fatores "
        "de Concentracao de Tensao (Kt), aplicando Kt = 2.5 para ressaltos de rolamentos e Kt = 2.0 para "
        "rasgos de chaveta nas engrenagens/polias."
    )
    pdf.multi_cell(0, 5, teoria)
    pdf.ln(5)

    # --- 2. METODOLOGIA DO CÓDIGO ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "2. Metodologia Computacional", ln=True)
    pdf.set_font("Arial", '', 10)
    metodologia = (
        "O script resolve inicialmente o equilibrio estatico para determinar as reacoes nos mancais. "
        "Em seguida, utilizando a biblioteca Numpy, o eixo e discretizado em 1000 pontos. Funcoes "
        "de Macaulay sao aplicadas para gerar as funcoes continuas de Esforco Cortante (V), "
        "Momento Fletor (M) e Torque (T) nos planos vertical e horizontal. O algoritmo varre esses arrays "
        "para identificar a combinacao critica exata em cada estacao do eixo."
    )
    pdf.multi_cell(0, 5, metodologia)
    pdf.ln(5)

    # --- 3. RESULTADOS E TABELA ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "3. Analise de Diametros Escalonados (Ponto a Ponto)", ln=True)
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
    
    # --- 4. GRÁFICOS ---
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "4. Diagramas de Esforcos Solicitantes", ln=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, format="png", bbox_inches="tight")
        pdf.image(tmp.name, x=10, y=pdf.get_y(), w=190)

    return pdf.output(dest="S").encode("latin-1", errors="replace")

# =========================================================
# 4. ESTRUTURA DO SITE E MENU LATERAL
# =========================================================
st.set_page_config(page_title="Software de Eixos", layout="wide")
st.sidebar.markdown("# 🎓 UESC - Eng. Mecânica")
st.sidebar.markdown("### Elementos de Máquinas I")
st.sidebar.markdown("---")

menu = st.sidebar.selectbox("Navegação:", [
    "Visualizar Exercício 1", 
    "Visualizar Exercício 2", 
    "Visualizar Exercício 3", 
    "Visualizar Exercício 4", 
    "📄 Gerar Relatório Completo"
])

# =========================================================
# INTERFACES DE VISUALIZAÇÃO (Sem botões de download)
# =========================================================
if menu in ["Visualizar Exercício 1", "Visualizar Exercício 2"]:
    st.title(f"⚙️ Análise Dinâmica - {menu.split()[-2]} {menu.split()[-1]}")
    n = st.sidebar.number_input("Rotação (RPM)", value=550 if "1" in menu else 750)
    P = st.sidebar.number_input("Potência (HP)", value=30.0 if "1" in menu else 20.0)
    
    if st.button("Calcular Esforços"):
        z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list = motor_ex1_2(n, P, 96, 6.0, 10.0)
        df_tab = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, 30000, 60000, 2.0)
        st.dataframe(df_tab.style.format({"Momento M": "{:.1f}", "Torque T": "{:.1f}", "Cortante V": "{:.1f}", "D_min": "{:.3f}"}), use_container_width=True)
        st.pyplot(plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes))

elif menu == "Visualizar Exercício 3":
    st.title("⚙️ Análise Dinâmica - Exercício 3")
    n = st.sidebar.number_input("Rotação (RPM)", value=200)
    
    if st.button("Calcular Esforços"):
        z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list = motor_ex3(n, 10.0, 6.0, 4.0)
        df_tab = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, 30000, 60000, 2.0)
        st.dataframe(df_tab.style.format({"Momento M": "{:.1f}", "Torque T": "{:.1f}", "Cortante V": "{:.1f}", "D_min": "{:.3f}"}), use_container_width=True)
        st.pyplot(plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes))

elif menu == "Visualizar Exercício 4":
    st.title("⚙️ Análise Dinâmica - Exercício 4")
    n = st.sidebar.number_input("Rotação (RPM)", value=480)
    
    if st.button("Calcular Esforços"):
        z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list = motor_ex4(n)
        df_tab = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, 30000, 60000, 2.0)
        st.dataframe(df_tab.style.format({"Momento M": "{:.1f}", "Torque T": "{:.1f}", "Cortante V": "{:.1f}", "D_min": "{:.3f}"}), use_container_width=True)
        st.pyplot(plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes))

# =========================================================
# INTERFACE UNIFICADA DO LAUDO/RELATÓRIO
# =========================================================
elif menu == "📄 Gerar Relatório Completo":
    st.title("📄 Central de Relatórios e Laudos")
    st.markdown("Interface dedicada à compilação da fundamentação teórica (baseada na disciplina CET 948), explicação metodológica do código e memórias de cálculo.")
    
    ex_escolhido = st.selectbox("Selecione qual exercício deseja processar e anexar ao Laudo:", 
                                ["Exercício 1", "Exercício 2", "Exercício 3", "Exercício 4"])
    
    material = st.text_input("Especifique o material (para o cabeçalho do laudo):", "Aço SAE 1040")
    Sy = st.number_input("Limite de Escoamento - Sy (psi)", value=60000)
    Se = st.number_input("Limite de Fadiga - Se (psi)", value=30000)
    ns = st.number_input("Fator de Segurança (ns)", value=2.0)
    
    if st.button("Compilar Documento (PDF)", type="primary"):
        # Direciona para o motor de cálculo correto silenciosamente
        if ex_escolhido == "Exercício 1":
            z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list = motor_ex1_2(550, 30.0, 96, 6.0, 10.0)
        elif ex_escolhido == "Exercício 2":
            z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list = motor_ex1_2(750, 20.0, 100, 6.0, 9.0)
        elif ex_escolhido == "Exercício 3":
            z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list = motor_ex3(200, 10.0, 6.0, 4.0)
        else:
            z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list = motor_ex4(480)
            
        # Gera os dados visuais
        df_tabela = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, Se, Sy, ns)
        fig = plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes)
        
        # Constrói o Super PDF
        pdf_bytes = gerar_relatorio_integrado(ex_escolhido, material, df_tabela, fig)
        
        st.success("Documento gerado com sucesso! Contém citações teóricas do material didático, explicações do algoritmo e diagramas.")
        st.download_button(
            label="📥 Baixar Laudo de Engenharia (PDF)",
            data=pdf_bytes,
            file_name=f"Laudo_CET948_{ex_escolhido.replace(' ', '')}.pdf",
            mime="application/pdf"
        )
