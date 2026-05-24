import streamlit as st
import pandas as pd
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

# LINKS DEFINITIVOS E SEGUROS DO POSTIMAGES (Fundo limpo do seu Canva)
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
            df["pontos"] = df["ataques"] + df["bloqueios"] + df["aces"]
            
            if "id" in df.columns:
                return df.sort_values(by="id").reset_index(drop=True)
            return df.sort_values(by="nome").reset_index(drop=True)
        return pd.DataFrame(columns=["id", "nome", "apelido", "time", "ataques", "bloqueios", "aces", "pontos", "foto_time", "foto_jogador", "idade", "posicao", "altura", "frase"])
    except Exception:
        return pd.DataFrame(columns=["id", "nome", "apelido", "time", "ataques", "bloqueios", "aces", "pontos", "foto_time", "foto_jogador", "idade", "posicao", "altura", "frase"])

def carregar_partidas_banco():
    try:
        response = supabase.table("partidas").select("*").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            if "fase" not in df.columns:
                df["fase"] = "Fase de Grupos"
            return df.sort_values(by="id", ascending=False).reset_index(drop=True)
        return pd.DataFrame(columns=["id", "time_a", "time_b", "sets_a", "sets_b", "placar_sets", "fase", "detalhes_pontos"])
    except Exception:
        return pd.DataFrame(columns=["id", "time_a", "time_b", "sets_a", "sets_b", "placar_sets", "fase", "detalhes_pontos"])

def zerar_rankings_banco():
    try:
        supabase.table("jogadores").update({"ataques": 0, "bloqueios": 0, "aces": 0, "pontos": 0}).neq("id", 0).execute()
        return True
    except Exception:
        return False

def salvar_partida_retroativa(fase, time_a, time_b, sets_a, sets_b, placar_sets, stats_jogadores):
    try:
        linhas_detalhe = []
        for j_id, stats in stats_jogadores.items():
            tot = stats["ataques"] + stats["bloqueios"] + stats["aces"]
            if tot > 0:
                res_j = supabase.table("jogadores").select("apelido, nome").eq("id", j_id).execute()
                if res_j.data:
                    nome_f = res_j.data[0]["apelido"] if res_j.data[0]["apelido"] else res_j.data[0]["nome"]
                    linhas_detalhe.append(f"{nome_f}: {tot} Pts (Atq: {stats['ataques']}, Bloq: {stats['bloqueios']}, Ace: {stats['aces']})")
        
        txt_detalhes = " | ".join(linhas_detalhe) if linhas_detalhe else "Sem pontuações individuais salvas."

        dados_partida = {
            "fase": fase, "time_a": time_a, "time_b": time_b,
            "sets_a": sets_a, "sets_b": sets_b, "placar_sets": placar_sets,
            "detalhes_pontos": txt_detalhes
        }
        supabase.table("partidas").insert(dados_partida).execute()

        for j_id, stats in stats_jogadores.items():
            if stats["ataques"] > 0 or stats["bloqueios"] > 0 or stats["aces"] > 0:
                # CORRIGIDO: Removido o campo "Skinner" que causava o erro técnico
                res_j = supabase.table("jogadores").select("ataques, bloqueios, aces").eq("id", j_id).execute()
                if res_j.data:
                    atq_atual = res_j.data[0]["ataques"] if res_j.data[0]["ataques"] else 0
                    blo_atual = res_j.data[0]["bloqueios"] if res_j.data[0]["bloqueios"] else 0
                    ace_atual = res_j.data[0]["aces"] if res_j.data[0]["aces"] else 0

                    supabase.table("jogadores").update({
                        "ataques": atq_atual + stats["ataques"],
                        "bloqueios": blo_atual + stats["bloqueios"],
                        "aces": ace_atual + stats["aces"]
                    }).eq("id", j_id).execute()
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
            "pontos": 0, "ataques": 0, "bloqueios": 0, "aces": 0, "idade": idade, "posicao",: posicao, "altura": altura, "frase": frase
        }
        supabase.table("jogadores").insert(dados).execute()
        return True
    except Exception:
        return False

def deletar_jogador_banco(jogador_id):
    try:
        supabase.table("jogadores").delete().eq("id",_jogador_id).execute()
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
# 3. INTERFACE INTERATIVA (ABAS)
# =========================================================
if "admin_logado" not in st.session_state:
    st.session_state.admin_logado = False

