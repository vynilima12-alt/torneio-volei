import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import base64
from PIL import Image
import io
import os

# =========================================================
# CONFIGURAÇÃO DE PROXY (Para funcionar na rede do banco)
# =========================================================
# Adicione estas 3 linhas para o Python conseguir acessar o Google Sheets pelo proxy:
#os.environ["http_proxy"] = "http://webproxy.brb.com.br:8080"
#os.environ["https_proxy"] = "http://webproxy.brb.com.br:8080"
#os.environ["HTTP_PROXY"] = "http://webproxy.brb.com.br:8080"
#os.environ["HTTPS_PROXY"] = "http://webproxy.brb.com.br:8080"

# =========================================================
# 1. CONFIGURAÇÕES DA PÁGINA
# =========================================================
st.set_page_config(page_title="Torneio de Vôlei Online", layout="wide")
st.title("🏆 Gestão do Torneio de Vôlei")

# URL pública da sua planilha do Google
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/17CWheIF3UG2TIuUoAkHfNTSwuHJBElSPdf8PHRVZb8c"

# ... (todo o resto do seu código online com gsheets continua igualzinho abaixo)

# Ícone padrão (em formato Base64 ou texto plano) caso o usuário não tenha foto
FOTO_PADRAO_URL = "https://cdn-icons-png.flaticon.com/512/4333/4333609.png"

# =========================================================
# 2. FUNÇÕES CORE E CONEXÃO COM O GOOGLE SHEETS
# =========================================================
# Cria a conexão nativa do Streamlit com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados_online():
    """Lê os dados em tempo real da planilha do Google"""
    try:
        # ttl="0" garante que o Streamlit não guarde cache e busque sempre o dado mais recente
        return conn.read(spreadsheet=URL_PLANILHA, ttl="0 minutes")
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        return None

def salvar_dados_online(df_atualizado):
    """Envia o DataFrame atualizado de volta para o Google Sheets"""
    try:
        conn.update(spreadsheet=URL_PLANILHA, data=df_atualizado)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar os dados na nuvem: {e}")
        return False

def converter_imagem_para_base64(arquivo_imagem):
    """Redimensiona a imagem para ficar leve e a converte em string Base64"""
    if arquivo_imagem is not None:
        img = Image.open(arquivo_imagem)
        img = img.resize((150, 150)) # Mantém tamanho padrão de perfil bem leve
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    return ""

# Inicializa os dados no session_state puxando da nuvem na primeira execução
if 'df_jogadores' not in st.session_state:
    df_inicial = carregar_dados_online()

    if df_inicial is None:
        df_inicial = pd.DataFrame(columns=[
            "ID",
            "NOME",
            "TIME",
            "PONTOS",
            "FOTO TIME",
            "FOTO JOGADOR"
        ])

    st.session_state.df_jogadores = df_inicial

# =========================================================
# 3. INTERFACE INTERATIVA (ABAS)
# =========================================================
aba_ranking, aba_registrar, aba_admin = st.tabs([
    "📊 Rankings Geral", 
    "🎯 Registrar Pontos", 
    "🔒 Painel Admin"
])

# --- ABA 1: RANKINGS Geral ---
with aba_ranking:
    df = st.session_state.df_jogadores
    
    if df is not None and not df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("🏆 Classificação dos Times")
            # Agrupa os pontos por equipe
            ranking_times = df.groupby("TIME")["PONTOS"].sum().reset_index()
            ranking_times = ranking_times.sort_values(by="PONTOS", ascending=False)
            
            st.dataframe(
                ranking_times,
                column_config={"TIME": "Equipe", "PONTOS": "Pontos Conquistados"},
                hide_index=True,
                use_container_width=True
            )
            
        with col2:
            st.header("🔥 Artilharia (Jogadores)")
            ranking_jogadores = df.sort_values(by="PONTOS", ascending=False)
            
            # Exibe o ranking de jogadores renderizando a foto cadastrada na tabela
            st.dataframe(
                ranking_jogadores[["FOTO JOGADOR", "NOME", "TIME", "PONTOS"]],
                column_config={
                    "FOTO JOGADOR": st.column_config.ImageColumn("Perfil", width="small"),
                    "NOME": "Jogador", 
                    "TIME": "Time", 
                    "PONTOS": "Pontos Individuais"
                },
                hide_index=True,
                use_container_width=True
            )
    else:
        st.info("Nenhum dado encontrado na planilha online. Acesse o Painel Admin para cadastrar os jogadores.")

