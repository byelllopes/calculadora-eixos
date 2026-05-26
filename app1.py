import streamlit as st
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

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
# 3. GERADOR DO SUPER PDF (IDÊNTICO AO LATEX)
# =========================================================
DADOS_MATERIAIS = {
    "Exercício 1": {"nome": "Aço SAE 1040 estirado a frio", "Sy": 60000, "Se": 30000},
    "Exercício 2": {"nome": "Aço SAE 1040 estirado a frio", "Sy": 60000, "Se": 30000},
    "Exercício 3": {"nome": "Aço SAE 1117 CD", "Sy": 68000, "Se": 34000}, 
    "Exercício 4": {"nome": "Aço SAE 1137 OQT 1300", "Sy": 93000, "Se": 46500}
}

def clean_text(text):
    return text.encode('latin-1', 'replace').decode('latin-1')

def gerar_relatorio_lote(lista_exercicios, ns):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(30, 30, 20)
    
    # ================= CAPA (PÁGINA 1) =================
    pdf.add_page()
    if os.path.exists("logo_uesc.png"):
        pdf.image("logo_uesc.png", x=92.5, y=30, w=25)
        pdf.ln(40)
    else:
        pdf.ln(50)
        
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 6, clean_text("UNIVERSIDADE ESTADUAL DE SANTA CRUZ - UESC"), ln=True, align='C')
    pdf.cell(0, 6, clean_text("DEPARTAMENTO DE ENGENHARIAS E COMPUTAÇÃO - DEC"), ln=True, align='C')
    pdf.cell(0, 6, clean_text("CURSO DE ENGENHARIA MECÂNICA"), ln=True, align='C')
    
    pdf.ln(65)
    pdf.set_font("Times", 'B', 18)
    pdf.cell(0, 8, clean_text("PROJETO DE EIXOS E CHAVETAS"), ln=True, align='C')
    pdf.set_font("Times", 'B', 14)
    pdf.cell(0, 8, clean_text("Resolução Detalhada da Lista de Exercícios 02"), ln=True, align='C')
    
    pdf.set_y(-50)
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 6, clean_text("Ilhéus - BA"), ln=True, align='C')
    pdf.cell(0, 6, clean_text("2026"), ln=True, align='C')

    # ================= FOLHA DE ROSTO (PÁGINA 2) =================
    pdf.add_page()
    
    # Equipe (Minipage right-aligned simulada)
    pdf.set_y(40)
    pdf.set_left_margin(90) # Empurra a margem esquerda pro meio da folha
    pdf.set_font("Times", 'B', 11)
    equipe = "Cauê Oliveira Viana (202110921)\nDavi Lisboa da Silva Almeida (202110922)\nIago Campos de Melo (202311585)\nJoão Gabryell Lopes Santana (202110926)\nJoão Felipe Santos Matos (202110921)\nKaike Santos dos Santos (202111309)"
    pdf.multi_cell(0, 6, clean_text(equipe), align='L')
    pdf.set_left_margin(30) # Reseta margem normal
    
    pdf.ln(35)
    pdf.set_font("Times", 'B', 16)
    pdf.cell(0, 8, clean_text("LISTA DE EXERCÍCIO --- Eixos e Chavetas:"), ln=True, align='C')
    pdf.cell(0, 8, clean_text("Equivalente ao 2º crédito --- 2026.1"), ln=True, align='C')
    
    pdf.ln(30)
    # Justificativa Institucional (Minipage right-aligned)
    pdf.set_left_margin(90)
    pdf.set_font("Times", '', 11)
    justificativa = "Trabalho apresentado como critério de avaliação do 2º crédito da disciplina CET548 -- Elementos de Máquinas I.\n\nTurma T02. Dia da entrega do crédito: 27/06/2026."
    pdf.multi_cell(0, 6, clean_text(justificativa), align='J')
    pdf.set_left_margin(30)
    
    pdf.ln(25)
    pdf.set_font("Times", 'B', 12)
    pdf.cell(0, 6, clean_text("Professor: José Carlos de Camargo"), ln=True, align='C')
    
    pdf.set_y(-50)
    pdf.cell(0, 6, clean_text("Ilhéus - BA"), ln=True, align='C')
    pdf.cell(0, 6, clean_text("2026"), ln=True, align='C')

    # ================= INTRODUÇÃO GERAL (PÁGINA 3) =================
    pdf.add_page()
    pdf.set_font("Times", 'B', 16)
    pdf.cell(0, 10, clean_text("Introdução Geral de Projeto"), ln=True)
    pdf.set_font("Times", '', 12)
    intro = "Para todos os problemas de eixos rotativos sujeitos a carregamentos combinados de flexão e torção cíclica, adota-se a formulação da norma ASME/Von Mises para fadiga:\n\nd = [ (32 * ns / pi) * sqrt( (M_max / Se)^2 + 0.75 * (T / Sy)^2 ) ]^(1/3)\n\n"
    intro += "O dimensionamento escala os diâmetros mínimos de forma individual para cada elemento (D1, D2, D3...) com base nos fatores de concentração de tensão (Kt)."
    pdf.multi_cell(0, 6, clean_text(intro))
    pdf.ln(10)
    pdf.cell(0, 0, "", "T") # Desenha a linha divisória (---)
    pdf.ln(10)
    
    # ================= RESOLUÇÃO DOS EXERCÍCIOS =================
    for ex in lista_exercicios:
        mat_info = DADOS_MATERIAIS[ex]
        
        pdf.add_page()
        pdf.set_font("Times", 'B', 16)
        pdf.cell(0, 10, clean_text(f"Resolução do {ex}"), ln=True)
        pdf.set_font("Times", 'B', 14)
        pdf.cell(0, 8, clean_text("1.1 Torques e Forças nos Elementos"), ln=True)
        pdf.set_font("Times", '', 12)
        
        # TEXTOS MATEMÁTICOS SIMULANDO O LATEX
        if ex in ["Exercício 1", "Exercício 2"]:
            n, P = (550, 30.0) if ex == "Exercício 1" else (750, 20.0)
            z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, dc = motor_ex1_2(n, P, 96, 6.0, 10.0 if ex == "Exercício 1" else 9.0)
            
            p1 = f"{chr(149)} Dados: n = {n} rpm, P = {P} hp. Material: {mat_info['nome']}.\n"
            p1 += f"{chr(149)} Torque no Eixo (T): T = ({P} * 63025) / {n} = {dc['T']:.2f} lb.pol\n"
            p1 += f"{chr(149)} Engrenagem B (z = 10 pol): Z = 96, Pd = 6 -> DB = 16 pol (RB = 8 pol).\n"
            p1 += f"      FtB = {dc['T']:.2f} / 8 = {dc['FtB']:.2f} lb (+X)\n"
            p1 += f"      FrB = {dc['FtB']:.2f} * tan(20) = {dc['FrB']:.2f} lb (-Y pois o pinhão força para baixo)\n"
            p1 += f"{chr(149)} Polia de Correia V em D (z = 26 pol): DD = 10 pol (RD = 5 pol).\n"
            p1 += f"      FtD = {dc['T']:.2f} / 5 = {dc['FtD']:.2f} lb -> FD = 1.5 * {dc['FtD']:.2f} = {dc['FD']:.2f} lb\n"
            p1 += f"      FDx = {dc['FD']:.2f} * cos(40) = {dc['FDx']:.2f} lb (+X)\n"
            p1 += f"      FDy = -{dc['FD']:.2f} * sin(40) = {dc['FDy']:.2f} lb (-Y)\n"
            pdf.multi_cell(0, 6, clean_text(p1))
            
            pdf.ln(4)
            pdf.set_font("Times", 'B', 14)
            pdf.cell(0, 8, clean_text("1.2 Reações de Apoio nos Mancais (A em z=0 e C em z=20)"), ln=True)
            pdf.set_font("Times", '', 12)
            p2 = f"{chr(149)} Plano Horizontal (XZ): RAx = {dc['RAx']:.2f} lb, RCx = {dc['RCx']:.2f} lb\n"
            p2 += f"{chr(149)} Plano Vertical (YZ): RAy = {dc['RAy']:.2f} lb, RCy = {dc['RCy']:.2f} lb\n"
            pdf.multi_cell(0, 6, clean_text(p2))
            
        elif ex == "Exercício 3":
            z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, dc = motor_ex3(200, 10.0, 6.0, 4.0)
            p1 = f"{chr(149)} Dados Operacionais: n = 200 rpm, Potência de entrada PA = 10 hp.\n"
            p1 += f"{chr(149)} Distribuição de Torque:\n"
            p1 += f"      TA = (10 * 63025) / 200 = {dc['TA']:.2f} lb.pol (Entrada em z=0 pol)\n"
            p1 += f"      TC = (6 * 63025) / 200 = {dc['TC']:.2f} lb.pol (Saída em z=12 pol)\n"
            p1 += f"      TD = (4 * 63025) / 200 = {dc['TD']:.2f} lb.pol (Saída em z=22 pol)\n"
            p1 += f"{chr(149)} Polia A (z = 0 pol, DA = 20 pol, RA = 10 pol):\n"
            p1 += f"      FtA = {dc['TA']:.2f} / 10 = {dc['TA']/10:.2f} lb -> FA = 2.0 * {dc['TA']/10:.2f} = {dc['FA']:.2f} lb (-Y)\n"
            p1 += f"{chr(149)} Engrenagem C (z = 12 pol, DC = 10 pol, RC = 5 pol):\n"
            p1 += f"      FtC = {dc['TC']:.2f} / 5 = {dc['FtC']:.2f} lb (+X)\n"
            p1 += f"      FrC = {dc['FtC']:.2f} * tan(20) = {dc['FrC']:.2f} lb (+Y)\n"
            p1 += f"{chr(149)} Corrente D (z = 22 pol, DD = 6 pol, RD = 3 pol):\n"
            p1 += f"      FD = {dc['TD']:.2f} / 3 = {dc['FD']:.2f} lb (+Y)\n"
            pdf.multi_cell(0, 6, clean_text(p1))
            
            pdf.ln(4)
            pdf.set_font("Times", 'B', 14)
            pdf.cell(0, 8, clean_text("1.2 Cálculo das Reações de Apoio nos Mancais B e E"), ln=True)
            pdf.set_font("Times", '', 12)
            p2 = f"Mancais localizados em B (z=6 pol) e E (z=26 pol):\n"
            p2 += f"{chr(149)} Plano Horizontal (XZ): RBx = {dc['RBx']:.2f} lb, REx = {dc['REx']:.2f} lb\n"
            p2 += f"{chr(149)} Plano Vertical (YZ): RBy = {dc['RBy']:.2f} lb, REy = {dc['REy']:.2f} lb\n"
            pdf.multi_cell(0, 6, clean_text(p2))
            
        else: # Ex 4
            z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, dc = motor_ex4(480)
            p1 = f"Eixo triturador de alumínio de alta performance operando a 480 rpm.\n"
            p1 += f"{chr(149)} Torques Calculados:\n"
            p1 += f"      TC = (11 * 63025) / 480 = {dc['TC']:.2f} lb.pol (Entrada)\n"
            p1 += f"      TB = {dc['TB']:.2f} lb.pol, TD = TE = {dc['TD']:.2f} lb.pol\n"
            p1 += f"{chr(149)} Pinhão B (z = 4 pol, DB = 3 pol, RB = 1.5 pol):\n"
            p1 += f"      FtB = {dc['FtB']:.2f} lb (+X), FrB = {dc['FrB']:.2f} lb (+Y)\n"
            p1 += f"{chr(149)} Corrente C (z = 10 pol, DC = 10 pol, RC = 5 pol):\n"
            p1 += f"      FC = {dc['TC']:.2f} / 5 = {dc['TC']/5:.2f} lb\n"
            p1 += f"      Decomposição angular a 15 graus da vertical: FCx = {dc['FCx']:.2f} lb, FCy = {dc['FCy']:.2f} lb\n"
            p1 += f"{chr(149)} Polia D (z = 16 pol, DD = 4 pol, RD = 2 pol): FD = {dc['FD']:.2f} lb (+Y)\n"
            p1 += f"{chr(149)} Polia E (z = 20 pol, DE = 4 pol, RE = 2 pol): FE = {dc['FD']:.2f} lb\n"
            p1 += f"      Inclinada a 30 graus da horizontal: FEx = {dc['FEx']:.2f} lb (+X), FEy = {dc['FEy']:.2f} lb (+Y)\n"
            pdf.multi_cell(0, 6, clean_text(p1))
            
            pdf.ln(4)
            pdf.set_font("Times", 'B', 14)
            pdf.cell(0, 8, clean_text("1.2 Cálculo Vetorial das Reações (Mancais A e F)"), ln=True)
            pdf.set_font("Times", '', 12)
            p2 = f"Apoios situados nas extremidades A (z=0 pol) e F (z=24 pol):\n"
            p2 += f"{chr(149)} Plano Horizontal (XZ): RAx = {dc['RAx']:.2f} lb, RFx = {dc['RFx']:.2f} lb\n"
            p2 += f"{chr(149)} Plano Vertical (YZ): RAy = {dc['RAy']:.2f} lb, RFy = {dc['RFy']:.2f} lb\n"
            pdf.multi_cell(0, 6, clean_text(p2))

        # ==================== GERENCIADOR DE GRÁFICOS ([H] do LaTeX) ====================
        # Se a altura atual + altura do gráfico (140mm) ultrapassar o fim da página, pula de página.
        if pdf.get_y() + 140 > 270:
            pdf.add_page()
        else:
            pdf.ln(5)
            
        pdf.set_font("Times", 'B', 14)
        pdf.cell(0, 8, clean_text(f"1.3 Diagramas de Esforços Solicitantes --- {ex}"), ln=True)
        
        fig = plotar_diagramas_completos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.savefig(tmp.name, format="png", bbox_inches="tight")
            # Inserindo com largura 160mm garante tamanho legível e proporção correta
            pdf.image(tmp.name, x=25, y=pdf.get_y(), w=160) 
        plt.close(fig)
        
        # Pula o cursor para baixo do gráfico
        pdf.set_y(pdf.get_y() + 135)
        
        # ==================== CONCLUSÃO CRÍTICA ====================
        df_tabela = gerar_tabela_pontos(z, Vx, Vy, My, Mx, T_mesh, z_p, nomes, kt_list, mat_info["Se"], mat_info["Sy"], ns)
        
        # Encontrando a linha do pior caso (Ponto crítico)
        linha_critica = df_tabela.loc[df_tabela['D_min'].idxmax()]
        
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 8, clean_text("1.4 Dimensionamento Ponto a Ponto e Seção Crítica"), ln=True)
        pdf.set_font("Times", '', 12)
        
        conclusao = f"O momento resultante máximo ocorreu no elemento {linha_critica['Ponto']} (z = {linha_critica['Z (pol)']} pol):\n"
        conclusao += f"M_max = {linha_critica['Momento M']:.1f} lb.pol | Torque = {linha_critica['Torque T']:.1f} lb.pol\n"
        pdf.multi_cell(0, 6, clean_text(conclusao))
        
        pdf.set_font("Times", 'B', 12)
        pdf.cell(0, 6, clean_text(f"Diâmetro Mínimo Admissível em {linha_critica['Ponto']}: d = {linha_critica['D_min']:.2f} pol."), ln=True)
        pdf.set_font("Times", '', 12)
        
        if ex == "Exercício 3":
            pdf.ln(2)
            pdf.cell(0, 6, clean_text(">> Recomenda-se diâmetro nominal comercial bruto de 1 5/8 pol para a seção central."), ln=True)
        elif ex == "Exercício 4":
            pdf.ln(2)
            pdf.cell(0, 6, clean_text(">> Incorporando restrições de anéis de retenção, estabelece-se diâmetro bruto de 1 1/4 pol."), ln=True)
            
        # Tabela Detalhada (Complementar)
        pdf.ln(8)
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
