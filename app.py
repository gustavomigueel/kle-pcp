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
    fname = file.name.lower()
    # Carrega com engine adequado
    if fname.endswith('.xlsb'):
        xls = pd.ExcelFile(file, engine='pyxlsb')
    else:
        xls = pd.ExcelFile(file)
    sheet_names = xls.sheet_names
    # Detecta sheet de pedidos (nome contém 'pedido')
    sheet_ped = next((s for s in sheet_names if 'pedido' in s.lower()), sheet_names[0])
    # Detecta sheet de SKUs (colunas 'Prioridade' e 'Sabores')
    sku_sheet = None
    for s in sheet_names:
        df_tmp = xls.parse(s, nrows=0)
        cols = [c.strip().lower() for c in df_tmp.columns]
        if 'prioridade' in cols and 'sabores' in cols:
            sku_sheet = s
            break
    if not sku_sheet:
        sku_sheet = sheet_names[0]
    pedidos = xls.parse(sheet_ped)
    skus    = xls.parse(sku_sheet)
    # Padroniza nomes
    pedidos.columns = [c.strip() for c in pedidos.columns]
    skus.columns    = [c.strip() for c in skus.columns]
    # Timestamp a partir de DataEntrada + HoraEntrada
    date_cols = [c for c in pedidos.columns if 'data' in c.lower()]
    entry_date = next((c for c in date_cols if 'entrada' in c.lower()), date_cols[0] if date_cols else pedidos.columns[0])
    time_cols = [c for c in pedidos.columns if 'hora' in c.lower()]
    entry_time = next((c for c in time_cols if 'entrada' in c.lower()), time_cols[0] if time_cols else None)
    if entry_time:
        pedidos['Timestamp'] = pd.to_datetime(
            pedidos[entry_date].astype(str) + ' ' + pedidos[entry_time].astype(str),
            dayfirst=True, errors='coerce'
        )
    else:
        pedidos['Timestamp'] = pd.to_datetime(pedidos[entry_date], dayfirst=True, errors='coerce')
    # Mescla prioridade de SKUs
    if 'Item' in pedidos.columns and 'Sabores' in skus.columns and 'Prioridade' in skus.columns:
        pedidos = pd.merge(
            pedidos,
            skus[['Sabores','Prioridade']],
            left_on='Item', right_on='Sabores', how='left'
        )
        pedidos['Prioridade'] = pedidos['Prioridade'].fillna(9999).astype(int)
    else:
        pedidos['Prioridade'] = 9999
    return pedidos, skus

# Carrega dados
pedidos, skus = load_data(uploaded_file)
# Debug para conferir
st.sidebar.write('Abas no Excel:', pd.ExcelFile(uploaded_file, engine='pyxlsb' if uploaded_file.name.lower().endswith('.xlsb') else None).sheet_names)
st.sidebar.write('Colunas Pedidos:', pedidos.columns.tolist())
st.sidebar.write('Timestamp de entrada (min e max):', pedidos['Timestamp'].min(), pedidos['Timestamp'].max())

# Inicializa flags
for col in ['Gerado_RP1','Gerado_RP2','Gerado_RP3']:
    if col not in pedidos.columns:
        pedidos[col] = False

# Configuração de cortes
st.sidebar.header('Configuração de Cortes')
cut1 = datetime.time(16,30)
cut2 = datetime.time(10,30)
cut3 = datetime.time(15,30)
hoje = datetime.date.today()

# Função genérica
def generate_rp(flag_col, cutoff_dt):
    df = pedidos[(pedidos[flag_col] != True) & (pedidos['Timestamp'] <= cutoff_dt)].copy()
    pedidos.loc[df.index, flag_col] = True
    # Ordena por prioridade e por nome do item
    df = df.sort_values(['Prioridade','Item'])
    return df

# Geração de Roteiros
st.header('Geração de Roteiros')
col1, col2, col3 = st.columns(3)
with col1:
    if st.button('Gerar RP1'):
        dt1 = datetime.datetime.combine(hoje - datetime.timedelta(days=1), cut1)
        rp1 = generate_rp('Gerado_RP1', dt1)
        st.success(f'RP1 gerado: {rp1.shape[0]} pedidos')
        if not rp1.empty:
            st.table(rp1[['Item','Quantidade','Prioridade']])
with col2:
    if st.button('Gerar RP2'):
        dt2 = datetime.datetime.combine(hoje, cut2)
        rp2 = generate_rp('Gerado_RP2', dt2)
        st.success(f'RP2 gerado: {rp2.shape[0]} pedidos')
        if not rp2.empty:
            st.table(rp2[['Item','Quantidade','Prioridade']])
with col3:
    if st.button('Gerar RP3'):
        dt3 = datetime.datetime.combine(hoje, cut3)
        rp3 = generate_rp('Gerado_RP3', dt3)
        st.success(f'RP3 gerado: {rp3.shape[0]} pedidos')
        if not rp3.empty:
            st.table(rp3[['Item','Quantidade','Prioridade']])

# Exportação da base
st.header('Banco Atualizado')
output = pd.ExcelWriter('db_atualizado.xlsx', engine='xlsxwriter')
pedidos.to_excel(output, sheet_name='Pedidos_Gerais', index=False)
skus.to_excel(output, sheet_name='Base_SKUs', index=False)
output.save()
st.download_button('Baixar base atualizada', 'db_atualizado.xlsx')