aba_ranking, aba_elenco, aba_confronto, aba_historico, aba_admin = st.tabs([
    "📊 Classificação & Estatísticas", 
    "🏃‍♂️ Elenco & Fichas",
    "⚔️ Registrar Partida (Finais/Grupos)", 
    "📜 Histórico de Jogos",
    "🔒 Painel Admin"
])

# --- ABA 1: RANKINGS ---
with aba_ranking:
    if not df_jogadores.empty:
        col1, col2 = st.columns([2, 3])
        with col1:
            st.header("🏆 Classificação por Seleção")
            ranking_times = df_jogadores.groupby("time")["pontos"].sum().reset_index()
            ranking_times = ranking_times.sort_values(by="pontos", ascending=False)
            st.dataframe(ranking_times, column_config={"time": "Seleção", "pontos": "Pontos Totais Conquistados"}, hide_index=True, use_container_width=True)
            
        with col2:
            st.header("🔥 Scout Geral de Atletas (Ranking Completo)")
            ranking_jogadores = df_jogadores.sort_values(by="pontos", ascending=False).copy()
            ranking_jogadores["exibir_nome"] = ranking_jogadores["apelido"].fillna(ranking_jogadores["nome"])
            
            st.dataframe(
                ranking_jogadores[["exibir_nome", "time", "ataques", "bloqueios", "aces", "pontos"]],
                column_config={
                    "exibir_nome": "Atleta", 
                    "time": "Seleção", 
                    "ataques": "⚔️ Ataques", 
                    "bloqueios": "🧱 Bloqueios", 
                    "aces": "🎯 Aces", 
                    "pontos": "📊 TOTAL"
                },
                hide_index=True, use_container_width=True
            )
    else:
        st.info("Nenhum atleta cadastrado no torneio.")

