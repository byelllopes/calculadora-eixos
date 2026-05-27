import streamlit as st
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

st.set_page_config(
    page_title="Calculadora de Eixos",
    page_icon="logo_uesc.png",
    layout="wide"
)

st.title("Calculadora de Eixos")

# =========================================================
# 1. MATEMÁTICA E DIMENSIONAMENTO DE FADIGA
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
        D_min = calcular_diametro_local(M_local, T_local, V_local, Kt, Se, Sy, ns)
        
        dados.append({
            "Ponto": nomes[i], "Z (pol)": z_val, "Kt": Kt,
            "Momento M": M_local, "Torque T": T_local, 
            "Cortante V": V_local, "D_min": D_min
        })
    return pd.DataFrame(dados)

def plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes):
    fig, axs = plt.subplots(3, 2, figsize=(14, 12), sharex=True)
    M_res = np.sqrt(My**2 + Mx**2)

    def annotate_plot(ax, data, title, is_step=False, color_base='blue'):
        ax.plot(z, data, color=color_base, drawstyle='steps-post' if is_step else 'default')
        ax.fill_between(z, data, step='post' if is_step else None, alpha=0.15, color=color_base)
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.axhline(0, color='black', linewidth=1)
        
        for i, zp in enumerate(z_pontos):
            ax.axvline(zp, color='black', linestyle=':', alpha=0.4)
            if is_step and i < len(z_pontos) - 1:
                mid_zp = (zp + z_pontos[i+1]) / 2.0
                mid_idx = (np.abs(z - mid_zp)).argmin()
                val_plateau = data[mid_idx]
                if abs(val_plateau) > 0.1:
                    ax.annotate(f"{val_plateau:.1f}", (mid_zp, val_plateau), 
                                textcoords="offset points", xytext=(0, 4), ha='center', 
                                fontsize=9, fontweight='bold', color='black',
                                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))
            elif not is_step:
                idx = (np.abs(z - zp)).argmin()
                val = data[idx]
                if abs(val) > 0.1:
                    ax.plot(zp, val, 'ko', markersize=4)
                    ax.annotate(f"{val:.1f}", (zp, val), 
                                textcoords="offset points", xytext=(0, 6), ha='center', 
                                fontsize=9, fontweight='bold', color='black')

    annotate_plot(axs[0, 0], T_mesh, "Diagrama de Torque (T) [lb.pol]", is_step=True, color_base='green')
    annotate_plot(axs[1, 0], Vx, "Esforço Cortante XZ (Vx) [lb]", is_step=True, color_base='blue')
    annotate_plot(axs[2, 0], My, "Momento Fletor XZ (My) [lb.pol]", is_step=False, color_base='red')
    
    annotate_plot(axs[0, 1], Vy, "Esforço Cortante YZ (Vy) [lb]", is_step=True, color_base='blue')
    annotate_plot(axs[1, 1], Mx, "Momento Fletor YZ (Mx) [lb.pol]", is_step=False, color_base='red')
    annotate_plot(axs[2, 1], M_res, "Momento Fletor Resultante (M_max) [lb.pol]", is_step=False, color_base='purple')

    for ax in [axs[0,0], axs[0,1]]:
        for i, zp in enumerate(z_pontos):
            ax.text(zp, ax.get_ylim()[1], f" {nomes[i]}", rotation=90, va='top', ha='right', alpha=0.7, fontsize=8)

    plt.tight_layout()
    return fig

