import streamlit as st
import pandas as pd
import base64
from PIL import Image, ImageOps
import io
from supabase import create_client, Client

# =========================================================
# 1. CONFIGURAÇÕES DA PÁGINA
# =========================================================
st.set_page_config(page_title="Copa do Mundo de Vôlei 2026", layout="wide")
st.title("🏐 Copa do Mundo de Vôlei 2026 — Gestão de Confrontos")

FOTO_PADRAO_URL = "https://cdn-icons-png.flaticon.com/512/4333/4333609.png"

# Definição dos Grupos e Times Oficiais
GRUPO_A = ["🇧🇷 Brasil", "🇺🇸 EUA", "🇫🇷 França", "🇯🇵 Japão"]
GRUPO_B = ["🇩🇪 Alemanha", "🇦🇷 Argentina", "🇪🇸 Espanha", "🇵🇹 Portugal"]
TODOS_TIMES = GRUPO_A + GRUPO_B

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
            if "id" in df.columns:
                return df.sort_values(by="id").reset_index(drop=True)
            return df.sort_values(by="nome").reset_index(drop=True)
        return pd.DataFrame(columns=["id", "nome", "time", "pontos", "foto_time", "foto_jogador"])
    except Exception:
        return pd.DataFrame(columns=["id", "nome", "time", "pontos", "foto_time", "foto_jogador"])

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
        dados = {
            "sets_a": sets_a,
            "sets_b": sets_b,
            "placar_sets": placar_sets
        }
        supabase.table("partidas").update(dados).eq("id", partida_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar partida: {e}")
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
    except Exception as e:
        st.error(f"Erro ao computar dados no banco: {e}")
        return False

def inserir_jogador_banco(nome, time, emoji, foto_base64):
    try:
        dados = {"nome": nome, "time": time, "foto_time": emoji, "foto_jogador": foto_base64, "pontos": 0}
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

def converter_imagem_para_base64(arquivo_imagem):
    if arquivo_imagem is not None:
        img = Image.open(arquivo_imagem)
        img = ImageOps.fit(img, (150, 150), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    return ""

df_jogadores = carregar_dados_banco()
df_partidas = carregar_partidas_banco()

# =========================================================
# 3. INTERFACE INTERATIVA (ABAS)
# =========================================================
aba_ranking, aba_confronto, aba_historico, aba_admin = st.tabs([
    "📊 Classificação & Estatísticas", 
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
            ranking_jogadores = df_jogadores.sort_values(by="pontos", ascending=False)
            st.dataframe(
                ranking_jogadores[["foto_jogador", "nome", "time", "pontos"]],
                column_config={
                    "foto_jogador": st.column_config.ImageColumn("Perfil", width="small"),
                    "nome": "Atleta", "time": "Seleção", "pontos": "Pontos Totais"
                },
                hide_index=True, use_container_width=True
            )
    else:
        st.info("Nenhum atleta cadastrado no torneio.")

# --- ABA 2: MODO CONFRONTO ---
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

        # --- TELÃO DO PLACAR ESTILIZADO ---
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
                    st.image(row["foto_jogador"] if pd.notna(row["foto_jogador"]) else FOTO_PADRAO_URL, width=60)
                with c_txt:
                    st.markdown(f"**{row['nome']}**")
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
                    st.image(row["foto_jogador"] if pd.notna(row["foto_jogador"]) else FOTO_PADRAO_URL, width=60)
                with c_txt:
                    st.markdown(f"**{row['nome']}**")
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

# --- ABA 3: HISTÓRICO DE JOGOS ---
with aba_historico:
    st.header("📜 Histórico de Partidas Realizadas")
    
    # Verifica de forma silenciosa se o admin está logado na sessão
    is_admin = st.session_state.get("admin_logado", False)
    
    if not df_partidas.empty:
        for _, partida in df_partidas.iterrows():
            p_id = partida['id']
            
            # Layout do card com alto contraste
            st.markdown(
                f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; margin-bottom: 5px; border-left: 6px solid #ff4b4b; box-shadow: 0px 4px 6px rgba(0,0,0,0.05);">
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
            
            # Se for admin, renderiza um expander discreto logo abaixo do card para edição
            if is_admin:
                with st.expander(f"🛠️ Editar resultado da partida #{p_id}"):
                    c_ed1, c_ed2, c_ed3 = st.columns([1, 1, 2])
                    with c_ed1:
                        novos_sets_a = st.number_input(f"Sets {partida['time_a']}:", min_value=0, max_value=3, value=int(partida['sets_a']), key=f"set_a_{p_id}")
                    with c_ed2:
                        novos_sets_b = st.number_input(f"Sets {partida['time_b']}:", min_value=0, max_value=3, value=int(partida['sets_b']), key=f"set_b_{p_id}")
                    with c_ed3:
                        novas_parciais = st.text_input("Parciais (Ex: 15-12, 13-15):", value=str(partida['placar_sets']), key=f"parciais_{p_id}")
                    
                    if st.button("💾 Atualizar Placar", key=f"btn_update_partida_{p_id}", type="primary"):
                        if atualizar_partida_banco(p_id, novos_sets_a, novos_sets_b, novas_parciais):
                            st.success("Partida corrigida com sucesso!")
                            st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("Nenhum jogo registrado no histórico.")

# --- ABA 4: ADMINISTRAÇÃO ---
with aba_admin:
    senha = st.text_input("Senha Master:", type="password")
    if senha == "volei123":
        st.session_state.admin_logado = True
        st.success("Acesso administrativo liberado.")
        
        st.markdown("---")
        st.subheader("Adicionar Novo Atleta ao Torneio")
        nome_novo = st.text_input("Nome completo do jogador:")
        time_novo = st.selectbox("Seleção do Jogador (Time Fixo):", options=TODOS_TIMES)
        arquivo_foto = st.file_uploader("Foto do atleta:", type=["png", "jpg", "jpeg"])

        if st.button("Confirmar Cadastro"):
            qtd_atual = len(df_jogadores[df_jogadores["time"] == time_novo])
            if qtd_atual >= 4:
                st.error(f"A seleção do {time_novo} já atingiu o limite máximo de 4 jogadores cadastrados.")
            elif nome_novo:
                emoji_flag = time_novo.split()[0]
                string_foto = converter_imagem_para_base64(arquivo_foto)
                if inserir_jogador_banco(nome_novo, time_novo, emoji_flag, string_foto):
                    st.success(f"{nome_novo} adicionado ao {time_novo}!")
                    st.rerun()
            else:
                st.error("Por favor, digite o nome do jogador.")

        st.markdown("---")
        st.subheader("🗑️ Remover Atleta do Torneio")
        if not df_jogadores.empty:
            jogador_del = st.selectbox("Selecione quem deseja remover:", options=df_jogadores["nome"].tolist())
            id_del = df_jogadores[df_jogadores["nome"] == jogador_del].iloc[0]["id"]
            confirma = st.checkbox("Confirmo a exclusão permanente deste jogador.")
            if st.button("Deletar Jogador", type="primary"):
                if confirma and deletar_jogador_banco(id_del):
                    st.success("Jogador removido do banco.")
                    st.rerun()