# --- ABA 2: ELENCO & FICHAS (MODO ÁLBUM CARROSSEL) ---
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
        .carrossel-container::-webkit-scrollbar {
            height: 6px;
        }
        .carrossel-container::-webkit-scrollbar-thumb {
            background-color: #333;
            border-radius: 10px;
        }
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
                for idx, (_, atleta) in enumerate(atletas_do_time.reset_index().iterrows()):
                    link_fundo_time = LINKS_FUNDOS_LIMPOS.get(time, FOTO_PADRAO_URL)
                    dados_foto = atleta["foto_jogador"]
                    img_src_atleta = str(dados_foto).strip() if pd.notna(dados_foto) and str(dados_foto).strip() != "" else FOTO_PADRAO_URL

                    apelido_atleta = atleta["apelido"] if pd.notna(atleta["apelido"]) and str(atleta["apelido"]).strip() != "" else atleta["nome"].split()[0]
                    posicao_txt = str(atleta["posicao"]).upper() if pd.notna(atleta["posicao"]) else "S"
                    
                    letra_posicao = "S"
                    if "LEVANTADOR" in posicao_txt: letra_posicao = "LEV"
                    elif "PONTEIRO" in posicao_txt: letra_posicao = "P"
                    elif "LÍBERO" in posicao_txt or "LIBERO" in posicao_txt: letra_posicao = "L"
                    elif "CENTRAL" in posicao_txt: letra_posicao = "C"
                    elif "OPOSTO" in posicao_txt: letra_posicao = "OPP"

                    altura_atleta = f"{int(atleta['altura'])} CM" if pd.notna(atleta['altura']) else "—"
                    idade_atleta = f"{int(atleta['idade'])}" if pd.notna(atleta['idade']) else "—"
                    frase_atleta = str(atleta["frase"]).upper() if pd.notna(atleta["frase"]) and str(atleta["frase"]).strip() != "" else "COPA DO MUNDO 2026"
                    
                    html_carrossel += (
                        f'<div style="flex: 0 0 auto; width: 200px; height: 300px; border-radius: 6px; position: relative; overflow: hidden; font-family: \'Arial\', sans-serif; box-shadow: 0px 6px 12px rgba(0,0,0,0.5);">'
                        f'  <img src="{link_fundo_time}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 1;">'
                        f'  <div style="position: absolute; top: 8px; left: 8px; background: linear-gradient(180deg, #ffffff 0%, #cccccc 100%); min-width: 28px; padding: 0 4px; height: 32px; display: flex; align-items: center; justify-content: center; box-shadow: 1px 1px 4px rgba(0,0,0,0.4); z-index: 10; border-radius: 2px;">'
                        f'    <span style="color: #1b47ff; font-size: 13px; font-weight: 900;">{letra_posicao}</span>'
                        f'  </div>'
                        f'  <div style="position: absolute; bottom: 0; left: 0; width: 100%; height: 75%; display: flex; align-items: flex-end; justify-content: center; z-index: 5; padding-bottom: 60px; box-sizing: border-box;">'
                        f'    <img src="{img_src_atleta}" style="width: auto; max-width: 95%; height: 100%; object-fit: contain;">'
                        f'  </div>'
                        f'  <div style="position: absolute; bottom: 0; left: 0; width: 100%; background: linear-gradient(0deg, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.7) 75%, rgba(0,0,0,0) 100%); padding: 15px 5px 8px 5px; text-align: center; box-sizing: border-box; z-index: 12;">'
                        f'    <div style="color: #ffffff; font-size: 15px; font-weight: 900; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.1; text-shadow: 1px 1px 2px #000;">{apelido_atleta}</div>'
                        f'    <div style="color: #bbbbbb; font-size: 10px; font-weight: bold; margin-top: 2px; text-shadow: 1px 1px 1px #000;">{idade_atleta} ANOS | {altura_atleta}</div>'
                        f'    <div style="color: #00ff00; font-size: 8px; font-weight: 800; margin-top: 4px; font-style: italic; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 4px; text-shadow: 1px 1px 1px #000;">\"{frase_atleta}\"</div>'
                        f'  </div>'
                        f'</div>'
                    )
                html_carrossel += '</div>'
                st.markdown(html_carrossel, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("Nenhum atleta cadastrado para montar o álbum.")

# --- ABA 3: REGISTRO DE CONFRONTO RETROATIVO TOTALMENTE DIGITÁVEL ---
with aba_confronto:
    st.header("⚔️ Registrar Partidas Realizadas (Scout de Finais & Grupos)")
    
    senha_confronto = st.text_input("🔒 Insira a Senha Master para liberar o registro:", type="password", key="senha_aba_confronto")
    
    if senha_confronto != "mikasa123":
        st.warning("🔒 Esta aba é restrita. Digite a senha master para liberar os campos de súmula.")
    else:
        st.success("🔓 Súmula liberada para registro!")
        st.markdown("---")
        st.subheader("📝 Configuração Geral da Partida")
        
        # Título do jogo livre e digitável
        fase_final_jogo = st.text_input("✍️ Nome da Fase / Título do Jogo:", value="Jogo 1", placeholder="Ex: Jogo 1, Semifinal, Terceiro Lugar, Final...")

        # Seleção de Equipes
        c_t1, c_t2 = st.columns(2)
        with c_t1:
            time_a_sel = st.selectbox("Selecione o Time A:", options=TODOS_TIMES, index=0, key="retro_ta")
        with c_t2:
            opcoes_time_b = [t for t in TODOS_TIMES if t != time_a_sel]
            time_b_sel = st.selectbox("Selecione o Time B:", options=opcoes_time_b, index=0, key="retro_tb")

        # Placar e Parciais Gerais do Jogo
        st.markdown("#### 📊 Placar Geral do Confronto")
        c_p1, c_p2, c_p3 = st.columns([1, 1, 2])
        with c_p1:
            sets_a_final = st.number_input(f"Sets Ganhos por {time_a_sel}:", min_value=0, max_value=3, value=2, step=1)
        with c_p2:
            sets_b_final = st.number_input(f"Sets Ganhos por {time_b_sel}:", min_value=0, max_value=3, value=0, step=1)
        with c_p3:
            parciais_finais = st.text_input("Parciais das parciais separadas por vírgula:", value="25-18, 25-21", placeholder="Ex: 25-18, 21-25, 15-10")

        jugadores_a = df_jogadores[df_jogadores["time"] == time_a_sel]
        jugadores_b = df_jogadores[df_jogadores["time"] == time_b_sel]

        if jugadores_a.empty or jugadores_b.empty:
            st.warning("Ambas as seleções precisam ter atletas cadastrados para registrar a súmula.")
        else:
            st.markdown("---")
            st.markdown("### 🎯 Scout de Fundamentos por Atleta (Insira o total acumulado)")
            
            stats_inseridas = {}

            # Time A
            st.markdown(f"#### 🏃‍♂️ Atletas de {time_a_sel}")
            for _, row in jugadores_a.iterrows():
                j_id = row["id"]
                nome_f = row["apelido"] if pd.notna(row["apelido"]) and str(row["apelido"]).strip() != "" else row["nome"]
                
                c_img, c_nome, c_atq, c_blo, c_ace = st.columns([0.6, 1.4, 1, 1, 1])
                with c_img:
                    st.image(obter_imagem_atleta(row["foto_jogador"]), width=45)
                with c_nome:
                    st.markdown(f"**{nome_f}**")
                with c_atq:
                    atq = st.number_input("Ataques:", min_value=0, max_value=60, value=0, key=f"atq_a_{j_id}", step=1)
                with c_blo:
                    blo = st.number_input("Bloqueios:", min_value=0, max_value=20, value=0, key=f"blo_a_{j_id}", step=1)
                with c_ace:
                    ace = st.number_input("Aces:", min_value=0, max_value=15, value=0, key=f"ace_a_{j_id}", step=1)
                
                stats_inseridas[j_id] = {"ataques": atq, "bloqueios": blo, "aces": ace}
                st.markdown("<div style='margin-top:-10px; border-bottom:1px dashed #333;'></div>", unsafe_allow_html=True)

            # Time B
            st.markdown(f"#### 🏃‍♂️ Atletas de {time_b_sel}")
            for _, row in jugadores_b.iterrows():
                j_id = row["id"]
                nome_f = row["apelido"] if pd.notna(row["apelido"]) and str(row["apelido"]).strip() != "" else row["nome"]
                
                c_img, c_nome, c_atq, c_blo, c_ace = st.columns([0.6, 1.4, 1, 1, 1])
                with c_img:
                    st.image(obter_imagem_atleta(row["foto_jogador"]), width=45)
                with c_nome:
                    st.markdown(f"**{nome_f}**")
                with c_atq:
                    atq = st.number_input("Ataques:", min_value=0, max_value=60, value=0, key=f"atq_b_{j_id}", step=1)
                with c_blo:
                    blo = st.number_input("Bloqueios:", min_value=0, max_value=20, value=0, key=f"blo_b_{j_id}", step=1)
                with c_ace:
                    ace = st.number_input("Aces:", min_value=0, max_value=15, value=0, key=f"ace_b_{j_id}", step=1)
                
                stats_inseridas[j_id] = {"ataques": atq, "bloqueios": blo, "aces": ace}
                st.markdown("<div style='margin-top:-10px; border-bottom:1px dashed #333;'></div>", unsafe_allow_html=True)

            st.markdown("---")
            if st.button("💾 Computar e Gravar Partida Definitivamente", type="primary", use_container_width=True):
                if salvar_partida_retroativa(fase_final_jogo, time_a_sel, time_b_sel, sets_a_final, sets_b_final, parciais_finais, stats_inseridas):
                    st.success(f"Partida da '{fase_final_jogo}' cadastrada com sucesso e estatísticas computadas!")
                    st.rerun()
                else:
                    st.error("Erro técnico ao salvar dados no Supabase. Cheque as conexões.")

# --- ABA 4: HISTÓRICO DE JOGOS ---
with aba_historico:
    st.header("📜 Histórico de Partidas Realizadas")
    if not df_partidas.empty:
        for _, partida in df_partidas.iterrows():
            detalhes = partida['detalhes_pontos'] if 'detalhes_pontos' in partida and pd.notna(partida['detalhes_pontos']) else "Sem dados de fundamentos individuais registrados."
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
                        📊 <b>Parciais:</b> {partida['placar_sets'] if partida['placar_sets'] else 'Sem parciais gravadas'}
                    </p>
                    <p style='color: #1b47ff; font-size: 12px; margin: 6px 0 0 0; font-family: sans-serif;'>
                        🎯 <b>Scout Detalhado:</b> <span style='color: #444444;'>{detalhes}</span>
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )
    else:
        st.info("Nenhum jogo registrado no histórico.")