# =========================================================
# 2. MOTORES DE RESOLUÇÃO
# =========================================================
def motor_ex1_2(n, P, Z_dentes, Pd, D_polia):
    T = (P * 63025) / n
    F_tB = T / ((Z_dentes / Pd) / 2.0)
    F_rB = F_tB * math.tan(math.radians(20))
    F_tD = T / (D_polia / 2.0)
    F_D = 1.5 * F_tD
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
    dados_calc = {"T": T, "FtB": F_tB, "FrB": F_rB, "FtD": F_tD, "FD": F_D, "FDx": F_Dx, "FDy": F_Dy, "RAx": R_Ax, "RCx": R_Cx, "RAy": R_Ay, "RCy": R_Cy}
    return z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list, dados_calc

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
    dados_calc = {"TA": T_A, "TC": T_C, "TD": T_D, "FA": F_A, "FtC": F_tC, "FrC": F_rC, "FD": F_D, "RBx": R_Bx, "REx": R_Ex, "RBy": R_By, "REy": R_Ey}
    return z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list, dados_calc

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
    dados_calc = {"TC": T_C, "TB": T_B, "TD": T_D, "TE": T_E, "FtB": F_tB, "FrB": F_rB, "FCx": F_Cx, "FCy": F_Cy, "FD": F_D, "FEx": F_Ex, "FEy": F_Ey, "RAx": R_Ax, "RFx": R_Fx, "RAy": R_Ay, "RFy": R_Fy}
    return z, Vx, Vy, My, Mx, T_mesh, z_pontos, nomes, kt_list, dados_calc

# =========================================================
# 3. GERADOR DO SUPER PDF
# =========================================================
DADOS_MATERIAIS = {
    "Exercício 1": {"nome": "Aço SAE 1040 estirado a frio", "Sy": 60000, "Se": 30000},
    "Exercício 2": {"nome": "Aço SAE 1040 estirado a frio", "Sy": 60000, "Se": 30000},
    "Exercício 3": {"nome": "Aço SAE 1117 CD", "Sy": 68000, "Se": 34000}, 
    "Exercício 4": {"nome": "Aço SAE 1137 OQT 1300", "Sy": 93000, "Se": 46500}
}

def clean_text(text):
    return text.encode('latin-1', 'replace').decode('latin-1')

def equacao(pdf, eq_literal, eq_numeros):
    pdf.set_font("Times", 'I', 12)
    pdf.cell(0, 6, clean_text(eq_literal), ln=True, align='C')
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 6, clean_text(eq_numeros), ln=True, align='C')
    pdf.ln(2)

