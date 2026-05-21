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

def editar_jogador_banco(jogador_id, novo_nome, novo_time, novo_emoji):
    try:
        dados = {
            "nome": novo_nome,
            "time": novo_time,
            "foto_time": novo_emoji
        }
        supabase.table("jogadores").update(dados).eq("id", jogador_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar cadastro no banco: {e}")
        return False

def converter_imagem_para_base64(arquivo_imagem):
    if arquivo_imagem is not None:
        img = Image.open(arquivo_imagem)
        img = ImageOps.fit(img, (150, 150), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        # Retorna apenas a string de texto base64 pura
        return base64.b64encode(buffered.getvalue()).decode()
    return ""

def obter_imagem_atleta(dados_foto):
    """Tratamento seguro que converte Base64 em bytes legíveis para o st.image"""
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
            ranking_jogadores = df_jogadores.sort_values(by="pontos", ascending=False).copy()
            
            # Formata temporariamente o base64 com prefixo exigido pela tabela do Streamlit
            ranking_jogadores["foto_jogador"] = ranking_jogadores["foto_jogador"].apply(
                lambda x: f"data:image/png;base64,{str(x).split('base64,')[-1]}" if pd.notna(x) and str(x).strip() != "" and not str(x).startswith("http") else (x if pd.notna(x) else FOTO_PADRAO_URL)
            )
            
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
    
    c_t1, c_
