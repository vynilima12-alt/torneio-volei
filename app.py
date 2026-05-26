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
st.title("🏐 Copa do Mundo de Vôlei 2026 — Estatísticas & Confrontos")

FOTO_PADRAO_URL = "https://cdn-icons-png.flaticon.com/512/4333/4333609.png"

GRUPO_A = ["🇧🇷 Brasil", "🇺🇸 EUA", "🇫🇷 França", "🇯🇵 Japão"]
GRUPO_B = ["🇩🇪 Alemanha", "🇦🇷 Argentina", "🇪🇸 Espanha", "🇵🇹 Portugal"]
TODOS_TIMES = GRUPO_A + GRUPO_B

LISTA_POSICOES = ["Ponteiro(a)", "Central", "Levantador(a)", "Oposto(a)", "Líbero"]

LISTA_JOGOS_TORNEIO = [
    f"Jogo {i}" for i in range(1, 17)
] + ["Semifinal 1", "Semifinal 2", "Terceiro Lugar", "Final"]

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
# 2. FUNÇÕES DE BANCO DE DADOS (PULL / PUSH)
# =========================================================
def carregar_dados_banco():
    try:
        response = supabase.table("jogadores").select("*").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            for col in ["ataques", "bloqueios", "aces", "apelido", "idade", "posicao", "altura", "frase"]:
                if col not in df.columns:
                    df[col] = 0 if col in ["ataques", "bloqueios", "aces"] else None
            
            df["ataques"] = df["ataques"].fillna(0).astype(int)
            df["bloqueios"] = df["bloqueios"].fillna(0).astype(int)
            df["aces"] = df["aces"].fillna(0).astype(int)
            df["altura"] = df["altura"].fillna(180).astype(int)
            df["idade"] = df["idade"].fillna(25).astype(int)
            df["posicao"] = df["posicao"].fillna("Ponteiro(a)").astype(str)
            df["pontos"] = df["ataques"] + df["bloqueios"] + df["aces"]
            
            if "id" in df.columns:
                return df.sort_values(by="id").reset_index(drop=True)
            return df.sort_values(by="nome").reset_index(drop=True)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def carregar_partidas_banco():
    try:
        response = supabase.table("partidas").select("*").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            return df.sort_values(by="id", ascending=False).reset_index(drop=True)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def zerar_rankings_banco():
    try:
        supabase.table("jogadores").update({"ataques": 0, "bloqueios": 0, "aces": 0, "pontos": 0}).neq("id", 0).execute()
        return True
    except Exception:
        return False

def salvar_partida_coletiva(fase, time_a, time_b, sets_a, sets_b, placar_sets):
    try:
        dados_partida = {
            "fase": fase, 
            "time_a": time_a, 
            "time_b": time_b,
            "sets_a": sets_a, 
            "sets_b": sets_b, 
            "placar_sets": placar_sets,
            "detalhes_pontos": "Placar oficial de mesa."
        }
        supabase.table("partidas").insert(dados_partida).execute()
        return True
    except Exception:
        return False

def atualizar_scout_total_jogador(jogador_id, novo_ataques, novo_bloqueios, novo_aces):
    try:
        supabase.table("jogadores").update({
            "ataques": novo_ataques,
            "bloqueios": novo_bloqueios,
            "aces": novo_aces
        }).eq("id", jogador_id).execute()
        return True
    except Exception:
        return False

def deletar_partida_banco(partida_id):
    try:
        supabase.table("partidas").delete().eq("id", partida_id).execute()
        return True
    except Exception:
        return False

def inserir_jogador_banco(nome, apelido, time, emoji, foto_base64, idade, posicao, altura, frase):
    try:
        foto_final = foto_base64
        if foto_base64 and not foto_base64.startswith("http") and not foto_base64.startswith("data:"):
            foto_final = f"data:image/png;base64,{foto_base64}"
        dados = {
            "nome": nome, "apelido": apelido, "time": time, "foto_time": emoji, "foto_jogador": foto_final, 
            "pontos": 0, "ataques": 0, "bloqueios": 0, "aces": 0, "idade": idade, "posicao": posicao, "altura": altura, "frase": frase
        }
        supabase.table("jogadores").insert(dados).execute()
        return True
    except Exception:
        return False