def gerar_relatorio_lote(lista_exercicios, ns):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(30, 25, 20)
    
    # ================= CAPA =================
    pdf.add_page()
    if os.path.exists("logo_uesc.png"):
        pdf.image("logo_uesc.png", x=92.5, y=25, w=25)
        pdf.ln(45)
    else:
        pdf.ln(55)
        
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 6, clean_text("UNIVERSIDADE ESTADUAL DE SANTA CRUZ - UESC"), ln=True, align='C')
    pdf.cell(0, 6, clean_text("DEPARTAMENTO DE CIÊNCIAS EXATAS E TECNOLÓGICAS - DCET"), ln=True, align='C')
    pdf.cell(0, 6, clean_text("CURSO DE ENGENHARIA MECÂNICA"), ln=True, align='C')
    
    pdf.ln(60)
    pdf.set_font("Times", 'B', 18)
    pdf.cell(0, 8, clean_text("PROJETO DE EIXOS E CHAVETAS"), ln=True, align='C')
    pdf.set_font("Times", 'B', 14)
    pdf.cell(0, 8, clean_text("Resolução Detalhada da Lista de Exercícios 02"), ln=True, align='C')
    
    pdf.set_y(-50)
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 6, clean_text("Ilhéus - BA"), ln=True, align='C')
    pdf.cell(0, 6, clean_text("2026"), ln=True, align='C')

    # ================= FOLHA DE ROSTO =================
    pdf.add_page()
    pdf.set_y(40)
    pdf.set_left_margin(90)
    pdf.set_font("Times", 'B', 11)
    equipe = [
        "Cauê Oliveira Viana (202310921)",
        "Claudio Avila Rosa Filho (202310661)",
        "Davi Lisboa da Silva Almeida (202310922)",
        "Gustavo Moreira dos Santos (202310663)",
        "Iago Campos de Melo (202311585)",
        "João Gabryell Lopes Santana (202110927)",
        "Kaike Santos dos Santos (202311309)",
        "Pedro Enrique Nascimento Santos (202211370)",
        "Tharcizio Rubens Santos Mota (202211373)"
    ]
    for membro in equipe:
        pdf.cell(0, 5, clean_text(membro), ln=True, align='L')
    
    pdf.set_left_margin(30)
    pdf.ln(30)
    pdf.set_font("Times", 'B', 16)
    pdf.cell(0, 8, clean_text("LISTA DE EXERCÍCIO --- Eixos e Chavetas:"), ln=True, align='C')
    pdf.cell(0, 8, clean_text("Equivalente ao 2º crédito --- 2026.1"), ln=True, align='C')
    
    pdf.ln(30)
    pdf.set_left_margin(90)
    pdf.set_font("Times", '', 11)
    justificativa = "Trabalho apresentado como critério de avaliação do 2º crédito da disciplina CET 948 -- Elementos de Máquinas I.\n\nTurma T07. Dia da entrega do crédito: 27/05/2026."
    pdf.multi_cell(0, 6, clean_text(justificativa), align='J')
    pdf.set_left_margin(30)
    
    pdf.ln(25)
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 6, clean_text("Professor: Dr. José Carlos de Camargo"), ln=True, align='C')
    pdf.set_y(-50)
    pdf.cell(0, 6, clean_text("Ilhéus - BA"), ln=True, align='C')
    pdf.cell(0, 6, clean_text("2026"), ln=True, align='C')
    
    # ================= INTRODUÇÃO =================
    pdf.add_page()
    pdf.set_font("Times", 'B', 16)
    pdf.cell(0, 10, clean_text("Introdução e Complementos Técnicos"), ln=True)
    pdf.set_font("Times", '', 12)
    intro = "Para todos os problemas de eixos rotativos sujeitos a carregamentos combinados de flexão e torção cíclica, adota-se a formulação da norma ASME/Von Mises para fadiga:\n"
    pdf.multi_cell(0, 6, clean_text(intro))
    pdf.ln(2)

    # Imagem da fórmula ASME
    if os.path.exists("formula_asme.png"):
        y_atual = pdf.get_y()
        pdf.image("formula_asme.png", x=55, y=y_atual, w=100) 
        pdf.set_y(y_atual + 25) 
    else:
        pdf.ln(5)
        pdf.set_font("Times", 'I', 10)
        pdf.cell(0, 6, clean_text("[Para exibir a equação aqui, salve o arquivo como 'formula_asme.png' na mesma pasta]"), ln=True, align='C')
        pdf.ln(5)

    pdf.set_font("Times", '', 12)
    intro2 = "O dimensionamento escala os diâmetros mínimos de forma individual para cada elemento (D1, D2, D3...) com base nos fatores de concentração de tensão (Kt).\n\n"
    intro2 += "A seguir, são descritos os conceitos e complementos técnicos que fundamentam as memórias de cálculo deste laudo:\n"
    pdf.multi_cell(0, 6, clean_text(intro2))
    pdf.ln(10) # ESPAÇAMENTO AUMENTADO AQUI PARA "RESPIRAR" ANTES DA LISTA

    fundamentos = [
        ("Afastamentos dos elementos", "Os afastamentos representam as distâncias entre mancais, engrenagens e pontos de aplicação das forças. Essas distâncias influenciam diretamente o momento fletor do eixo."),
        ("Torque transmitido", "O torque representa o esforço de torção responsável pela transmissão de potência no eixo. Quanto maior a potência transmitida, maior o torque atuante."),
        ("Forças atuantes", "As forças tangenciais e radiais aplicadas pelos elementos mecânicos geram esforços de flexão no eixo."),
        ("Diagrama de corpo livre", "No diagrama de corpo livre representamos todas as forças e reações atuantes no eixo para aplicar as equações de equilíbrio."),
        ("Reações nos mancais", "As reações nos mancais foram calculadas utilizando as equações de equilíbrio estático. Elas representam as forças de apoio que equilibram o sistema."),
        ("Esforço cortante", "O diagrama de esforço cortante mostra como as forças internas variam ao longo do eixo. As mudanças no gráfico ocorrem nos pontos de aplicação das forças."),
        ("Momento fletor", "O momento fletor representa a tendência de flexão do eixo. O ponto de maior momento é considerado crítico para o dimensionamento."),
        ("Torção no eixo", "A transmissão de torque gera tensões de cisalhamento devido à torção no eixo."),
        ("Dimensionamento", "O dimensionamento foi realizado considerando os esforços combinados de flexão e torção para garantir segurança mecânica."),
        ("Chavetas", "A chaveta é responsável pela transmissão de torque entre o eixo e o elemento acoplado.")
    ]

    for titulo, desc in fundamentos:
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 6, clean_text(f"- {titulo}:"), ln=True)
        pdf.set_font("Times", '', 12)
        pdf.multi_cell(0, 6, clean_text(desc))
        pdf.ln(8) # ESPAÇAMENTO GENEROSO ENTRE OS TÓPICOS PARA PREENCHER BEM AS PÁGINAS
    
    # ================= RESOLUÇÃO DOS EXERCÍCIOS =================
    for ex in lista_exercicios:
        mat_info = DADOS_MATERIAIS[ex]
        pdf.add_page()
        pdf.set_font("Times", 'B', 16)
        pdf.cell(0, 10, clean_text(f"Resolução - {ex}"), ln=True)
        pdf.set_font("Times", '', 12)
        pdf.cell(0, 6, clean_text(f"Material Especificado: {mat_info['nome']}"), ln=True)
        pdf.ln(5)
        
        # --- EXERCÍCIOS 1 E 2 ---
        if ex in ["Exercício 1", "Exercício 2"]:
            n, P = (550, 30.0) if ex == "Exercício 1" else (750, 20.0)
            z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, dc = motor_ex1_2(n, P, 96, 6.0, 10.0 if ex == "Exercício 1" else 9.0)
            
            pdf.set_font("Times", 'B', 12)
            pdf.cell(0, 8, clean_text("Passo 1 - Torque transmitido"), ln=True)
            pdf.set_font("Times", '', 12)
            pdf.cell(0, 6, clean_text(f"Dados: n = {n} rpm, P = {P} hp."), ln=True)
            equacao(pdf, "T = (P * 63025) / n", f"T = ({P} * 63025) / {n} = {dc['T']:.2f} lb.pol")
            
            pdf.set_font("Times", 'B', 12)
            pdf.cell(0, 8, clean_text("Passo 2 - Forças atuantes nos elementos"), ln=True)
            pdf.set_font("Times", '', 12)
            pdf.cell(0, 6, clean_text(">> Na Engrenagem B (z = 10 pol):"), ln=True)
            equacao(pdf, "F_tB = T / R_B", f"F_tB = {dc['T']:.2f} / 8 = {dc['FtB']:.2f} lb")
            equacao(pdf, "F_rB = F_tB * tan(20 graus)", f"F_rB = {dc['FtB']:.2f} * 0.364 = {dc['FrB']:.2f} lb")
            
            pdf.cell(0, 6, clean_text(f">> Na Polia D (z = 26 pol, D = {10.0 if ex=='Exercício 1' else 9.0} pol):"), ln=True)
            equacao(pdf, "F_D = 1.5 * (T / R_D)", f"F_D = 1.5 * ({dc['T']:.2f} / {5.0 if ex=='Exercício 1' else 4.5}) = {dc['FD']:.2f} lb")
            equacao(pdf, "F_Dx = F_D * cos(40 graus)", f"F_Dx = {dc['FD']:.2f} * 0.766 = {dc['FDx']:.2f} lb")
            equacao(pdf, "F_Dy = F_D * sin(40 graus)", f"F_Dy = {dc['FD']:.2f} * 0.642 = {abs(dc['FDy']):.2f} lb")
            
            pdf.set_font("Times", 'B', 12)
            pdf.cell(0, 8, clean_text("Passo 3 - Reações nos mancais (Equilíbrio Estático)"), ln=True)
            pdf.set_font("Times", '', 12)
            pdf.cell(0, 6, clean_text(">> Mancais A (z=0) e C (z=20) no Plano Horizontal (XZ):"), ln=True)
            equacao(pdf, "R_Cx = - [ (F_tB * 10) + (F_Dx * 26) ] / 20", f"R_Cx = {dc['RCx']:.2f} lb")
            equacao(pdf, "R_Ax = - (F_tB + F_Dx + R_Cx)", f"R_Ax = {dc['RAx']:.2f} lb")
            
            pdf.cell(0, 6, clean_text(">> Mancais A (z=0) e C (z=20) no Plano Vertical (YZ):"), ln=True)
            equacao(pdf, "R_Cy = - [ (-F_rB * 10) + (F_Dy * 26) ] / 20", f"R_Cy = {dc['RCy']:.2f} lb")
            equacao(pdf, "R_Ay = - (-F_rB + F_Dy + R_Cy)", f"R_Ay = {dc['RAy']:.2f} lb")
            
        # --- EXERCÍCIO 3 ---
        elif ex == "Exercício 3":
            z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, dc = motor_ex3(200, 10.0, 6.0, 4.0)
            
            pdf.set_font("Times", 'B', 12)
            pdf.cell(0, 8, clean_text("Passo 1 - Distribuição de Torque"), ln=True)
            equacao(pdf, "T_A = (10 * 63025) / 200", f"Entrada T_A = {dc['TA']:.2f} lb.pol")
            equacao(pdf, "T_C = (6 * 63025) / 200", f"Saída T_C = {dc['TC']:.2f} lb.pol")
            equacao(pdf, "T_D = (4 * 63025) / 200", f"Saída T_D = {dc['TD']:.2f} lb.pol")
            
            pdf.set_font("Times", 'B', 12)
            pdf.cell(0, 8, clean_text("Passo 2 - Forças atuantes nos elementos"), ln=True)
            pdf.set_font("Times", '', 12)
            pdf.cell(0, 6, clean_text(">> Na Polia A (z = 0 pol):"), ln=True)
            equacao(pdf, "F_A = 2.0 * (T_A / R_A)", f"F_A = {dc['FA']:.2f} lb (-Y)")
            
            pdf.cell(0, 6, clean_text(">> Na Engrenagem C (z = 12 pol):"), ln=True)
            equacao(pdf, "F_tC = T_C / R_C", f"F_tC = {dc['FtC']:.2f} lb (+X)")
            equacao(pdf, "F_rC = F_tC * tan(20 graus)", f"F_rC = {dc['FrC']:.2f} lb (+Y)")
            
            pdf.cell(0, 6, clean_text(">> Na Corrente D (z = 22 pol):"), ln=True)
            equacao(pdf, "F_D = T_D / R_D", f"F_D = {dc['FD']:.2f} lb (+Y)")
            
            pdf.set_font("Times", 'B', 12)
            pdf.cell(0, 8, clean_text("Passo 3 - Reações de Apoio nos Mancais B(z=6) e E(z=26)"), ln=True)
            pdf.set_font("Times", '', 12)
            equacao(pdf, "Plano XZ (Horizontal)", f"R_Bx = {dc['RBx']:.2f} lb | R_Ex = {dc['REx']:.2f} lb")
            equacao(pdf, "Plano YZ (Vertical)", f"R_By = {dc['RBy']:.2f} lb | R_Ey = {dc['REy']:.2f} lb")

        # --- EXERCÍCIO 4 ---
        else:
            z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, dc = motor_ex4(480)
            
            pdf.set_font("Times", 'B', 12)
            pdf.cell(0, 8, clean_text("Passo 1 - Torques e Forças Atuantes"), ln=True)
            equacao(pdf, "T_C = (11 * 63025) / 480", f"T_C = {dc['TC']:.2f} lb.pol (Entrada)")
            equacao(pdf, "T_B = (5 * 63025) / 480", f"T_B = {dc['TB']:.2f} lb.pol (Pinhão B)")
            
            pdf.set_font("Times", '', 12)
            pdf.cell(0, 6, clean_text(">> Pinhão B (z = 4 pol):"), ln=True)
            equacao(pdf, "F_tB = T_B / R_B", f"F_tB = {dc['FtB']:.2f} lb (+X)")
            
            pdf.cell(0, 6, clean_text(">> Corrente C (z = 10 pol) a 15 graus da vertical:"), ln=True)
            equacao(pdf, "F_Cx = -F_C * sin(15 graus)", f"F_Cx = {dc['FCx']:.2f} lb")
            equacao(pdf, "F_Cy = -F_C * cos(15 graus)", f"F_Cy = {dc['FCy']:.2f} lb")
            
            pdf.cell(0, 6, clean_text(">> Polia E (z = 20 pol) a 30 graus da horizontal:"), ln=True)
            equacao(pdf, "F_Ex = F_E * cos(30 graus)", f"F_Ex = {dc['FEx']:.2f} lb (+X)")
            equacao(pdf, "F_Ey = F_E * sin(30 graus)", f"F_Ey = {dc['FEy']:.2f} lb (+Y)")
            
            pdf.set_font("Times", 'B', 12)
            pdf.cell(0, 8, clean_text("Passo 2 - Reações de Apoio (Mancais A e F)"), ln=True)
            pdf.set_font("Times", '', 12)
            equacao(pdf, "Plano XZ (Horizontal)", f"R_Ax = {dc['RAx']:.2f} lb | R_Fx = {dc['RFx']:.2f} lb")
            equacao(pdf, "Plano YZ (Vertical)", f"R_Ay = {dc['RAy']:.2f} lb | R_Fy = {dc['RFy']:.2f} lb")

        # ==================== GRÁFICOS (PASSO 4) ====================
        if pdf.get_y() + 150 > 280:
            pdf.add_page()
        else:
            pdf.ln(5)
            
        pdf.set_font("Times", 'B', 14)
        pdf.cell(0, 8, clean_text(f"Passo 4 - Diagramas de Esforços Internos"), ln=True)
        
        fig = plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.savefig(tmp.name, format="png", bbox_inches="tight", dpi=200)
            pdf.image(tmp.name, x=25, y=pdf.get_y(), w=160) 
        plt.close(fig)
        
        pdf.set_y(pdf.get_y() + 130)
        
        # ==================== DIMENSIONAMENTO (PASSO 5) ====================
        df_tabela = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, mat_info["Se"], mat_info["Sy"], ns)
        linha_critica = df_tabela.loc[df_tabela['D_min'].idxmax()]
        
        if pdf.get_y() + 70 > 280:
            pdf.add_page()
            
        pdf.ln(10)
        pdf.set_font("Times", 'B', 14)
        pdf.cell(0, 8, clean_text("Passo 5 - Dimensionamento e Chavetas"), ln=True)
        
        pdf.set_font("Times", '', 12)
        pdf.cell(0, 6, clean_text(f"Ponto crítico selecionado: {linha_critica['Ponto']} (z = {linha_critica['Z (pol)']} pol)."), ln=True)
        
        equacao(pdf, "M_max = sqrt( M_y^2 + M_x^2 )", f"M_max = {linha_critica['Momento M']:.1f} lb.pol")
        
        # Equação ASME sem caracteres difíceis
        equacao(pdf, "d = [ (32*ns/pi) * sqrt( (M_max/Se)^2 + 0.75*(T/Sy)^2 ) ]^(1/3)", f"d = {linha_critica['D_min']:.2f} pol")

        pdf.ln(5)
        pdf.set_font("Times", 'B', 10)
        cols = [25, 12, 10, 25, 25, 25, 30]
        headers = ["Elemento", "Z", "Kt", "Momento M", "Torque T", "Cortante V", "D_min (pol)"]
        for i in range(len(cols)):
            pdf.cell(cols[i], 8, headers[i], border=1, align='C')
        pdf.ln()
        
        pdf.set_font("Times", '', 10)
        for i in range(len(df_tabela)):
            pdf.cell(cols[0], 8, clean_text(str(df_tabela.iloc[i, 0])), border=1, align='C')
            pdf.cell(cols[1], 8, str(df_tabela.iloc[i, 1]), border=1, align='C')
            pdf.cell(cols[2], 8, str(df_tabela.iloc[i, 2]), border=1, align='C')
            pdf.cell(cols[3], 8, f"{df_tabela.iloc[i, 3]:.1f}", border=1, align='C')
            pdf.cell(cols[4], 8, f"{df_tabela.iloc[i, 4]:.1f}", border=1, align='C')
            pdf.cell(cols[5], 8, f"{df_tabela.iloc[i, 5]:.1f}", border=1, align='C')
            pdf.set_font("Times", 'B', 10)
            pdf.cell(cols[6], 8, f"{df_tabela.iloc[i, 6]:.3f}", border=1, align='C')
            pdf.set_font("Times", '', 10)
            pdf.ln()

    # ================= CONCLUSÃO E REFERÊNCIAS (ÚLTIMA PÁGINA) =================
    pdf.add_page()
    pdf.set_font("Times", 'B', 16)
    pdf.cell(0, 10, clean_text("Conclusão Geral"), ln=True)
    pdf.set_font("Times", '', 12)
    conc_text = "Neste trabalho, os eixos de transmissão foram analisados e dimensionados com sucesso sob carregamentos de fadiga severos. Aplicando as equações de equilíbrio estático, foi possível gerar os diagramas de corpo livre, esforço cortante e momento fletor espacial.\n\n"
    conc_text += "A utilização da teoria da energia de distorção combinada de Von Mises (via norma ASME) permitiu escalar com precisão o diâmetro da seção transversal do eixo para cada degrau e alojamento de rolamento, compensando as descontinuidades geométricas por meio dos fatores de concentração de tensões (Kt)."
    pdf.multi_cell(0, 6, clean_text(conc_text))
    
    pdf.ln(15)
    pdf.set_font("Times", 'B', 16)
    pdf.cell(0, 10, clean_text("Referências Bibliográficas"), ln=True)
    pdf.set_font("Times", '', 12)
    referencias = [
        "1. SHIGLEY, J. E., MISCHKE, C. R., & BUDYNAS, R. G. (2005). Projeto de Engenharia Mecânica. 7a Edição. Bookman.",
        "2. NORTON, R. L. (2013). Projetos de Máquinas: Uma Abordagem Integrada. 4a Edição. Bookman.",
        "3. JUVINALL, R. C., & MARSHEK, K. M. (2008). Fundamentos do Projeto de Componentes de Máquinas. 4a Edição. LTC.",
        "4. MOTT, R. L. (2015). Elementos de Máquinas em Projetos Mecânicos. 5a Edição. Pearson.",
        "5. CAMARGO, J. C. (2026). Material Didático - CET 948: Elementos de Máquinas I. Universidade Estadual de Santa Cruz (UESC)."
    ]
    for ref in referencias:
        pdf.multi_cell(0, 6, clean_text(ref))
        pdf.ln(2)

    return pdf.output(dest="S").encode("latin-1", errors="replace")

