import streamlit as st
import pandas as pd
import base64
from PIL import Image, ImageOps
import io
from supabase import create_client, Client

# =========================================================
# 1. CONFIGURAÇÕES DA PÁGINA
# =========================================================
st.set_page_config(page_title="Torneio de Vôlei Oficial", layout="wide")
st.title("🏆 Gestão do Torneio de Vôlei (Database Online)")

FOTO_PADRAO_URL = "https://cdn-icons-png.flaticon.com/512/4333/4333609.png"

# Puxa as credenciais diretamente dos Secrets salvos no Streamlit Cloud
SUPABASE_URL = st.secrets["connections"]["supabase"]["url"]
SUPABASE_KEY = st.secrets["connections"]["supabase"]["key"]

# Cria a conexão direta com o Banco de Dados
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================================
# 2. FUNÇÕES DE BANCO DE DADOS (PULL / PUSH)
# =========================================================
def carregar_dados_banco():
    """Busca a tabela de jogadores direto do banco de dados relacional"""
    try:
        response = supabase.table("jogadores").select("*").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Ordena por ID caso a coluna exista no banco
            if "id" in df.columns:
                return df.sort_values(by="id").reset_index(drop=True)
            return df.sort_values(by="nome").reset_index(drop=True)
        return pd.DataFrame(columns=["id", "nome", "time", "pontos", "foto_time", "foto_jogador"])
    except Exception as e:
        st.error(f"Erro ao conectar ao Banco de Dados: {e}")
        return pd.DataFrame(columns=["id", "nome", "time", "pontos", "foto_time", "foto_jogador"])

