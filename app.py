import streamlit as st
import pandas as pd
import numpy as np
import base64
from PIL import Image, ImageOps
import io
from supabase import create_client, Client

# =========================================================
# 1. CONFIGURAÇÕES DA PÁGINA & CONSTANTES
# =========================================================
st.set_page_config(page_title="Copa do Mundo de Vôlei 2026", layout="wide")
st.title("🏐 Copa do Mundo de Vôlei 2026 — Painel Estatístico")

FOTO_PADRAO_URL = "https://cdn-icons-png.flaticon.com/512/4333/4333609.png"

GRUPO_A = ["🇧🇷 Brasil", "🇺🇸 EUA", "🇫🇷 França", "🇯🇵 Japão"]
GRUPO_B = ["🇩🇪 Alemanha", "🇦🇷 Argentina", "🇪🇸 Espanha", "🇵🇹 Portugal"]
TODOS_TIMES = GRUPO_A + GRUPO_B

LISTA_POSICOES = ["Ponteiro(a)", "Central", "Levantador(a)", "Oposto(a)", "Líbero"]

LINKS_FUNDOS_LIMPOS = {
    "🇧🇷 Brasil": "https://i.postimg.cc/t4vHWsFP/Brasil.png",
    "🇺🇸 EUA": "https://i.postimg.cc/52KMLX8L/EUA.png",
    "🇫🇷 França": "https://i.postimg.cc/7Zty05S3/Franca.png",
    "🇯🇵 Japão": "https://i.postimg.cc/cLkNwvfB/Japao.png",
    "🇩🇪 Alemanha": "https://i.postimg.cc/sggrMYGZ/Alemanha.png",
    "🇦🇷 Argentina": "https://i.postimg.cc/pLctzmKF/Argentina.png",
    "🇪🇸 Espanha": "https://i.postimg.cc/HkvCXrbM/Espanha.png",
    "🇵🇹 Portugal": "https://i.postimg.cc/DwpKLS15/Portugal.png",
}