# =========================================================
# 4. ESTRUTURA DO SITE E MENU LATERAL
# =========================================================
st.set_page_config(page_title="Projeto Eixos UESC", layout="wide")
st.sidebar.markdown("# 🎓 UESC - Eng. Mecânica")
st.sidebar.markdown("### Elementos de Máquinas I")
st.sidebar.markdown("---")

menu = st.sidebar.selectbox("Navegação:", [
    "Visualizar Exercício 1", 
    "Visualizar Exercício 2", 
    "Visualizar Exercício 3", 
    "Visualizar Exercício 4", 
    "📄 Gerar Relatório Oficial (LaTeX)"
])

# =========================================================
# INTERFACES DE VISUALIZAÇÃO NA TELA
# =========================================================
if menu in ["Visualizar Exercício 1", "Visualizar Exercício 2"]:
    st.title(f"⚙️ Análise Dinâmica - {menu.split()[-2]} {menu.split()[-1]}")
    n = st.sidebar.number_input("Rotação (RPM)", value=550 if "1" in menu else 750)
    P = st.sidebar.number_input("Potência (HP)", value=30.0 if "1" in menu else 20.0)
    
    st.sidebar.header("Propriedades Específicas")
    Sy = st.sidebar.number_input("Sy (psi)", value=60000)
    Se = st.sidebar.number_input("Se (psi)", value=30000)
    ns = st.sidebar.number_input("Fator de Segurança", value=2.0)
    
    if st.button("Calcular Esforços"):
        z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, dc = motor_ex1_2(n, P, 96, 6.0, 10.0)
        df_tab = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, Se, Sy, ns)
        st.dataframe(df_tab.style.format({"Momento M": "{:.1f}", "Torque T": "{:.1f}", "Cortante V": "{:.1f}", "D_min": "{:.3f}"}), use_container_width=True)
        st.pyplot(plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes))