# --- ABA 2: REGISTRAR PONTOS (SELEÇÃO POR FOTO) ---
with aba_registrar:
    st.header("🎯 Registrar Pontos do Confronto")
    df_j = st.session_state.df_jogadores
    
    if df_j is not None and not df_j.empty:
        st.write("Clique no botão abaixo da foto para selecionar o atleta:")
        
        colunas = st.columns(4)
        for i, row in df_j.iterrows():
            with colunas[i % 4]:
                # Se a coluna de foto estiver vazia na planilha, usa a imagem padrão
                img_exibicao = row["FOTO JOGADOR"] if pd.notna(row["FOTO JOGADOR"]) and str(row["FOTO JOGADOR"]).strip() != "" else FOTO_PADRAO_URL
                
                st.image(img_exibicao, width=130)
                st.markdown(f"**{row['NOME']}**")
                
                # Se o time tiver símbolo/foto texto cadastrado, exibe ao lado
                simbolo_time = row["FOTO TIME"] if pd.notna(row["FOTO TIME"]) else "🏐"
                st.caption(f"{simbolo_time} {row['TIME']} | {row['PONTOS']} pts")
                
                if st.button("Selecionar", key=f"btn_{row['ID']}"):
                    st.session_state.jogador_atual = row["ID"]
                    st.session_state.pontos_temp = int(row["PONTOS"])
                    st.rerun()

        # Janela de Ajuste de pontos
        if 'jogador_atual' in st.session_state:
            id_sel = st.session_state.jogador_atual
            jogador_info = df_j[df_j["ID"] == id_sel].iloc[0]
            
            st.markdown("""<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-top: 20px;">""", unsafe_allow_html=True)
            st.subheader(f"Modificando pontuação de: {jogador_info['NOME']}")
            
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                if st.button("➖ Diminuir", use_container_width=True):
                    st.session_state.pontos_temp -= 1
                    st.rerun()
            with c2:
                st.markdown(f"<h1 style='text-align:center; color:#ff4b4b;'>{st.session_state.pontos_temp}</h1>", unsafe_allow_html=True)
            with c3:
                if st.button("➕ Aumentar", use_container_width=True):
                    st.session_state.pontos_temp += 1
                    st.rerun()
            
            if st.button("💾 Salvar Alteração na Nuvem (Google Sheets)", type="primary", use_container_width=True):
                # 1. Modifica na memória
                st.session_state.df_jogadores.loc[st.session_state.df_jogadores["ID"] == id_sel, "PONTOS"] = st.session_state.pontos_temp
                
                # 2. Envia para o Google Sheets online
                if salvar_dados_online(st.session_state.df_jogadores):
                    st.success(f"Placar atualizado no Google Sheets para {jogador_info['NOME']}!")
                    del st.session_state.jogador_atual
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("Adicione jogadores no Painel Admin antes de registrar pontos.")

# --- ABA 3: ADMINISTRAÇÃO (COM UPLOAD DE FOTOS DIRETO) ---
with aba_admin:
    st.header("🔒 Controle de Acesso")
    senha = st.text_input("Senha Master:", type="password")
    
    if senha == "volei123":
        st.success("Acesso administrativo liberado.")
        st.markdown("---")
        st.subheader("Adicionar Novo Atleta ao Torneio")
        
        nome_novo = st.text_input("Nome completo do jogador:")
        time_novo = st.text_input("Nome da equipe:")
        emoji_time = st.text_input("Emoji ou símbolo do time (Ex: 🔥, 🦈, ⚡):", value="🏐")
        
        # Upload direto da Imagem - Ativa a Câmera/Galeria nativa do celular
        arquivo_foto = st.file_uploader("Tire uma foto do atleta ou faça upload:", type=["png", "jpg", "jpeg"])
        
        if st.button("Confirmar Cadastro"):
            if nome_novo and time_novo:
                df_atual = st.session_state.df_jogadores
                
                # Gera o ID incremental automático
                novo_id = 1 if df_atual is None or df_atual.empty else int(df_atual["ID"].max() + 1)
                
                # Transforma o arquivo da foto em string Base64 se houver upload
                string_foto_jogador = converter_imagem_para_base64(arquivo_foto)
                
                nova_linha = pd.DataFrame([{
                    "ID": novo_id,
                    "NOME": nome_novo,
                    "TIME": time_novo,
                    "PONTOS": 0,
                    "FOTO TIME": emoji_time,
                    "FOTO JOGADOR": string_foto_jogador
                }])
                
                # Une os dados antigos com o novo cadastro
                if df_atual is None or df_atual.empty:
                    df_novo_total = nova_linha
                else:
                    df_novo_total = pd.concat([df_atual, nova_linha], ignore_index=True)
                
                # Salva a nova base na nuvem
                if salvar_dados_online(df_novo_total):
                    st.session_state.df_jogadores = df_novo_total
                    st.success(f"Atleta {nome_novo} cadastrado com sucesso com foto salva no Google Sheets!")
                    st.rerun()
            else:
                st.error("Por favor, preencha os campos obrigatórios de Nome e Time.")
    elif senha != "":
        st.error("Senha incorreta.")
