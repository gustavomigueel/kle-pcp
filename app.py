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
    if fname.endswith('.xlsb'):
        xls = pd.ExcelFile(file, engine='pyxlsb')
    else:
        xls = pd.ExcelFile(file)
    # Detecta abas
    sheet_ped = next((s for s in xls.sheet_names if 'pedido' in s.lower()), xls.sheet_names[0])
    sheet_sku = next((s for s in xls.sheet_names if 'sku' in s.lower()), xls.sheet_names[0])
    pedidos = xls.parse(sheet_ped)
    skus    = xls.parse(sheet_sku)
    # Construir timestamp (data + hora)
    date_cols = [c for c in pedidos.columns if 'data' in c.lower()]
    time_cols = [c for c in pedidos.columns if 'hora' in c.lower()]
    if date_cols:
        date_col = date_cols[0]
    else:
        date_col = pedidos.columns[0]
    time_col = time_cols[0] if time_cols else None
    if time_col:
        pedidos['Timestamp'] = pd.to_datetime(
            pedidos[date_col].astype(str) + ' ' + pedidos[time_col].astype(str),
            dayfirst=True, errors='coerce'
        )
    else:
        pedidos['Timestamp'] = pd.to_datetime(pedidos[date_col], dayfirst=True, errors='coerce')
    return pedidos, skus

# --- Carrega dados e mescla prioridade ---
pedidos, skus = load_data(uploaded_file)
# Garante colunas padrão
skus.columns = [c.strip() for c in skus.columns]
pedidos.columns = [c.strip() for c in pedidos.columns]
# Mescla prioridade dos SKUs na tabela de pedidos
if 'Item' in pedidos.columns and 'Sabores' in skus.columns and 'Prioridade' in skus.columns:
    pedidos = pd.merge(
        pedidos,
        skus[['Sabores','Prioridade']],
        left_on='Item', right_on='Sabores', how='left'
    )
    pedidos['Prioridade'] = pedidos['Prioridade'].fillna(9999)
else:
    pedidos['Prioridade'] = 9999

# --- Inicializa flags de geração ---
for col in ['Gerado_RP1','Gerado_RP2','Gerado_RP3']:
    if col not in pedidos.columns:
        pedidos[col] = False

# --- Configuração de horários de corte ---
st.sidebar.header('Configuração de Cortes')
cut_rp1 = datetime.time(16,30)
cut_rp2 = datetime.time(10,30)
cut_rp3 = datetime.time(15,30)
# Data de referência
hoje = datetime.date.today()

# Função genérica para gerar e ordenar roteiros
def generate_rp(pedidos_df, flag_col, cutoff_datetime):
    df = pedidos_df[
        (pedidos_df[flag_col] != True) &
        (pedidos_df['Timestamp'] <= cutoff_datetime)
    ].copy()
    # Marca como gerado
    pedidos_df.loc[df.index, flag_col] = True
    # Ordena por prioridade e item (alfabético)
    if 'Prioridade' in df.columns and 'Item' in df.columns:
        df = df.sort_values(['Prioridade','Item'])
    return df

# --- Geração de roteiros ---
st.header('Geração de Roteiros')
if st.button('Gerar RP1'):
    cutoff1 = datetime.datetime.combine(hoje - datetime.timedelta(days=1), cut_rp1)
    rp1 = generate_rp(pedidos, 'Gerado_RP1', cutoff1)
    st.success(f'RP1 gerado: {len(rp1)} pedidos')
    st.table(rp1[['Item','Qtde','Prioridade']])

if st.button('Gerar RP2'):
    cutoff2 = datetime.datetime.combine(hoje, cut_rp2)
    rp2 = generate_rp(pedidos, 'Gerado_RP2', cutoff2)
    st.success(f'RP2 gerado: {len(rp2)} pedidos')
    st.table(rp2[['Item','Qtde','Prioridade']])

if st.button('Gerar RP3'):
    cutoff3 = datetime.datetime.combine(hoje, cut_rp3)
    rp3 = generate_rp(pedidos, 'Gerado_RP3', cutoff3)
    st.success(f'RP3 gerado: {len(rp3)} pedidos')
    st.table(rp3[['Item','Qtde','Prioridade']])

# --- Exportação da base atualizada ---
st.header('Banco Atualizado')
output = pd.ExcelWriter('db_atualizado.xlsx', engine='xlsxwriter')
pedidos.to_excel(output, sheet_name='Pedidos_Gerais', index=False)
skus.to_excel(output, sheet_name='Base_SKUs', index=False)
output.save()
st.download_button('Baixar base atualizada', 'db_atualizado.xlsx')