elif menu == "Visualizar Exercício 3":
    st.title("⚙️ Análise Dinâmica - Exercício 3")
    n = st.sidebar.number_input("Rotação (RPM)", value=200)
    
    st.sidebar.header("Propriedades Específicas (Ex: SAE 1117)")
    Sy = st.sidebar.number_input("Sy (psi)", value=68000)
    Se = st.sidebar.number_input("Se (psi)", value=34000)
    ns = st.sidebar.number_input("Fator de Segurança", value=2.0)
    
    if st.button("Calcular Esforços"):
        z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, dc = motor_ex3(n, 10.0, 6.0, 4.0)
        df_tab = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, Se, Sy, ns)
        st.dataframe(df_tab.style.format({"Momento M": "{:.1f}", "Torque T": "{:.1f}", "Cortante V": "{:.1f}", "D_min": "{:.3f}"}), use_container_width=True)
        st.pyplot(plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes))

elif menu == "Visualizar Exercício 4":
    st.title("⚙️ Análise Dinâmica - Exercício 4")
    n = st.sidebar.number_input("Rotação (RPM)", value=480)
    
    st.sidebar.header("Propriedades Específicas (Ex: SAE 1137)")
    Sy = st.sidebar.number_input("Sy (psi)", value=93000)
    Se = st.sidebar.number_input("Se (psi)", value=46500)
    ns = st.sidebar.number_input("Fator de Segurança", value=2.0)
    
    if st.button("Calcular Esforços"):
        z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, dc = motor_ex4(n)
        df_tab = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, Se, Sy, ns)
        st.dataframe(df_tab.style.format({"Momento M": "{:.1f}", "Torque T": "{:.1f}", "Cortante V": "{:.1f}", "D_min": "{:.3f}"}), use_container_width=True)
        st.pyplot(plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes))