# --- ABA 5: ADMINISTRAÇÃO ---
with aba_admin:
    senha = st.text_input("Senha Master:", type="password")
    if senha == "mikasa123":
        st.session_state.admin_logado = True
        st.success("Acesso administrative liberado. O 'Modo Confronto' agora está desbloqueado!")

        st.markdown("---")
        st.subheader("🚨 ZERAR E RESETAR TORNEIO")
        st.warning("Atenção: O botão abaixo vai zerar TODOS os fundamentos (Ataques, Bloqueios, Aces e Totais) dos atletas no banco de dados. Use apenas para novas temporadas!")
        
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
        
        # ==========================================
        # 1. FORMULÁRIO COMPACTO DE CADASTRO
        # ==========================================
        st.markdown("---")
        st.subheader("➕ Cadastrar Jogador (Manual/Backup)")
        with st.form("form_cadastro_jogador", clear_on_submit=True):
            nome_novo = st.text_input("Nome completo:")
            apelido_novo = st.text_input("Apelido / Nome no Ranking:")
            time_novo = st.selectbox("Seleção Fixa:", options=TODOS_TIMES)
            
            c_cad1, c_cad2, c_cad3 = st.columns(3)
            with c_cad1:
                idade_nova = st.number_input("Idade:", min_value=12, max_value=60, value=22)
            with c_cad2:
                posicao_nova = st.selectbox("Gosta de jogar de:", options=LISTA_POSICOES)
            with c_cad3:
                altura_nova = st.number_input("Altura estimada (em cm):", min_value=120, max_value=230, value=185, step=1)
                
            frase_nova = st.text_area("Frase que te define:")
            arquivo_foto = st.file_uploader("Foto para o perfil:", type=["png", "jpg", "jpeg"])
            botao_cadastrar = st.form_submit_button("Confirmar Cadastro", type="primary")
            
            if botao_cadastrar:
                qtd_atual = len(df_jogadores[df_jogadores["time"] == time_novo])
                if qtd_atual >= 4:
                    st.error(f"A seleção do {time_novo} ya atingiu o limite de 4 jogadores.")
                elif nome_novo:
                    emoji_flag = time_novo.split()[0]
                    string_foto = converter_imagem_para_base64(arquivo_foto)
                    if inserir_jogador_banco(nome_novo, apelido_novo, time_novo, emoji_flag, string_foto, idade_nova, posicao_nova, altura_nova, frase_nova):
                        st.success(f"Atleta {nome_novo} gravado com sucesso!")
                        st.rerun()
                else:
                    st.error("O nome é obrigatório.")

        # ==========================================
        # 2. FORMULÁRIO DE EDIÇÃO DE ATLETAS
        # ==========================================
        st.markdown("---")
        st.subheader("🛠️ Editar Cadastro de Atleta")
        if not df_jogadores.empty:
            jogador_editar = st.selectbox("Selecione quem deseja editar:", options=df_jogadores["nome"].tolist(), key="sb_edit_adm")
            dados_atleta = df_jogadores[df_jogadores["nome"] == jogador_editar].iloc[0]
            id_atleta = dados_atleta["id"]

            with st.form(f"form_edicao_{id_atleta}"):
                col_ed1, col_ed2 = st.columns(2)
                with col_ed1:
                    nome_editado = st.text_input("Editar Nome:", value=dados_atleta["nome"])
                with col_ed2:
                    apelido_editado = st.text_input("Editar Apelido:", value=dados_atleta["apelido"] if pd.notna(dados_atleta["apelido"]) else "")

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
                        st.success("Cadastro do atleta updated!")
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

        # ==========================================
        # 3. GERENCIAR E REMOVER PARTIDAS DO HISTÓRICO
        # ==========================================
        st.markdown("---")
        st.subheader("🎬 Gerenciar Partidas Salvas (Histórico)")
        if not df_partidas.empty:
            opcoes_partidas = [f"Jogo #{p['id']}: {p['time_a']} vs {p['time_b']}" for _, p in df_partidas.iterrows()]
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
                    n_parciais = st.text_input("Parciais dos Sets (Ex: 15-12, 13-15):", value=str(dados_partida['placar_sets']))

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
    else:
        st.session_state.admin_logado = False
