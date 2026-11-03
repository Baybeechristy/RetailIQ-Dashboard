"""RetailIQ | Exploratory retail dashboard and raw data quality assessment.
Data source: Chen (2015), UCI Online Retail, DOI:10.24432/C5BW33.
"""
from __future__ import annotations
import io
import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='RetailIQ | Retail Intelligence', page_icon='🛍️', layout='wide')
st.markdown('''<style>
.block-container {padding-top: 2rem; max-width: 1380px;}
h1,h2,h3 {letter-spacing:-.025em;} div[data-testid="stMetric"] {background:#131f33; border:1px solid #30435d; border-radius:16px; padding:18px;}
</style>''', unsafe_allow_html=True)

EXPECTED = ['InvoiceNo','StockCode','Description','Quantity','InvoiceDate','UnitPrice','CustomerID','Country']
SOURCE = 'Chen, D. (2015). Online Retail. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33'

@st.cache_data(show_spinner='Loading the Excel workbook…')
def load_excel(data: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(data), dtype={'InvoiceNo':'string','StockCode':'string','Description':'string','CustomerID':'string','Country':'string'})

def profile(df: pd.DataFrame):
    n=len(df)
    miss=df.isna().sum()
    report={
        'rows':n, 'columns':len(df.columns), 'column_names':list(df.columns),
        'types':{x:str(df[x].dtype) for x in df.columns},
        'missing':{x:{'count':int(miss[x]),'pct':round(100*int(miss[x])/n,3) if n else 0} for x in df.columns},
        'exact_duplicate_rows':int(df.duplicated().sum()),
    }
    for key in ['InvoiceNo','StockCode','CustomerID','Country']:
        if key in df: report['distinct_'+key]=int(df[key].nunique(dropna=True))
    if 'InvoiceDate' in df:
        dt=pd.to_datetime(df['InvoiceDate'],errors='coerce')
        report.update(date_min=str(dt.min()),date_max=str(dt.max()),invalid_dates=int(dt.isna().sum()))
    if 'Quantity' in df:
        q=pd.to_numeric(df.Quantity,errors='coerce')
        report.update(negative_quantity=int((q<0).sum()),zero_quantity=int((q==0).sum()),quantity_non_numeric=int((q.isna() & df.Quantity.notna()).sum()))
    if 'UnitPrice' in df:
        p=pd.to_numeric(df.UnitPrice,errors='coerce')
        report.update(negative_unit_price=int((p<0).sum()),zero_unit_price=int((p==0).sum()),unit_price_non_numeric=int((p.isna() & df.UnitPrice.notna()).sum()))
    if 'InvoiceNo' in df:
        report['cancelled_invoice_rows']=int(df.InvoiceNo.str.upper().str.startswith('C',na=False).sum())
        report['distinct_cancelled_invoices']=int(df.loc[df.InvoiceNo.str.upper().str.startswith('C',na=False),'InvoiceNo'].nunique())
    if 'StockCode' in df:
        report['non_5_digit_stock_code_rows']=int((~df.StockCode.str.fullmatch(r'\d{5}',na=False)).sum())
    return report

def audit_table(report):
    issues=[]
    def put(name,count,severity,note):
        if count: issues.append({'Issue':name,'Affected rows':count,'Severity':severity,'Why review':note})
    for col, d in report['missing'].items():
        put('Missing '+col,d['count'],'High' if col in ('InvoiceDate','Quantity','UnitPrice','InvoiceNo') else 'Medium','Assess impact before excluding')
    put('Exact duplicate rows',report['exact_duplicate_rows'],'Medium','Repeated line items may be legitimate; inspect invoices')
    put('Cancellation-coded rows',report.get('cancelled_invoice_rows',0),'High','Keep separate from completed sales')
    put('Negative quantities',report.get('negative_quantity',0),'High','Often cancellations/returns')
    put('Zero quantities',report.get('zero_quantity',0),'Medium','Investigate non-sale lines')
    put('Negative prices',report.get('negative_unit_price',0),'High','Possibly accounting adjustments')
    put('Zero prices',report.get('zero_unit_price',0),'Medium','May represent freebies or special codes')
    put('Invalid dates',report.get('invalid_dates',0),'High','Cannot assign period')
    put('Non-5-digit stock codes',report.get('non_5_digit_stock_code_rows',0),'Medium','Special charges and administrative codes exist; review')
    return pd.DataFrame(issues,columns=['Issue','Affected rows','Severity','Why review'])

def dashboard_dataframe(df):
    """Explicit analytical view only: source df is never changed."""
    d=df.copy()
    d['Quantity']=pd.to_numeric(d['Quantity'],errors='coerce')
    d['UnitPrice']=pd.to_numeric(d['UnitPrice'],errors='coerce')
    d['InvoiceDate']=pd.to_datetime(d['InvoiceDate'],errors='coerce')
    d['is_cancelled']=d['InvoiceNo'].str.upper().str.startswith('C',na=False)
    d['revenue']=d['Quantity']*d['UnitPrice']
    # Only positive completed line items, transparent filter not 'cleaned' source.
    valid=(~d.is_cancelled)&(d.Quantity>0)&(d.UnitPrice>0)&d.InvoiceDate.notna()
    return d.loc[valid].copy(), int((~valid).sum())

st.title('RetailIQ')
st.caption('Retail sales performance & customer intelligence · UCI Online Retail (2010–2011)')
st.write('An auditable exploration of historic UK retail transactions, with an explicit distinction between raw records and analytical views.')
file=st.file_uploader('Upload the original Online Retail.xlsx',type=['xlsx'],help='The file is analysed in memory. No data is modified on disk.')
local=Path(__file__).with_name('Online Retail.xlsx')
if file is None and local.exists():
    st.info('Using local Online Retail.xlsx from the project folder.')
    data=local.read_bytes()