# =========================================================
# INTERFACE UNIFICADA DO LAUDO
# =========================================================
elif menu == "📄 Gerar Relatório Oficial (LaTeX)":
    st.title("📄 Emissão de Relatório Acadêmico")
    st.markdown("Gere o PDF final com a estrutura exata do documento LaTeX da equipe, incluindo Capa da UESC, Folha de Rosto e Memória de Cálculo passo a passo.")
    
    exercicios_selecionados = st.multiselect(
        "Selecione as questões para incluir na entrega:", 
        ["Exercício 1", "Exercício 2", "Exercício 3", "Exercício 4"],
        default=["Exercício 1", "Exercício 2", "Exercício 3", "Exercício 4"]
    )
    
    st.sidebar.header("Segurança Global (Para o Relatório)")
    ns = st.sidebar.number_input("Fator de Segurança (ns)", value=2.0)
    
    if st.button("Gerar PDF Oficial (Capa + Cálculos)", type="primary"):
        if not exercicios_selecionados:
            st.warning("Selecione pelo menos um exercício!")
        else:
            with st.spinner("Construindo documento acadêmico..."):
                pdf_bytes = gerar_relatorio_lote(exercicios_selecionados, ns)
                
            st.success("Relatório gerado com a estrutura oficial da UESC!")
            st.download_button(
                label="📥 Baixar Trabalho Final (PDF)",
                data=pdf_bytes,
                file_name=f"Trabalho_Eixos_UESC.pdf",
                mime="application/pdf"
            )