def atualizar_pontos_banco(jogador_id, novos_pontos):
    """Atualiza a pontuação de um jogador específico no banco"""
    try:
        supabase.table("jogadores").update({"pontos": novos_pontos}).eq("id", jogador_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar pontos no banco: {e}")
        return False

def inserir_jogador_banco(nome, time, emoji, foto_base64):
    """Cadastra um novo jogador no banco de dados"""
    try:
        dados = {
            "nome": nome,
            "time": time,
            "foto_time": emoji,
            "foto_jogador": foto_base64,
            "pontos": 0
        }
        supabase.table("jogadores").insert(dados).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao cadastrar no banco: {e}")
        return False

def deletar_jogador_banco(jogador_id):
    """Exclui permanentemente um jogador do banco de dados"""
    try:
        supabase.table("jogadores").delete().eq("id", jogador_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao remover jogador do banco: {e}")
        return False

def editar_jogador_banco(jogador_id, novo_nome, novo_time, novo_emoji):
    """Atualiza os dados cadastrais de um jogador existente"""
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
        # ImageOps.fit garante o corte 1:1 perfeito no centro sem deformar o rosto
        img = ImageOps.fit(img, (150, 150), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    return ""

# Carrega os dados direto da nuvem
df_jogadores = carregar_dados_banco()

# =========================================================
# 3. INTERFACE INTERATIVA (ABAS)
# =========================================================
aba_ranking, aba_registrar, aba_admin = st.tabs([
    "📊 Rankings Geral", 
    "🎯 Registrar Pontos", 
    "🔒 Painel Admin"
])

# --- ABA 1: RANKINGS ---
with aba_ranking:
    if not df_jogadores.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("🏆 Classificação dos Times")
            ranking_times = df_jogadores.groupby("time")["pontos"].sum().reset_index()
            ranking_times = ranking_times.sort_values(by="pontos", ascending=False)
            
            st.dataframe(
                ranking_times,
                column_config={"time": "Equipe", "pontos": "Points Conquistados"},
                hide_index=True,
                use_container_width=True
            )
            
        with col2:
            st.header("🔥 Artilharia (Jogadores)")
            ranking_jogadores = df_jogadores.sort_values(by="pontos", ascending=False)
            
            st.dataframe(
                ranking_jogadores[["foto_jogador", "nome", "time", "pontos"]],
                column_config={
                    "foto_jogador": st.column_config.ImageColumn("Perfil", width="small"),
                    "nome": "Jogador", "time": "Time", "pontos": "Pontos Individuais"
                },
                hide_index=True,
                use_container_width=True
            )
    else:
        st.info("👋 Nenhum jogador cadastrado na nuvem! Acesse o Painel Admin para iniciar o torneio.")

# --- ABA 2: REGISTRAR PONTOS ---
with aba_registrar:
    st.header("🎯 Registrar Pontos do Confronto")
    
    if not df_jogadores.empty:
        st.write("Selecione o atleta para computar os pontos:")
        
        colunas = st.columns(4)
        for i, row in df_jogadores.iterrows():
            with colunas[i % 4]:
                img_exibicao = row["foto_jogador"] if pd.notna(row["foto_jogador"]) and str(row["foto_jogador"]).strip() != "" else FOTO_PADRAO_URL
                
                st.image(img_exibicao, width=130)
                st.markdown(f"**{row['nome']}**")
                
                simbolo_time = row["foto_time"] if pd.notna(row["foto_time"]) else "🏐"
                st.caption(f"{simbolo_time} {row['time']} | {row['pontos']} pts")
                
                if st.button("Selecionar", key=f"btn_{row['id']}"):
                    st.session_state.id_jogador_sel = row["id"]
                    st.session_state.nome_jogador_sel = row["nome"]
                    st.session_state.pontos_temp = int(row["pontos"])

        if 'id_jogador_sel' in st.session_state:
            st.markdown("""<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-top: 20px;">""", unsafe_allow_html=True)
            st.subheader(f"Modificando placar de: {st.session_state.nome_jogador_sel}")
            
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                if st.button("➖ Diminuir", use_container_width=True):
                    st.session_state.pontos_temp -= 1
            with c2:
                st.markdown(f"<h1 style='text-align:center; color:#ff4b4b;'>{st.session_state.pontos_temp}</h1>", unsafe_allow_html=True)
            with c3:
                if st.button("➕ Aumentar", use_container_width=True):
                    st.session_state.pontos_temp += 1
            
            if st.button("💾 Confirmar e Salvar no Banco de Dados", type="primary", use_container_width=True):
                if atualizar_pontos_banco(st.session_state.id_jogador_sel, st.session_state.pontos_temp):
                    st.success(f"Placar de {st.session_state.nome_jogador_sel} updated com sucesso!")
                    del st.session_state.id_jogador_sel
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("Adicione jogadores no Painel Admin antes de registrar pontos.")

# --- ABA 3: ADMINISTRAÇÃO ---
with aba_admin:
    st.header("🔒 Controle de Acesso")
    senha = st.text_input("Senha Master:", type="password")
    
    if senha == "volei123":
        st.success("Acesso administrativo liberado.")
        st.markdown("---")
        
        st.subheader("📦 Backoffice (Exportar Dados)")
        if not df_jogadores.empty:
            csv_data = df_jogadores.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Cópia de Segurança do Torneio (CSV)",
                data=csv_data,
                file_name="backup_banco_torneio.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        st.markdown("---")
        st.subheader("Adicionar Novo Atleta ao Torneio")
        
        nome_novo = st.text_input("Nome completo do jogador:")
        time_novo = st.text_input("Nome da equipe:")
        emoji_time = st.text_input("Emoji ou símbolo do time (Ex: 🔥, 🦈, ⚡):", value="🏐")
        arquivo_foto = st.file_uploader("Tire uma foto do atleta ou faça upload:", type=["png", "jpg", "jpeg"])
        
        if st.button("Confirmar Cadastro"):
            if nome_novo and time_novo:
                string_foto_jogador = converter_imagem_para_base64(arquivo_foto)
                if inserir_jogador_banco(nome_novo, time_novo, emoji_time, string_foto_jogador):
                    st.success(f"Atleta {nome_novo} gravado com sucesso!")
                    st.rerun()
            else:
                st.error("Por favor, preencha os campos obrigatórios de Nome e Time.")

        # Gerenciamento agora está trancado dentro do bloco correto da senha master!
        st.markdown("---")
        st.subheader("🛠️ Gerenciar Atletas Cadastrados")

        if not df_jogadores.empty:
            jogador_selecionado = st.selectbox(
                "Selecione um atleta para editar ou remover:",
                options=df_jogadores["nome"].tolist()
            )

            dados_atleta = df_jogadores[df_jogadores["nome"] == jogador_selecionado].iloc[0]
            id_atleta = dados_atleta["id"]

            col_ed1, col_ed2, col_ed3 = st.columns(3)
            with col_ed1:
                nome_editado = st.text_input("Editar Nome:", value=dados_atleta["nome"], key=f"edit_nome_{id_atleta}")
            with col_ed2:
                time_edited = st.text_input("Editar Equipe:", value=dados_atleta["time"], key=f"edit_time_{id_atleta}")
            with col_ed3:
                emoji_editado = st.text_input("Editar Símbolo/Emoji:", value=dados_atleta["foto_time"], key=f"edit_emoji_{id_atleta}")

            col_botoes = st.columns([1, 1, 2])
            with col_botoes[0]:
                if st.button("💾 Salvar Alterações", type="primary", use_container_width=True, key=f"btn_salvar_{id_atleta}"):
                    if editar_jogador_banco(id_atleta, nome_editado, time_edited, emoji_editado):
                        st.success("Cadastro atualizado com sucesso!")
                        st.rerun()

            with col_botoes[1]:
                confirmar_exclusao = st.checkbox("⚠️ Confirmar exclusão", key=f"check_del_{id_atleta}")
                if st.button("🗑️ Remover Atleta", type="secondary", use_container_width=True, key=f"btn_del_{id_atleta}"):
                    if confirmar_exclusao:
                        if deletar_jogador_banco(id_atleta):
                            st.success(f"{jogador_selecionado} foi removido do torneio.")
                            st.rerun()
                    else:
                        st.error("Marque a caixa de confirmação para poder deletar.")
        else:
            st.info("Nenhum atleta cadastrado para gerenciamento.")
            
    elif senha != "":
        st.error("Senha incorreta.")