elif file is not None:
    data=file.getvalue()
else:
    st.info('Download the public UCI workbook and upload it to begin. https://archive.ics.uci.edu/dataset/352/online+retail')
    st.stop()
try:
    raw=load_excel(data)
except Exception as ex:
    st.error('The Excel workbook could not be read: '+str(ex));st.stop()

with st.sidebar:
    st.header('Workflow')
    page=st.radio('Stage',['1 · Raw data profile','2 · Dashboard (analytical view)'])
    st.caption('Original file is never overwritten. Dashboard uses explicitly documented inclusion rules.')

if page.startswith('1'):
    st.header('Raw data quality profile')
    r=profile(raw)
    a,b,c,d=st.columns(4)
    a.metric('Rows',f"{r['rows']:,}")
    b.metric('Columns',r['columns'])
    c.metric('Exact duplicates',f"{r['exact_duplicate_rows']:,}")
    d.metric('Cancellation-coded rows',f"{r.get('cancelled_invoice_rows',0):,}")
    st.write('**Columns and inferred types**')
    st.dataframe(pd.DataFrame([{'Column':x,'Type':r['types'][x],'Missing':r['missing'][x]['count'],'Missing %':r['missing'][x]['pct']} for x in r['column_names']]),hide_index=True,use_container_width=True)
    st.write('**Issues to investigate (no fixes applied)**')
    st.dataframe(audit_table(r),hide_index=True,use_container_width=True)
    st.write('**Profiling details**')
    st.json({k:v for k,v in r.items() if k not in ['missing','types','column_names']})
    st.download_button('Download raw profile JSON',json.dumps(r,indent=2).encode(),'retailiq_raw_profile.json','application/json')
    st.download_button('Download audit issues CSV',audit_table(r).to_csv(index=False).encode(),'retailiq_audit_issues.csv','text/csv')
    st.warning('No rows have been deleted, imputed, corrected or deduplicated. Review the issues before accepting any cleaning plan.')
else:
    st.header('Exploratory sales dashboard')
    st.caption('This is an exploratory analytical view, not a cleaned master dataset.')
    if not set(EXPECTED).issubset(raw.columns):
        st.error('Missing required fields: '+', '.join(sorted(set(EXPECTED)-set(raw.columns))));st.stop()
    st.info('Inclusion rule: non-cancellation invoice, quantity > 0, unit price > 0, and valid date. Missing customer IDs remain included in overall sales. No deduplication is applied. Revenue = Quantity × UnitPrice in GBP. Returns are excluded, so this is **gross completed-line sales**, not net revenue.')
    if not st.checkbox('I understand and want to apply these exploratory filters'):
        st.stop()
    df,excluded=dashboard_dataframe(raw)
    if df.empty: st.warning('No rows meet these rules.');st.stop()
    countries=['All']+sorted(df.Country.dropna().unique().tolist())
    selected=st.selectbox('Country',countries)
    if selected!='All':df=df.loc[df.Country==selected].copy()
    if df.empty:st.warning('No matching records.');st.stop()
    m1,m2,m3,m4=st.columns(4)
    m1.metric('Gross sales',f"£{df.revenue.sum():,.0f}")
    m2.metric('Completed invoices',f"{df.InvoiceNo.nunique():,}")
    m3.metric('Identified customers',f"{df.CustomerID.nunique():,}")
    m4.metric('Sales line items',f"{len(df):,}")
    monthly=df.assign(month=df.InvoiceDate.dt.to_period('M').astype(str)).groupby('month',as_index=False).revenue.sum()
    fig=px.line(monthly,x='month',y='revenue',markers=True,title='Monthly gross sales',labels={'month':'Month','revenue':'Sales (£)'})
    fig.update_layout(hovermode='x unified');st.plotly_chart(fig,use_container_width=True)
    st.caption('Takeaway: hover to compare monthly totals; the first and last months may be partial.')
    left,right=st.columns(2)
    with left:
        products=df.loc[df.Description.notna()].groupby('Description',as_index=False).revenue.sum().nlargest(10,'revenue').sort_values('revenue')
        fig=px.bar(products,x='revenue',y='Description',orientation='h',title='Top 10 products by gross sales',labels={'revenue':'Sales (£)','Description':''})
        fig.update_layout(yaxis={'automargin':True});st.plotly_chart(fig,use_container_width=True)
        st.caption('Takeaway: rank products by sales value, not unit volume.')
    with right:
        geo=df.groupby('Country',dropna=False,as_index=False).revenue.sum().nlargest(10,'revenue').sort_values('revenue')
        fig=px.bar(geo,x='revenue',y='Country',orientation='h',title='Top 10 customer countries by gross sales',labels={'revenue':'Sales (£)','Country':''})
        st.plotly_chart(fig,use_container_width=True)
        st.caption('Takeaway: compare contribution by country; high values may reflect wholesale buyers.')
    customer=df.loc[df.CustomerID.notna()].groupby('CustomerID',as_index=False).revenue.sum()
    if not customer.empty:
        fig=px.histogram(customer,x='revenue',nbins=50,title='Distribution of customer spending',labels={'revenue':'Customer gross spending (£)','count':'Customers'})
        st.plotly_chart(fig,use_container_width=True)
        st.caption('Takeaway: investigate whether a small minority of identified customers account for most spending.')
    st.divider()
    st.caption(f'Underlying raw dataset: {len(raw):,} rows. Exploratory filters removed {excluded:,} rows BEFORE any country selection. Missing customer IDs are not imputed. No claim of net sales, profit, or unique customer identity beyond provided IDs.')
    st.caption(SOURCE+' · CC BY 4.0')
