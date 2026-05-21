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
st.title("🏐 Copa do Mundo de Vôlei 2026 — Gestão de Confrontos")

FOTO_PADRAO_URL = "https://cdn-icons-png.flaticon.com/512/4333/4333609.png"

# Definição das Seleções Oficiais
GRUPO_A = ["🇧🇷 Brasil", "🇺🇸 EUA", "🇫🇷 França", "🇯🇵 Japão"]
GRUPO_B = ["🇩🇪 Alemanha", "🇦🇷 Argentina", "🇪🇸 Espanha", "🇵🇹 Portugal"]
TODOS_TIMES = GRUPO_A + GRUPO_B

LISTA_POSICOES = ["Ponteiro(a)", "Central", "Levantador(a)", "Oposto(a)", "Líbero"]

# Links diretos dos PNGs limpos do Canva hospedados no Imgur
LINKS_FUNDOS_LIMPOS = {
    "🇧🇷 Brasil": "https://i.imgur.com/twomOPg.png",
    "🇺🇸 EUA": "https://i.imgur.com/dq2MoW7.png",
    "🇫🇷 França": "https://i.imgur.com/BTszNIS.png",
    "🇯🇵 Japão": "https://i.imgur.com/XWFPcH0.png",
    "🇩🇪 Alemanha": "https://i.imgur.com/Go6KygO.png",
    "🇦🇷 Argentina": "https://i.imgur.com/VUf5oCx.png",
    "🇪🇸 Espanha": "https://i.imgur.com/nYwbcCS.png",
    "🇵🇹 Portugal": "https://i.imgur.com/96OtRQS.png",
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
            for col in ["apelido", "idade", "posicao", "altura", "frase"]:
                if col not in df.columns:
                    df[col] = None
            if "id" in df.columns:
                return df.sort_values(by="id").reset_index(drop=True)
            return df.sort_values(by="nome").reset_index(drop=True)
        return pd.DataFrame(columns=["id", "nome", "apelido", "time", "pontos", "foto_time", "foto_jogador", "idade", "posicao", "altura", "frase"])
    except Exception:
        return pd.DataFrame(columns=["id", "nome", "apelido", "time", "pontos", "foto_time", "foto_jogador", "idade", "posicao", "altura", "frase"])

def carregar_partidas_banco():
    try:
        response = supabase.table("partidas").select("*").execute()
        if response.data:
            return pd.DataFrame(response.data).sort_values(by="id", ascending=False).reset_index(drop=True)
        return pd.DataFrame(columns=["id", "time_a", "time_b", "sets_a", "sets_b", "placar_sets"])
    except Exception:
        return pd.DataFrame(columns=["id", "time_a", "time_b", "sets_a", "sets_b", "placar_sets"])
    
def atualizar_partida_banco(partida_id, sets_a, sets_b, placar_sets):
    try:
        dados = {"sets_a": sets_a, "sets_b": sets_b, "placar_sets": placar_sets}
        supabase.table("partidas").update(dados).eq("id", partida_id).execute()
        return True
    except Exception:
        return False

def deletar_partida_banco(partida_id):
    try:
        supabase.table("partidas").delete().eq("id", partida_id).execute()
        return True
    except Exception:
        return False

def salvar_partida_e_estatisticas(time_a, time_b, sets_a, sets_b, string_sets, pontos_partida_dict):
    try:
        dados_partida = {
            "time_a": time_a, "time_b": time_b,
            "sets_a": sets_a, "sets_b": sets_b, "placar_sets": string_sets
        }
        supabase.table("partidas").insert(dados_partida).execute()
        
        for jogador_id, pontos_ganhos in pontos_partida_dict.items():
            if pontos_ganhos > 0:
                res = supabase.table("jogadores").select("pontos").eq("id", jogador_id).execute()
                if res.data:
                    pontos_atuais = res.data[0]["pontos"]
                    novo_total = pontos_atuais + pontos_ganhos
                    supabase.table("jogadores").update({"pontos": novo_total}).eq("id", jogador_id).execute()
        return True
    except Exception:
        return False

def inserir_jogador_banco(nome, apelido, time, emoji, foto_base64, idade, posicao, altura, frase):
    try:
        dados = {
            "nome": nome, "apelido": apelido, "time": time, "foto_time": emoji, "foto_jogador": foto_base64, 
            "pontos": 0, "idade": idade, "posicao": posicao, "altura": altura, "frase": frase
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

def converter_imagem_para_base64(arquivo_imagem):
    if arquivo_imagem is not None:
        img = Image.open(arquivo_imagem)
        img = ImageOps.fit(img, (150, 150), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return ""

def obter_imagem_atleta(dados_foto):
    if pd.isna(dados_foto) or str(dados_foto).strip() == "":
        return FOTO_PADRAO_URL
    dados_foto_str = str(dados_foto).strip()
    if "base64," in dados_foto_str:
        dados_foto_str = dados_foto_str.split("base64,")[1]
    try:
        return base64.b64decode(dados_foto_str)
    except Exception:
        return FOTO_PADRAO_URL

df_jogadores = carregar_dados_banco()
df_partidas = carregar_partidas_banco()

# =========================================================
# 3. INTERFACE INTERATIVA (ABAS)
# =========================================================
aba_ranking, aba_elenco, aba_confronto, aba_historico, aba_admin = st.tabs([
    "📊 Classificação & Estatísticas", 
    "🏃‍♂️ Elenco & Fichas",
    "⚔️ Modo Confronto", 
    "📜 Histórico de Jogos",
    "🔒 Painel Admin"
])

# --- ABA 1: RANKINGS ---
with aba_ranking:
    if not df_jogadores.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.header("🏆 Pontuação por Seleção")
            ranking_times = df_jogadores.groupby("time")["pontos"].sum().reset_index()
            ranking_times = ranking_times.sort_values(by="pontos", ascending=False)
            st.dataframe(ranking_times, column_config={"time": "Seleção", "pontos": "Pontos Corridos"}, hide_index=True, use_container_width=True)
            
        with col2:
            st.header("🔥 Artilharia Individual (MVP)")
            ranking_jogadores = df_jogadores.sort_values(by="pontos", ascending=False).copy()
            ranking_jogadores["foto_jogador"] = ranking_jogadores["foto_jogador"].apply(
                lambda x: f"data:image/png;base64,{str(x).split('base64,')[-1]}" if pd.notna(x) and str(x).strip() != "" and not str(x).startswith("http") else (x if pd.notna(x) else FOTO_PADRAO_URL)
            )
            ranking_jogadores["exibir_nome"] = ranking_jogadores["apelido"].fillna(ranking_jogadores["nome"])
            st.dataframe(
                ranking_jogadores[["foto_jogador", "exibir_nome", "time", "pontos"]],
                column_config={
                    "foto_jogador": st.column_config.ImageColumn("Perfil", width="small"),
                    "exibir_nome": "Atleta", "time": "Seleção", "pontos": "Pontos Totais"
                },
                hide_index=True, use_container_width=True
            )
    else:
        st.info("Nenhum atleta cadastrado no torneio.")

# --- ABA 2: ELENCO & FICHAS (MODO ALBUM DE FIGURINHAS CANVA PREMIUM) ---
with aba_elenco:
    st.header("📖 Álbum de Figurinhas Premium — Copa 2026")
    
    if not df_jogadores.empty:
        for time in TODOS_TIMES:
            atletas_do_time = df_jogadores[df_jogadores["time"] == time]
            
            if not atletas_do_time.empty:
                st.markdown(f"### {time}")
                colunas_fig = st.columns(4)
                link_fundo_time = LINKS_FUNDOS_LIMPOS.get(time, FOTO_PADRAO_URL)
                
                for idx, (_, atleta) in enumerate(atletas_do_time.reset_index().iterrows()):
                    if idx < 4:
                        with colunas_fig[idx]:
                            foto_bytes = obter_imagem_atleta(atleta["foto_jogador"])
                            if isinstance(foto_bytes, bytes):
                                base64_foto = base64.b64encode(foto_bytes).decode()
                                img_src_atleta = f"data:image/png;base64,{base64_foto}"
                            else:
                                img_src_atleta = "https://cdn-icons-png.flaticon.com/512/5351/5351307.png"

                            apelido_atleta = atleta["apelido"] if pd.notna(atleta["apelido"]) and str(atleta["apelido"]).strip() != "" else atleta["nome"].split()[0]
                            posicao_txt = str(atleta["posicao"]).upper() if pd.notna(atleta["posicao"]) else "S"
                            letra_posicao = posicao_txt[0] if posicao_txt else "S"
                            if "LEVANTADOR" in posicao_txt: letra_posicao = "L"
                            elif "PONTEIRO" in posicao_txt: letra_posicao = "P"
                            elif "LÍBERO" in posicao_txt or "LIBERO" in posicao_txt: letra_posicao = "L"
                            elif "CENTRAL" in posicao_txt: letra_posicao = "C"
                            elif "OPOSTO" in posicao_txt: letra_posicao = "O"

                            altura_atleta = f"{int(atleta['altura'])} CM" if pd.notna(atleta['altura']) else "—"
                            idade_atleta = f"{int(atleta['idade'])}" if pd.notna(atleta['idade']) else "—"
                            frase_atleta = str(atleta["frase"]).upper() if pd.notna(atleta["frase"]) and str(atleta["frase"]).strip() != "" else "WE'RE GONNA TAKE THE POWER BACK"
                            
                            html_canva_premium = (
                                f'<div style="width: 100%; aspect-ratio: 3 / 4; border-radius: 4px; box-shadow: 0px 8px 20px rgba(0,0,0,0.3); position: relative; overflow: hidden; font-family: \'Arial\', sans-serif; margin-bottom: 20px;">'
                                f'  <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background-image: url(\"{link_fundo_time}\"); background-size: cover; background-position: center; z-index: 1;"></div>'
                                f'  <div style="position: absolute; top: 10px; left: 10px; background: linear-gradient(180deg, #ffffff 0%, #cccccc 100%); width: 35px; height: 45px; display: flex; align-items: center; justify-content: center; z-index: 2; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">'
                                f'    <span style="color: #1b47ff; font-size: 24px; font-weight: 900;">{letra_posicao}</span>'
                                f'  </div>'
                                f'  <div style="position: absolute; top: 0; left: 0; width: 100%; height: 80%; z-index: 3; display: flex; align-items: center; justify-content: center;">'
                                f'    <img src="{img_src_atleta}" style="max-width: 90%; max-height: 95%; object-fit: contain; object-position: center bottom;">'
                                f'  </div>'
                                f'  <div style="position: absolute; bottom: 0; left: 0; width: 100%; background: linear-gradient(180deg, #ffffff 0%, #e6e6e6 100%); padding: 10px 5px; text-align: center; z-index: 4; box-sizing: border-box; border-top: 1px solid #ccc;">'
                                f'    <div style="color: #1b47ff; font-size: 22px; font-weight: 900; text-transform: uppercase; letter-spacing: -0.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{apelido_atleta}</div>'
                                f'    <div style="color: #1b47ff; font-size: 11px; font-weight: bold; margin-top: 2px;">{idade_atleta} | {altura_atleta}</div>'
                                f'    <div style="color: #1b47ff; font-size: 10px; font-weight: 900; margin-top: 5px; font-style: italic; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 4px;">\"{frase_atleta}\"</div>'
                                f'  </div>'
                                f'</div>'
                            )
                            st.markdown(html_canva_premium, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("Nenhum atleta cadastrado para montar o álbum.")

# --- ABA 3: MODO CONFRONTO ---
with aba_confronto:
    st.header("⚔️ Gerenciar Partida em Tempo Real")
    c_t1, c_t2 = st.columns(2)
    with c_t1:
        time_a_sel = st.selectbox("Selecione o Time A:", options=TODOS_TIMES, index=0)
    with c_t2:
        opcoes_time_b = [t for t in TODOS_TIMES if t != time_a_sel]
        time_b_sel = st.selectbox("Selecione o Time B:", options=opcoes_time_b, index=0)

    jugadores_a = df_jogadores[df_jogadores["time"] == time_a_sel]
    jugadores_b = df_jogadores[df_jogadores["time"] == time_b_sel]

    if jugadores_a.empty or jugadores_b.empty:
        st.warning("Ambas as seleções precisam ter atletas cadastrados para iniciar a partida.")
    else:
        st.markdown("---")
        if "partida_ativa" not in st.session_state:
            st.session_state.pontos_jogo_locais = {row["id"]: 0 for _, row in pd.concat([jugadores_a, jugadores_b]).iterrows()}
            st.session_state.set_atual = 1
            st.session_state.historico_parciais = []
            st.session_state.sets_ganhos_a = 0
            st.session_state.sets_ganhos_b = 0
            st.session_state.placar_set_a = 0
            st.session_state.placar_set_b = 0
            st.session_state.partida_ativa = True

        st.markdown(
            f"""
            <div style="background-color: #1a1a1a; padding: 25px; border-radius: 15px; border: 3px solid #ff4b4b; text-align: center; margin-bottom: 25px; box-shadow: 0px 8px 16px rgba(0,0,0,0.3);">
                <div style="color: #ff4b4b; font-weight: bold; letter-spacing: 2px; font-size: 14px; margin-bottom: 10px; font-family: monospace;">SET {st.session_state.set_atual} EM ANDAMENTO</div>
                <div style="display: block; margin: 0 auto; text-align: center;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="width: 40%; text-align: right; color: white; font-size: 22px; font-weight: bold; padding-right: 15px;">{time_a_sel}</td>
                            <td style="width: 20%; text-align: center; color: #ff4b4b; font-size: 45px; font-weight: bold; font-family: monospace; background: #000; border-radius: 8px; padding: 5px 10px;">
                                {st.session_state.placar_set_a} <span style="color: #444; font-size: 25px;">:</span> {st.session_state.placar_set_b}
                            </td>
                            <td style="width: 40%; text-align: left; color: white; font-size: 22px; font-weight: bold; padding-left: 15px;">{time_b_sel}</td>
                        </tr>
                        <tr>
                            <td style="text-align: right; color: #00ff00; font-size: 16px; font-weight: bold; padding-right: 15px;">{st.session_state.sets_ganhos_a} Set(s)</td>
                            <td style="text-align: center; color: #666; font-size: 13px; padding-top: 5px;">Placar do Set</td>
                            <td style="text-align: left; color: #00ff00; font-size: 16px; font-weight: bold; padding-left: 15px;">{st.session_state.sets_ganhos_b} Set(s)</td>
                        </tr>
                    </table>
                </div>
                <div style="color: #888; font-size: 13px; margin-top: 15px;">Parciais anteriores: {', '.join(st.session_state.historico_parciais) if st.session_state.historico_parciais else 'Nenhuma'}</div>
            </div>
            """, 
            unsafe_allow_html=True
        )

        st.markdown("### 🎯 Atribuir Pontos aos Atletas em Quadra:")
        col_quadra_a, col_quadra_b = st.columns(2)
        with col_quadra_a:
            st.markdown(f"**Jogadores de {time_a_sel}**")
            for _, row in jugadores_a.iterrows():
                j_id = row["id"]
                c_img, c_txt, c_btn = st.columns([1, 2, 1])
                with c_img:
                    st.image(obter_imagem_atleta(row["foto_jogador"]), width=60)
                with c_txt:
                    nome_quadra = row["apelido"] if pd.notna(row["apelido"]) and str(row["apelido"]).strip() != "" else row["nome"]
                    pos_txt = f" ({row['posicao']})" if pd.notna(row['posicao']) else ""
                    st.markdown(f"**{nome_quadra}**{pos_txt}")
                    st.caption(f"Pontos no jogo: {st.session_state.pontos_jogo_locais.get(j_id, 0)}")
                with c_btn:
                    if st.button("➕ Ponto", key=f"ponto_a_{j_id}"):
                        st.session_state.pontos_jogo_locais[j_id] = st.session_state.pontos_jogo_locais.get(j_id, 0) + 1
                        st.session_state.placar_set_a += 1
                        st.rerun()

        with col_quadra_b:
            st.markdown(f"**Jogadores de {time_b_sel}**")
            for _, row in jugadores_b.iterrows():
                j_id = row["id"]
                c_img, c_txt, c_btn = st.columns([1, 2, 1])
                with c_img:
                    st.image(obter_imagem_atleta(row["foto_jogador"]), width=60)
                with c_txt:
                    nome_quadra = row["apelido"] if pd.notna(row["apelido"]) and str(row["apelido"]).strip() != "" else row["nome"]
                    pos_txt = f" ({row['posicao']})" if pd.notna(row['posicao']) else ""
                    st.markdown(f"**{nome_quadra}**{pos_txt}")
                    st.caption(f"Pontos no jogo: {st.session_state.pontos_jogo_locais.get(j_id, 0)}")
                with c_btn:
                    if st.button("➕ Ponto", key=f"ponto_b_{j_id}"):
                        st.session_state.pontos_jogo_locais[j_id] = st.session_state.pontos_jogo_locais.get(j_id, 0) + 1
                        st.session_state.placar_set_b += 1
                        st.rerun()

        st.markdown("---")
        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1:
            if st.button("🔔 Confirmar Fim do Set Atual", use_container_width=True):
                pa, pb = st.session_state.placar_set_a, st.session_state.placar_set_b
                st.session_state.historico_parciais.append(f"{pa}-{pb}")
                if pa > pb:
                    st.session_state.sets_ganhos_a += 1
                else:
                    st.session_state.sets_ganhos_b += 1
                st.session_state.placar_set_a = 0
                st.session_state.placar_set_b = 0
                st.session_state.set_atual += 1
                st.rerun()

        with col_ctrl2:
            if st.button("💾 Finalizar Partida e Salvar no Banco", use_container_width=True, type="primary"):
                string_final_sets = ", ".join(st.session_state.historico_parciais)
                if salvar_partida_e_estatisticas(
                    time_a_sel, time_b_sel, 
                    st.session_state.sets_ganhos_a, st.session_state.sets_ganhos_b, 
                    string_final_sets, st.session_state.pontos_jogo_locais
                ):
                    st.success("Partida salva com sucesso na nuvem!")
                    if "partida_ativa" in st.session_state:
                        del st.session_state.partida_ativa
                    st.rerun()

        if st.button("🔄 Resetar Placar Local (Cancelar Jogo)", type="secondary"):
            if "partida_ativa" in st.session_state:
                del st.session_state.partida_ativa
            st.rerun()

# --- ABA 4: HISTÓRICO DE JOGOS ---
with aba_historico:
    st.header("📜 Histórico de Partidas Realizadas")
    if not df_partidas.empty:
        for _, partida in df_partidas.iterrows():
            st.markdown(
                f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; margin-bottom: 15px; border-left: 6px solid #ff4b4b; box-shadow: 0px 4px 6px rgba(0,0,0,0.05);">
                    <h3 style='margin: 0; color: #1e1e1e; font-family: sans-serif; font-size: 20px;'>
                        {partida['time_a']} <span style='color: #ff4b4b;'>{partida['sets_a']}</span> 
                        <span style='color: #cccccc; font-size: 16px;'> x </span> 
                        <span style='color: #ff4b4b;'>{partida['sets_b']}</span> {partida['time_b']}
                    </h3>
                    <p style='color: #666666; font-size: 15px; margin: 8px 0 0 0; font-family: sans-serif;'>
                        📊 <b>Parciais:</b> {partida['placar_sets'] if partida['placar_sets'] else 'Sem parciais gravadas'}
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
    if senha == "volei123":
        st.session_state.admin_logado = True
        st.success("Acesso administrative liberado.")
        
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
                    st.error(f"A seleção do {time_novo} já atingiu o limite de 4 jogadores.")
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
                        st.success("Cadastro do atleta atualizado com sucesso!")
                        st.rerun()
                        
            confirma_atleta = st.checkbox(f"Confirmo a exclusão definitiva de {jogador_editar}.", key=f"del_atleta_check_{id_atleta}")
            if st.button("🗑️ Excluir Atleta do Torneio", type="secondary", key=f"btn_del_atleta_{id_atleta}"):
                if confirma_atleta and deletar_jogador_banco(id_atleta):
                    st.success("Jogador removido com sucesso.")
                    st.rerun()
                elif not confirma_atleta:
                    st.error("Marque a caixa de confirmação para deletar o atleta.")
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
                    if atualizar_partida_banco(id_partida_sel, n_sets_a, n_sets_b, n_parciais):
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