def deletar_jogador_banco(jogador_id):
    try:
        supabase.table("jogadores").delete().eq("id", jogador_id).execute()
        return True
    except Exception:
        return False

def editar_jogador_banco(jogador_id, novo_nome, novo_apelido, novo_time, novo_emoji, nova_idade, nova_posicao, nova_altura, nova_frase):
    try:
        dados = {
            "nome": novo_nome, "apelido": novo_apelido, "time": novo_time, "foto_time": novo_emoji,
            "idade": nova_idade, "posicao": nova_posicao, "altura": nova_altura, "frase": nova_frase
        }
        supabase.table("jogadores").update(dados).eq("id", jogador_id).execute()
        return True
    except Exception:
        return False

def obter_imagem_atleta(dados_foto):
    if pd.isna(dados_foto) or str(dados_foto).strip() == "":
        return FOTO_PADRAO_URL
    dados_foto_str = str(dados_foto).strip()
    if dados_foto_str.startswith("http"):
        return dados_foto_str
    if "base64," in dados_foto_str:
        dados_foto_str = dados_foto_str.split("base64,")[1]
    try:
        return base64.b64decode(dados_foto_str)
    except Exception:
        return FOTO_PADRAO_URL

def converter_imagem_para_base64(arquivo_imagem):
    if arquivo_imagem is not None:
        img = Image.open(arquivo_imagem)
        img = ImageOps.fit(img, (150, 150), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return ""

df_jogadores = carregar_dados_banco()
df_partidas = carregar_partidas_banco()

# =========================================================
# 3. MOTOR DO OVERALL (CALCULADO EM LOTE)
# =========================================================
if not df_jogadores.empty:
    pontos_pro_dict = {time: 0 for time in TODOS_TIMES}
    pontos_contra_dict = {time: 0 for time in TODOS_TIMES}
    jogos_dict = {time: 0 for time in TODOS_TIMES}
    vitorias_times = {time: 0 for time in TODOS_TIMES} # Nova contagem de vitórias realistas
    
    if not df_partidas.empty:
        for _, partida in df_partidas.iterrows():
            ta, tb = partida["time_a"], partida["time_b"]
            sa, sb = int(partida["sets_a"]), int(partida["sets_b"])
            
            pontos_pro_dict[ta] += sa
            pontos_pro_dict[tb] += sb
            pontos_contra_dict[ta] += sb
            pontos_contra_dict[tb] += sa
            jogos_dict[ta] += 1
            jogos_dict[tb] += 1
            
            # Computa 3 pontos por vitória de partida para a tabela de classificação
            if sa > sb:
                vitorias_times[ta] += 3
            elif sb > sa:
                vitorias_times[tb] += 3

    df_jogadores["pontos_pro"] = df_jogadores["time"].map(pontos_pro_dict)
    df_jogadores["pontos_contra"] = df_jogadores["time"].map(pontos_contra_dict)
    df_jogadores["jogos"] = df_jogadores["time"].map(jogos_dict).replace(0, 1)

    df_jogadores["FA"] = (180 / df_jogadores["altura"]) ** 0.25
    df_jogadores["FI"] = 1 + ((25 - df_jogadores["idade"]) / 100)
    df_jogadores["FI"] = df_jogadores["FI"].clip(0.90, 1.10)

    df_jogadores["AA"] = df_jogadores["ataques"] * df_jogadores["FA"] * df_jogadores["FI"]
    df_jogadores["BA"] = df_jogadores["bloqueios"] * df_jogadores["FA"] * 1.7
    df_jogadores["SA"] = df_jogadores["aces"] * 1.2

    df_jogadores["SC"] = (df_jogadores["pontos_pro"] - df_jogadores["pontos_contra"]) / df_jogadores["jogos"]

    multiplicadores_posicao = {
        "central": 1.03, "ponteiro": 1.00, "oposto": 1.02, 
        "levantador": 1.04, "líbero": 1.05, "libero": 1.05
    }
    pos_limpa = df_jogadores["posicao"].str.lower().str.replace("(a)", "", regex=False).str.strip()
    df_jogadores["POS"] = pos_limpa.map(multiplicadores_posicao).fillna(1.00)

    df_jogadores["NIB"] = ((df_jogadores["AA"] + df_jogadores["BA"] + df_jogadores["SA"]) * df_jogadores["POS"]) + df_jogadores["SC"]

    nib_min = df_jogadores["NIB"].min()
    nib_max = df_jogadores["NIB"].max()

    if nib_max != nib_min:
        df_jogadores["OVR"] = 65 + 34 * ((df_jogadores["NIB"] - nib_min) / (nib_max - nib_min))
    else:
        df_jogadores["OVR"] = 75
        
    df_jogadores["OVR"] = df_jogadores["OVR"].round(0).astype(int)

# =========================================================
# 4. INTERFACE INTERATIVA (ABAS)
# =========================================================
if "admin_logado" not in st.session_state:
    st.session_state.admin_logado = False

aba_ranking, aba_elenco, aba_confronto, aba_historico, aba_admin = st.tabs([
    "📊 Classificação & Estatísticas", 
    "🏃‍♂️ Elenco & Fichas",
    "⚔️ Registrar Partida (Mesa)", 
    "📜 Histórico de Jogos",
    "🔒 Painel Admin"
])

# --- ABA 1: RANKINGS CORRIGIDOS ---
with aba_ranking:
    if not df_jogadores.empty:
        col1, col2 = st.columns([2, 3])
        with col1:
            st.header("🏆 Classificação por Seleção")
            
            # CORREÇÃO: Cria a tabela de classificação baseada nas vitórias reais computadas pelo histórico de jogos
            df_classif_times = pd.DataFrame(list(vitorias_times.items()), columns=["Seleção", "Pontos"]).sort_values(by="Pontos", ascending=False)
            st.dataframe(df_classif_times, column_config={"Seleção": "Seleção", "Pontos": "Pontos de Tabela (Vitórias)"}, hide_index=True, use_container_width=True)
            
        with col2:
            st.header("🔥 Scout Geral de Atletas (Ranking por Overall)")
            ranking_jogadores = df_jogadores.sort_values(by="OVR", ascending=False).copy()
            ranking_jogadores["exibir_nome"] = ranking_jogadores["apelido"].fillna(ranking_jogadores["nome"])
            
            st.dataframe(
                ranking_jogadores[["OVR", "exibir_nome", "time", "posicao", "ataques", "bloqueios", "aces"]],
                column_config={
                    "OVR": st.column_config.NumberColumn("🌟 OVR", format="%d"),
                    "exibir_nome": "Atleta", 
                    "time": "Seleção", 
                    "posicao": "Posição",
                    "ataques": "⚔️ Ataques", 
                    "bloqueios": "🧱 Bloqueios", 
                    "aces": "🎯 Aces"
                },
                hide_index=True, use_container_width=True
            )
    else:
        st.info("Nenhum atleta cadastrado no torneio.")

# --- ABA 2: ELENCO & FICHAS ---
with aba_elenco:
    st.header("📖 Álbum de Figurinhas Premium — Copa 2026")
    
    st.markdown(
        """
        <style>
        .carrossel-container {
            display: flex;
            flex-wrap: nowrap;
            overflow-x: auto;
            gap: 15px;
            padding: 10px 5px 20px 5px;
            scroll-behavior: smooth;
            -webkit-overflow-scrolling: touch;
        }
        .carrossel-container::-webkit-scrollbar { height: 6px; }
        .carrossel-container::-webkit-scrollbar-thumb { background-color: #333; border-radius: 10px; }
        </style>
        """, 
        unsafe_allow_html=True
    )
    
    if not df_jogadores.empty:
        for time in TODOS_TIMES:
            atletas_do_time = df_jogadores[df_jogadores["time"].str.strip() == time.strip()]
            if not atletas_do_time.empty:
                st.markdown(f"### {time}")
                html_carrossel = '<div class="carrossel-container">'
                for idx, (_, atleta) in enumerate(atletas_do_time.sort_values(by="OVR", ascending=False).reset_index().iterrows()):
                    link_fundo_time = LINKS_FUNDOS_LIMPOS.get(time, FOTO_PADRAO_URL)
                    dados_foto = atleta["foto_jogador"]
                    img_src_atleta = str(dados_foto).strip() if pd.notna(dados_foto) and str(dados_foto).strip() != "" else FOTO_PADRAO_URL
                    apelido_atleta = atleta["apelido"] if pd.notna(atleta["apelido"]) and str(atleta["apelido"]).strip() != "" else atleta["nome"].split()[0]
                    
                    html_carrossel += (
                        f'<div style="flex: 0 0 auto; width: 200px; height: 300px; border-radius: 6px; position: relative; overflow: hidden; font-family: \'Arial\', sans-serif; box-shadow: 0px 6px 12px rgba(0,0,0,0.5);">'
                        f'  <img src="{link_fundo_time}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 1;">'
                        f'  <div style="position: absolute; top: 8px; left: 8px; background: #ffffff; min-width: 32px; height: 32px; display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 10; border-radius: 4px; box-shadow: 1px 1px 4px rgba(0,0,0,0.3);">'
                        f'    <span style="color: #000; font-size: 14px; font-weight: 900; line-height: 1;">{atleta["OVR"]}</span>'
                        f'    <span style="color: #1b47ff; font-size: 7px; font-weight: 900;">OVR</span>'
                        f'  </div>'
                        f'  <div style="position: absolute; bottom: 0; left: 0; width: 100%; height: 75%; display: flex; align-items: flex-end; justify-content: center; z-index: 5; padding-bottom: 60px; box-sizing: border-box;">'
                        f'    <img src="{img_src_atleta}" style="width: auto; max-width: 95%; height: 100%; object-fit: contain;">'
                        f'  </div>'
                        f'  <div style="position: absolute; bottom: 0; left: 0; width: 100%; background: linear-gradient(0deg, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.7) 75%, rgba(0,0,0,0) 100%); padding: 15px 5px 8px 5px; text-align: center; box-sizing: border-box; z-index: 12;">'
                        f'    <div style="color: #ffffff; font-size: 15px; font-weight: 900; text-transform: uppercase;">{apelido_atleta}</div>'
                        f'    <div style="color: #bbbbbb; font-size: 10px; font-weight: bold; margin-top: 2px;">{int(atleta["idade"])} ANOS | {int(atleta["altura"])} CM</div>'
                        f'  </div>'
                        f'</div>'
                    )
                html_carrossel += '</div>'
                st.markdown(html_carrossel, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

# --- ABA 3: REGISTRO DE CONFRONTO LEVE ---
with aba_confronto:
    st.header("⚔️ Registrar Súmula da Mesa (Finais & Grupos)")
    senha_confronto = st.text_input("🔒 Insira a Senha Master para liberar o registro:", type="password", key="senha_aba_confronto")
    
    if senha_confronto != "mikasa123":
        st.warning("🔒 Esta aba é restrita. Digite a senha master para liberar os campos de súmula.")
    else:
        st.success("🔓 Súmula de Mesa liberada!")
        st.markdown("---")
        
        fase_final_jogo = st.selectbox("🎯 Escolha a Rodada / Partida correspondente:", options=LISTA_JOGOS_TORNEIO)

        c_t1, c_t2 = st.columns(2)
        with c_t1:
            time_a_sel = st.selectbox("Selecione o Time A:", options=TODOS_TIMES, index=0, key="retro_ta")
        with c_t2:
            time_b_sel = st.selectbox("Selecione o Time B:", options=[t for t in TODOS_TIMES if t != time_a_sel], index=0, key="retro_tb")

        st.markdown("#### 📊 Placar Final de Sets e Parciais")
        c_p1, c_p2, c_p3 = st.columns([1, 1, 2])
        with c_p1:
            sets_a_final = st.number_input(f"Sets Ganhos por {time_a_sel}:", min_value=0, max_value=3, value=2, step=1)
        with c_p2:
            sets_b_final = st.number_input(f"Sets Ganhos por {time_b_sel}:", min_value=0, max_value=3, value=0, step=1)
        with c_p3:
            parciais_finais = st.text_input("Parciais registradas (separadas por vírgula):", value="21-15, 21-17")

        st.markdown("---")
        if st.button("💾 Computar e Gravar Partida Coletiva", type="primary", use_container_width=True):
            if salvar_partida_coletiva(fase_final_jogo, time_a_sel, time_b_sel, sets_a_final, sets_b_final, parciais_finais):
                st.success(f"Partida '{fase_final_jogo}' cadastrada com sucesso! Classificação atualizada.")
                st.rerun()
            else:
                st.error("Erro técnico ao salvar dados no Supabase. Cheque as conexões.")

# --- ABA 4: HISTÓRICO ---
with aba_historico:
    st.header("📜 Histórico de Partidas Realizadas")
    if not df_partidas.empty:
        for _, partida in df_partidas.iterrows():
            fase_card = partida['fase'] if 'fase' in partida and pd.notna(partida['fase']) else "Fase de Grupos"
            st.markdown(
                f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; margin-bottom: 15px; border-left: 6px solid #ff4b4b; box-shadow: 0px 4px 6px rgba(0,0,0,0.05);">
                    <div style="color: #ff4b4b; font-family: monospace; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">{fase_card}</div>
                    <h3 style='margin: 0; color: #1e1e1e; font-family: sans-serif; font-size: 20px;'>
                        {partida['time_a']} <span style='color: #ff4b4b;'>{partida['sets_a']}</span> 
                        <span style='color: #cccccc; font-size: 16px;'> x </span> 
                        <span style='color: #ff4b4b;'>{partida['sets_b']}</span> {partida['time_b']}
                    </h3>
                    <p style='color: #666666; font-size: 14px; margin: 8px 0 0 0; font-family: sans-serif;'>
                        📊 <b>Parciais oficiais da mesa:</b> {partida['placar_sets']}
                    </p>
                </div>
                """, unsafe_allow_html=True
            )
    else:
        st.info("Nenhum jogo registrado no histórico.")

# --- ABA 5: PAINEL ADMIN ---
with aba_admin:
    senha = st.text_input("Senha Master:", type="password")
    if senha == "mikasa123":
        st.session_state.admin_logado = True
        st.success("Acesso administrativo liberado!")

        # 1. LANÇADOR DE SCOUT ACUMULADO DO TORNEIO TODO
        st.markdown("---")
        st.subheader("📈 Atualizar Scout Geral Acumulado do Torneio")
        st.caption("Selecione o jogador e digite os valores totais consolidados do campeonato.")
        
        if not df_jogadores.empty:
            df_lista = df_jogadores.copy()
            df_lista["exibir_admin"] = df_lista["time"].str.split().str[0] + " - " + df_lista["nome"]
            
            jogador_selecionado = st.selectbox("Selecione o Atleta:", options=df_lista["id"].tolist(), format_func=lambda x: df_lista[df_lista["id"] == x]["exibir_admin"].values[0])
            dados_atuais = df_jogadores[df_jogadores["id"] ==  jogador_selecionado].iloc[0]
            
            c_sc1, c_sc2, c_sc3 = st.columns(3)
            with c_sc1:
                val_atq = st.number_input("Total Acumulado de Ataques:", min_value=0, max_value=500, value=int(dados_atuais["ataques"]))
            with c_sc2:
                val_blo = st.number_input("Total Acumulado de Bloqueios:", min_value=0, max_value=200, value=int(dados_atuais["bloqueios"]))
            with c_sc3:
                val_ace = st.number_input("Total Acumulado de Aces:", min_value=0, max_value=200, value=int(dados_atuais["aces"]))
                
            if st.button("💾 Gravar e Atualizar Scout do Torneio", type="primary"):
                if atualizar_scout_total_jogador(jogador_selecionado, val_atq, val_blo, val_ace):
                    st.success("Estatísticas acumuladas atualizadas com sucesso no Supabase!")
                    st.rerun()

        # 2. GERENCIAR E REMOVER PARTIDAS DO HISTÓRICO
        st.markdown("---")
        st.subheader("🎬 Gerenciar Partidas Salvas (Histórico)")
        if not df_partidas.empty:
            opcoes_partidas = [f"Jogo #{p['id']}: [{p['fase']}] {p['time_a']} vs {p['time_b']}" for _, p in df_partidas.iterrows()]
            partida_selecionada = st.selectbox("Selecione qual partida deseja gerenciar/corrigir:", options=opcoes_partidas)
            
            id_partida_sel = int(partida_selecionada.split("Jogo #")[1].split(":")[0])
            dados_partida = df_partidas[df_partidas["id"] == id_partida_sel].iloc[0]

            with st.form(f"form_edicao_partida_{id_partida_sel}"):
                st.write(f"Modificando resultado de: **{dados_partida['time_a']} vs {dados_partida['time_b']}**")
                c_p1, c_p2, c_p3 = st.columns([1, 1, 2])
                with c_p1:
                    n_sets_a = st.number_input(f"Sets {dados_partida['time_a']}:", min_value=0, max_value=3, value=int(dados_partida['sets_a']))
                with c_p2:
                    n_sets_b = st.number_input(f"Sets {dados_partida['time_b']}:", min_value=0, max_value=3, value=int(dados_partida['sets_b']))
                with c_p3:
                    n_parciais = st.text_input("Parciais dos Sets (Ex: 21-15, 21-17):", value=str(dados_partida['placar_sets']))

                botao_salvar_partida = st.form_submit_button("💾 Salvar Alterações na Partida", type="primary")
                if botao_salvar_partida:
                    dados = {"sets_a": n_sets_a, "sets_b": n_sets_b, "placar_sets": n_parciais}
                    supabase.table("partidas").update(dados).eq("id", id_partida_sel).execute()
                    st.success("Placar do histórico corrigido com sucesso!")
                    st.rerun()
            
            confirma_partida = st.checkbox("Confirmo a exclusão permanente desta partida do histórico.", key=f"check_del_partida_{id_partida_sel}")
            if st.button("🗑️ Excluir Partida Definitivamente", type="secondary", key=f"btn_del_partida_{id_partida_sel}"):
                if confirma_partida:
                    if deletar_partida_banco(id_partida_sel):
                        st.success("Partida deletada e histórico atualizado!")
                        st.rerun()
                else:
                    st.error("Marque a caixa de confirmação para deletar a partida.")
        else:
            st.info("Nenhuma partida registrada para edição.")
        
        # 3. ZERAR E RESETAR TORNEIO
        st.markdown("---")
        st.subheader("🚨 ZERAR E RESETAR TORNEIO")
        st.warning("Atenção: O botão abaixo vai zerar TODOS os fundamentos (Ataques, Bloqueios, Aces e Totais) dos atletas no banco de dados.")
        
        confirmou_reset = st.checkbox("Estou ciente de que isso vai limpar totalmente o ranking acumulado.")
        if st.button("🔄 Zerar Todos os Rankings", type="secondary"):
            if confirmou_reset:
                if zerar_rankings_banco():
                    st.success("Scout zerado! Todos os jogadores voltaram para 0 pontos.")
                    st.rerun()
                else:
                    st.error("Erro técnico ao tentar limpar os dados do Supabase.")
            else:
                st.error("Por favor, marque a caixa de confirmação antes de resetar.")        
        
        # 4. FORMULÁRIO COMPACTO DE CADASTRO
        st.markdown("---")
        st.subheader("➕ Cadastrar Jogador (Manual/Backup)")
        with st.form("form_cadastro_jogador", clear_on_submit=True):
            nome_novo = st.text_input("Nome completo:")
            apelido_novo = st.text_input("Apelido / Nome no Ranking:")
            time_novo = st.selectbox("Seleção Fixa:", options=TODOS_TIMES)
            
            c_cad1, c_cad2, c_cad3 = st.columns(3)
            with c_cad1: idade_nova = st.number_input("Idade:", min_value=12, max_value=60, value=22)
            with c_cad2: posicao_nova = st.selectbox("Gosta de jogar de:", options=LISTA_POSICOES)
            with c_cad3: altura_nova = st.number_input("Altura estimada (em cm):", min_value=120, max_value=230, value=185, step=1)
                
            frase_nova = st.text_area("Frase que te define:")
            arquivo_foto = st.file_uploader("Foto para o perfil:", type=["png", "jpg", "jpeg"])
            botao_cadastrar = st.form_submit_button("Confirmar Cadastro", type="primary")
            
            if botao_cadastrar and nome_novo:
                emoji_flag = time_novo.split()[0]
                string_foto = converter_imagem_para_base64(arquivo_foto)
                if inserir_jogador_banco(nome_novo, apelido_novo, time_novo, emoji_flag, string_foto, idade_nova, posicao_nova, altura_nova, frase_nova):
                    st.success(f"Atleta {nome_novo} gravado com sucesso!")
                    st.rerun()

        # 5. FORMULÁRIO DE EDIÇÃO DE ATLETAS
        st.markdown("---")
        st.subheader("🛠️ Editar Cadastro de Atleta")
        if not df_jogadores.empty:
            jogador_editar = st.selectbox("Selecione quem deseja editar:", options=df_jogadores["nome"].tolist(), key="sb_edit_adm")
            dados_atleta = df_jogadores[df_jogadores["nome"] == jogador_editar].iloc[0]
            id_atleta = dados_atleta["id"]

            with st.form(f"form_edicao_{id_atleta}"):
                col_ed1, col_ed2 = st.columns(2)
                with col_ed1: nome_editado = st.text_input("Editar Nome:", value=dados_atleta["nome"])
                with col_ed2: apelido_editado = st.text_input("Editar Apelido:", value=dados_atleta["apelido"] if pd.notna(dados_atleta["apelido"]) else "")
                time_editado = st.selectbox("Mudar Seleção:", options=TODOS_TIMES, index=TODOS_TIMES.index(dados_atleta["time"]))

                col_ed3, col_ed4, col_ed5 = st.columns(3)
                with col_ed3:
                    val_idade = int(dados_atleta["idade"]) if pd.notna(dados_atleta["idade"]) else 22
                    idade_editada = st.number_input("Editar Idade:", min_value=12, max_value=60, value=val_idade)
                with col_ed4:
                    val_pos = dados_atleta["posicao"] if pd.notna(dados_atleta["posicao"]) and dados_atleta["posicao"] in LISTA_POSICOES else LISTA_POSICOES[0]
                    posicao_editada = st.selectbox("Editar Gosta de jogar de:", options=LISTA_POSICOES, index=LISTA_POSICOES.index(val_pos))
                with col_ed5:
                    val_alt = int(dados_atleta["altura"]) if pd.notna(dados_atleta["altura"]) else 185
                    altura_editada = st.number_input("Editar Altura (cm):", min_value=120, max_value=230, value=val_alt, step=1)

                frase_editada = st.text_area("Editar Frase que te define:", value=dados_atleta["frase"] if pd.notna(dados_atleta["frase"]) else "")
                botao_salvar = st.form_submit_button("💾 Salvar Alterações Atleta", type="primary")
                
                if botao_salvar:
                    emoji_novo = time_editado.split()[0]
                    if editar_jogador_banco(id_atleta, nome_editado, apelido_editado, time_editado, emoji_novo, idade_editada, posicao_editada, altura_editada, frase_editada):
                        st.success("Cadastro do atleta atualizado!")
                        st.rerun()
                        
            confirma_atleta = st.checkbox(f"Confirmo a exclusão definitiva de {jogador_editar}.", key=f"del_atleta_check_{id_atleta}")
            if st.button("🗑️ Excluir Atleta do Torneio", type="secondary", key=f"btn_del_atleta_{id_atleta}"):
                if confirma_atleta and deletar_jogador_banco(id_atleta):
                    st.success("Jogador removido com sucesso.")
                    st.rerun()
                elif not confirma_atleta:
                    st.error("Marque a caixa de confirmação para deletar a atleta.")
        else:
            st.info("Nenhum atleta cadastrado para edição.")
    else:
        st.session_state.admin_logado = False
