import streamlit as st
import pandas as pd
import datetime

# --- Autenticação simples ---
st.sidebar.header("🔒 Login")
username = st.sidebar.text_input("Usuário")
password = st.sidebar.text_input("Senha", type="password")
if username != "admin" or password != "admin123":
    st.sidebar.error("Usuário ou senha incorretos")
    st.stop()

# --- Título ---
st.title('Sistema PCP - Roteiros de Produção')

# --- Upload de arquivo Excel ---
uploaded_file = st.file_uploader('Carregar base Excel', type=['xlsx','xlsm','xlsb'])
if not uploaded_file:
    st.info('Por favor, carregue um arquivo Excel (.xlsx, .xlsm ou .xlsb)')
    st.stop()

# --- Função para ler Excel usando engine adequado ---
@st.cache_data
def load_data(file):
    import pandas as pd
    fname = file.name.lower()
    # Carrega o arquivo
    if fname.endswith('.xlsb'):
        xls = pd.ExcelFile(file, engine='pyxlsb')
    else:
        xls = pd.ExcelFile(file)
    # Mostra abas para debug (remova depois)
    st.sidebar.write("Abas no arquivo:", xls.sheet_names)
    # Tenta encontrar as duas abas-padrão
    sheet_ped = next((s for s in xls.sheet_names if s.lower().startswith('pedidos')), xls.sheet_names[0])
    sheet_sku = next((s for s in xls.sheet_names if s.lower().startswith('base_sku') or s.lower().startswith('sku')), 
                     xls.sheet_names[1] if len(xls.sheet_names)>1 else xls.sheet_names[0])
    # Faz a leitura
    pedidos = xls.parse(sheet_ped)
    skus    = xls.parse(sheet_sku)
    # Concatena data+hora (ajuste nomes se diferente)
    pedidos['Timestamp'] = pd.to_datetime(
        pedidos['DataEntrada'].astype(str) + ' ' + pedidos['HoraEntrada'].astype(str),
        dayfirst=True, errors='coerce'
    )
    return pedidos, skus


# --- Carrega dados ---
pedidos, skus = load_data(uploaded_file)

# --- Inicializa flags de geração ---
for col in ['Gerado_RP1','Gerado_RP2','Gerado_RP3']:
    if col not in pedidos.columns:
        pedidos[col] = False

# --- Configuração de horários de corte ---
st.sidebar.header('Configuração de Cortes')
cut_rp1 = datetime.time(16,30)
cut_rp2 = datetime.time(10,30)
cut_rp3 = datetime.time(15,30)

# Data de referência (hoje)
today = datetime.date.today()

# Função genérica para gerar roteiros
def generate_rp(pedidos_df, flag_col, cutoff_datetime):
    df = pedidos_df[(pedidos_df[flag_col] != True) & (pedidos_df['Timestamp'] <= cutoff_datetime)].copy()
    pedidos_df.loc[df.index, flag_col] = True
    return df

# --- Geração de roteiros ---
st.header('Geração de Roteiros')
if st.button('Gerar RP1'):
    dt1 = datetime.datetime.combine(today - datetime.timedelta(days=1), cut_rp1)
    rp1 = generate_rp(pedidos, 'Gerado_RP1', dt1)
    st.success(f'RP1 gerado: {len(rp1)} pedidos')
    st.dataframe(rp1)

if st.button('Gerar RP2'):
    dt2 = datetime.datetime.combine(today, cut_rp2)
    rp2 = generate_rp(pedidos, 'Gerado_RP2', dt2)
    st.success(f'RP2 gerado: {len(rp2)} pedidos')
    st.dataframe(rp2)

if st.button('Gerar RP3'):
    dt3 = datetime.datetime.combine(today, cut_rp3)
    rp3 = generate_rp(pedidos, 'Gerado_RP3', dt3)
    st.success(f'RP3 gerado: {len(rp3)} pedidos')
    st.dataframe(rp3)

# --- Download da base atualizada ---
st.header('Banco Atualizado')
# Gera arquivo em memória
buffer = pd.ExcelWriter('db_atualizado.xlsx', engine='xlsxwriter')
pedidos.to_excel(buffer, index=False, sheet_name='Pedidos_Gerais')
skus.to_excel(buffer, index=False, sheet_name='Base_SKUs')
buffer.save()
# Botão de download
tmp_download = st.download_button('Baixar base atualizada', 'db_atualizado.xlsx')
