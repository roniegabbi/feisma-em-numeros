"""Lê o CSV exportado da planilha da pesquisa com expositores e grava data/df.pkl
com as 46 colunas canônicas (na ordem usada por analise.py).
Uso: python3 -I pipeline/carregar_pesquisa.py caminho.csv
"""
import csv, json, sys, re, unicodedata
import pandas as pd

def n(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)

canon = json.load(open('pipeline/colunas.json'))
rows = list(csv.reader(open(sys.argv[1], encoding='utf-8-sig')))
head = rows[0]
idx = {}
for c in canon:
    hits = [i for i, h in enumerate(head) if n(h) == n(c)]
    if not hits:  # tolera pequenas mudanças de texto: casa pelo início
        hits = [i for i, h in enumerate(head) if n(h)[:40] == n(c)[:40]]
    if not hits:
        if c.startswith('AI categories'):
            idx[c] = None; continue
        sys.exit(f'Coluna não encontrada no CSV: {c}')
    idx[c] = hits[0]
ts = next((i for i, h in enumerate(head) if n(h).startswith('carimbo')), None)
TESTE = {'xxx', 'yyy', 'teste', 'test', 'pmsmsmdei', 'secretariadedesenvolvimentoeconomicoeinovacao'}
data = []; desc = []
for r in rows[1:]:
    if not any(x.strip() for x in r):
        continue
    emp = n(r[idx['Empresa']]) if idx['Empresa'] < len(r) else ''
    # testes e pré-teste antes do início da aplicação (06/11)
    if emp in TESTE or (ts is not None and r[ts][:10] in ('03/11/2026', '04/11/2026', '05/11/2026')):
        desc.append(r[idx['Empresa']]); continue
    data.append([(r[idx[c]] if idx[c] is not None and idx[c] < len(r) else '') for c in canon])
df = pd.DataFrame(data, columns=canon)
# descarta linhas sem empresa ou sem consentimento
df = df[df['Empresa'].str.strip() != '']
df = df[df[canon[0]].str.contains('Sim', case=False, na=False)]
df.to_pickle('data/df.pkl')
print(f'{len(df)} respostas carregadas; descartadas como teste: {desc}')