SUPABASE_URL = st.secrets["connections"]["supabase"]["url"]
SUPABASE_KEY = st.secrets["connections"]["supabase"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================================
# 2. FUNÇÕES DE CONEXÃO COM BANCO DE DADOS
# =========================================================
def carregar_jogadores():
    try:
        response = supabase.table("jogadores").select("*").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Garante preenchimento de colunas cruciais para o modelo
            df["ataques"] = df["ataques"].fillna(0).astype(int)
            df["bloqueios"] = df["bloqueios"].fillna(0).astype(int)
            df["aces"] = df["aces"].fillna(0).astype(int)
            df["altura_cm"] = df["altura_cm"].fillna(180).astype(int)
            df["idade"] = df["idade"].fillna(25).astype(int)
            df["posicao"] = df["posicao"].fillna("ponteiro").str.lower().str.replace("(a)", "", regex=False).str.strip()
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def carregar_partidas():
    try:
        response = supabase.table("partidas").select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def salvar_partida_banco(fase, time_a, time_b, sets_a, sets_b, placar_sets):
    try:
        dados = {
            "fase": fase, "time_a": time_a, "time_b": time_b,
            "sets_a": sets_a, "sets_b": sets_b, "placar_sets": placar_sets
        }
        supabase.table("partidas").insert(dados).execute()
        return True
    except Exception:
        return False

def atualizar_scout_jogador(jogador_id, ataques, bloqueios, aces):
    try:
        res = supabase.table("jogadores").select("ataques, bloqueios, aces").eq("id", jogador_id).execute()
        if res.data:
            at_at = (res.data[0]["ataques"] or 0) + ataques
            bl_at = (res.data[0]["bloqueios"] or 0) + bloqueios
            ac_at = (res.data[0]["aces"] or 0) + aces
            
            supabase.table("jogadores").update({
                "ataques": at_at, "bloqueios": bl_at, "aces": ac_at
            }).eq("id", jogador_id).execute()
            return True
        return False
    except Exception:
        return False

def converter_imagem_para_base64(arquivo_imagem):
    if arquivo_imagem is not None:
        img = Image.open(arquivo_imagem)
        img = ImageOps.fit(img, (150, 150), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return ""

# Carga inicial dos dados
df_jogadores_bruto = carregar_jogadores()
df_partidas = carregar_partidas()

# =========================================================
# 3. MOTOR ECONOMÉTRICO DO OVERALL (APLICADO GLOBALMENTE)
# =========================================================
df_processado = pd.DataFrame()

if not df_jogadores_bruto.empty:
    df_m = df_jogadores_bruto.copy()
    
    # 3.1 Impacto Coletivo (Pontos Pró e Contra extraídos do histórico real de partidas)
    pontos_pro_dict = {time: 0 for time in TODOS_TIMES}
    pontos_contra_dict = {time: 0 for time in TODOS_TIMES}
    jogos_dict = {time: 0 for time in TODOS_TIMES}
    
    if not df_partidas.empty:
        for _, partida in df_partidas.iterrows():
            ta, tb = partida["time_a"], partida["time_b"]
            sa, sb = int(partida["sets_a"]), int(partida["sets_b"])
            
            # Como não temos os pontos corridos das parciais mapeados por completo, 
            # estimamos o peso coletivo pelo volume de sets conquistados/cedidos
            pontos_pro_dict[ta] += sa
            pontos_pro_dict[tb] += sb
            pontos_contra_dict[ta] += sb
            pontos_contra_dict[tb] += sa
            jogos_dict[ta] += 1
            jogos_dict[tb] += 1

    # Mapeia os dados coletivos calculados de volta para o jogador
    df_m["pontos_pro"] = df_m["time"].map(pontos_pro_dict)
    df_m["pontos_contra"] = df_m["time"].map(pontos_contra_dict)
    df_m["jogos"] = df_m["time"].map(jogos_dict).replace(0, 1)
    
    # ETAPA 1 — AJUSTES BIOMÉTRICOS
    df_m["FA"] = (180 / df_m["altura_cm"]) ** 0.25
    df_m["FI"] = 1 + ((25 - df_m["idade"]) / 100)
    df_m["FI"] = df_m["FI"].clip(0.90, 1.10)
    
    # ETAPA 2 — PESO DOS FUNDAMENTOS
    df_m["AA"] = df_m["ataques"] * df_m["FA"] * df_m["FI"]
    df_m["BA"] = df_m["bloqueios"] * df_m["FA"] * 1.7
    df_m["SA"] = df_m["aces"] * 1.2
    
    # ETAPA 3 — IMPACTO COLETIVO (Saldo de sets médio por jogo)
    df_m["SC"] = (df_m["pontos_pro"] - df_m["pontos_contra"]) / df_m["jogos"]
    
    # ETAPA 4 — AJUSTE POR POSIÇÃO
    multiplicadores_posicao = {
        "central": 1.03, "ponteiro": 1.00, "oposto": 1.02, 
        "levantador": 1.04, "líbero": 1.05, "libero": 1.05
    }
    df_m["POS"] = df_m["posicao"].map(multiplicadores_posicao).fillna(1.00)
    
    # ETAPA 5 — NOTA DE IMPACTO BRUTA
    df_m["NIB"] = ((df_m["AA"] + df_m["BA"] + df_m["SA"]) * df_m["POS"]) + df_m["SC"]
    
    # ETAPA 6 — OVERALL (65 A 99 baseados na régua global dos 32 atletas)
    nib_min = df_m["NIB"].min()
    nib_max = df_m["NIB"].max()
    
    if nib_max != nib_min:
        df_m["OVR"] = 65 + 34 * ((df_m["NIB"] - nib_min) / (nib_max - nib_min))
    else:
        df_m["OVR"] = 75 # Nota padrão caso o banco esteja estático ou resetado
        
    df_m["OVR"] = df_m["OVR"].round(0).astype(int)
    df_processado = df_m.sort_values(by="OVR", ascending=False)

# =========================================================
# 4. INTERFACE INTERATIVA (ABAS DO STREAMLIT)
# =========================================================
aba_ranking, aba_elenco, aba_confronto, aba_historico, aba_admin = st.tabs([
    "📊 Classificação & Estatísticas", "🏃‍♂️ Elenco & Fichas",
    "⚔️ Registrar Partida", "📜 Histórico de Jogos", "🔒 Painel Admin"
])

# --- ABA 1: RANKINGS COM MODELO AVANÇADO ---
with aba_ranking:
    if not df_processado.empty:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.header("🏆 Classificação por Seleção")
            # Tabela simples calculando as vitórias indiretas baseadas no histórico
            pontos_equipes = {time: 0 for time in TODOS_TIMES}
            if not df_partidas.empty:
                for _, p in df_partidas.iterrows():
                    if int(p["sets_a"]) > int(p["sets_b"]): pontos_equipes[p["time_a"]] += 3
                    else: pontos_equipes[p["time_b"]] += 3
                    
            df_classif = pd.DataFrame(list(pontos_equipes.items()), columns=["Seleção", "Pontos Corridos"]).sort_values(by="Pontos Corridos", ascending=False)
            st.dataframe(df_classif, hide_index=True, use_container_width=True)
            
            # Card do grande MVP do campeonato
            mvp_geral = df_processado.iloc[0]
            st.markdown("---")
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #ffe600 0%, #ffb300 100%); padding: 18px; border-radius: 12px; text-align: center; box-shadow: 0 6px 12px rgba(0,0,0,0.15);">
                    <div style="color: #000; font-weight: 900; font-size: 12px; letter-spacing: 1.5px;">🥇 MELHOR JOGADOR (OVR)</div>
                    <div style="color: #000; font-size: 28px; font-weight: 900; margin: 4px 0;">{mvp_geral['apelido'] if pd.notna(mvp_geral['apelido']) else mvp_geral['nome']}</div>
                    <div style="color: #000; font-size: 15px; font-weight: bold;">OVERALL: <span style="font-size: 24px; font-weight: 900;">{mvp_geral['OVR']}</span></div>
                    <div style="color: #222; font-size: 12px; margin-top: 4px;">{mvp_geral['time']} • Posição: {mvp_geral['posicao'].upper()}</div>
                </div>
                """, unsafe_allow_html=True
            )
            
        with col2:
            st.header("🔥 Classificação Geral de Atletas (Scout Econométrico)")
            st.caption("O cálculo do Overall pondera a Altura (FA), Idade (FI), Posição (POS) e Saldo Coletivo (SC) sobre as ações reais.")
            
            # Exibe o tabelão com os dados reais processados
            df_exibicao = df_processado.copy()
            df_exibicao["Atleta"] = df_exibicao["apelido"].fillna(df_exibicao["nome"])
            
            st.dataframe(
                df_exibicao[["OVR", "Atleta", "time", "posicao", "ataques", "bloqueios", "aces"]],
                column_config={
                    "OVR": st.column_config.NumberColumn("🌟 OVR", format="%d"),
                    "Atleta": "Jogador", "time": "Seleção", "posicao": "Posição",
                    "ataques": "⚔ Ataques", "bloqueios": "🧱 Blocks", "aces": "🎯 Aces"
                },
                hide_index=True, use_container_width=True
            )
    else:
        st.info("Nenhum atleta processado no momento.")

# --- ABA 2: ELENCO & FICHAS ---
with aba_elenco:
    st.header("📖 Álbum de Figurinhas Oficial — Copa 2026")
    if not df_processado.empty:
        for time in TODOS_TIMES:
            atletas_do_time = df_processado[df_processado["time"].str.strip() == time.strip()]
            if not atletas_do_time.empty:
                st.markdown(f"### {time}")
                html_carrossel = '<div style="display: flex; gap: 15px; overflow-x: auto; padding: 10px 0;">'
                for _, atleta in atletas_do_time.iterrows():
                    link_fundo = LINKS_FUNDOS_LIMPOS.get(time, FOTO_PADRAO_URL)
                    img_src = atleta["foto_jogador"] if pd.notna(atleta["foto_jogador"]) and str(atleta["foto_jogador"]).strip() != "" else FOTO_PADRAO_URL
                    
                    nome_f = atleta["apelido"] if pd.notna(atleta["apelido"]) and str(atleta["apelido"]).strip() != "" else atleta["nome"].split()[0]
                    alt_txt = f"{int(atleta['altura_cm'])} CM"
                    
                    html_carrossel += (
                        f'<div style="flex: 0 0 auto; width: 190px; height: 280px; border-radius: 8px; position: relative; overflow: hidden; box-shadow: 0px 4px 10px rgba(0,0,0,0.4);">'
                        f'  <img src="{link_fundo}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 1;">'
                        f'  <div style="position: absolute; top: 6px; left: 6px; background: #ffffff; min-width: 32px; height: 32px; display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 10; border-radius: 4px; box-shadow: 1px 1px 4px rgba(0,0,0,0.3);">'
                        f'    <span style="color: #000; font-size: 14px; font-weight: 900; line-height: 1;">{atleta["OVR"]}</span>'
                        f'    <span style="color: #1b47ff; font-size: 7px; font-weight: 900;">OVR</span>'
                        f'  </div>'
                        f'  <div style="position: absolute; bottom: 0; left: 0; width: 100%; height: 70%; display: flex; align-items: flex-end; justify-content: center; z-index: 5; padding-bottom: 50px; box-sizing: border-box;">'
                        f'    <img src="{img_src}" style="width: auto; max-width: 95%; height: 100%; object-fit: contain;">'
                        f'  </div>'
                        f'  <div style="position: absolute; bottom: 0; left: 0; width: 100%; background: linear-gradient(0deg, rgba(0,0,0,1) 0%, rgba(0,0,0,0.7) 80%, rgba(0,0,0,0) 100%); padding: 10px 5px; text-align: center; box-sizing: border-box; z-index: 12;">'
                        f'    <div style="color: #fff; font-size: 14px; font-weight: 900; text-transform: uppercase;">{nome_f}</div>'
                        f'    <div style="color: #bbb; font-size: 10px;">{atleta["posicao"].upper()} | {alt_txt}</div>'
                        f'  </div>'
                        f'</div>'
                    )
                html_carrossel += '</div>'
                st.markdown(html_carrossel, unsafe_allow_html=True)
    else:
        st.info("Cadastre os jogadores no Painel Admin.")

# --- ABA 3: REGISTRO DE PARTIDA ---
with aba_confronto:
    st.header("⚔️ Registrar Partida Realizada")
    senha = st.text_input("🔒 Senha Master para liberar Súmula:", type="password", key="senha_súmula")
    
    if senha == "mikasa123":
        st.subheader("📝 Dados Coletivos da Mesa")
        fase = st.text_input("Fase do Jogo:", value="Fase de Grupos")
        
        c1, c2 = st.columns(2)
        with c1:
            time_a = st.selectbox("Time A:", options=TODOS_TIMES, key="ta_conf")
        with c2:
            time_b = st.selectbox("Time B:", options=[t for t in TODOS_TIMES if t != time_a], key="tb_conf")
            
        cc1, cc2, cc3 = st.columns(3)
        with cc1: sets_a = st.number_input(f"Sets de {time_a}:", min_value=0, max_value=3, value=2)
        with cc2: sets_b = st.number_input(f"Sets de {time_b}:", min_value=0, max_value=3, value=0)
        with cc3: parciais = st.text_input("Parciais (separadas por vírgula):", value="21-15, 21-17")
        
        st.markdown("---")
        if st.button("💾 Gravar Resultado da Partida", type="primary", use_container_width=True):
            if salvar_partida_banco(fase, time_a, time_b, sets_a, sets_b, parciais):
                st.success("Placar gravado no histórico!")
                st.rerun()
    else:
        st.warning("Insira a senha para liberar o registro de confrontos.")

# --- ABA 4: HISTÓRICO ---
with aba_historico:
    st.header("📜 Histórico de Partidas")
    if not df_partidas.empty:
        for _, p in df_partidas.sort_values(by="id", ascending=False).iterrows():
            st.markdown(
                f"""
                <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 5px solid #ff4b4b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <span style="color:#ff4b4b; font-size:10px; font-weight:bold; font-family:monospace;">{p.get('fase','Torneio')}</span>
                    <h4 style="margin: 2px 0; color:#111;">{p['time_a']} {p['sets_a']} x {p['sets_b']} {p['time_b']}</h4>
                    <small style="color:#666;">📊 Parciais: {p['placar_sets']}</small>
                </div>
                """, unsafe_allow_html=True
            )
    else:
        st.info("Nenhuma partida registrada.")

# --- ABA 5: PAINEL ADMIN (LANÇAR SCOUTS INDIVIDUAIS DOS 32) ---
with aba_admin:
    st.header("🔒 Gestão de Scouts e Atletas")
    senha_adm = st.text_input("Senha Admin:", type="password", key="senha_adm_global")
    
    if senha_adm == "mikasa123":
        st.subheader("📈 Lançar / Atualizar Pontos de Fundamento")
        st.caption("Use esta área para imputar os blocos, ataques e aces acumulados de cada um dos 32 atletas.")
        
        if not df_jogadores_bruto.empty:
            df_filtro = df_jogadores_bruto.copy()
            df_filtro["exibir"] = df_filtro["time"].str.split().str[0] + " - " + df_filtro["nome"]
            
            atleta_sel = st.selectbox("Selecione o Atleta:", options=df_filtro["id"].tolist(), format_func=lambda x: df_filtro[df_filtro["id"] == x]["exibir"].values[0])
            
            ca1, ca2, ca3 = st.columns(3)
            with ca1: n_ataques = st.number_input("Adicionar Ataques:", value=0, step=1)
            with ca2: n_bloqueios = st.number_input("Adicionar Bloqueios:", value=0, step=1)
            with ca3: n_aces = st.number_input("Adicionar Aces (Saques):", value=0, step=1)
            
            if st.button("➕ Atualizar Estatísticas do Atleta", type="primary"):
                if atualizar_scout_jogador(atleta_sel, n_ataques, n_bloqueios, n_aces):
                    st.success("Scout atualizado com sucesso no Supabase!")
                    st.rerun()
        else:
            st.info("Nenhum jogador encontrado no banco.")
