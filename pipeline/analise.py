import pandas as pd, json, re, unicodedata
df = pd.read_pickle('data/df.pkl')
df = df.apply(lambda s: s.str.strip())
C = list(df.columns)

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z]', '', s)

df['_k'] = df['Empresa'].map(norm)
n_resp = len(df)
d = df.drop_duplicates('_k', keep='first').reset_index(drop=True)
N = len(d)
out = {'n_respostas': n_resp, 'n_empresas': N}

def vc(col, order=None):
    s = d[col].value_counts()
    if order:
        return [[k, int(s.get(k, 0))] for k in order]
    return [[k, int(v)] for k, v in s.items()]

col = lambda i: C[i]
out['setor'] = vc(col(5))
out['porte'] = vc(col(6), ['MEI', 'Microempresa', 'Empresa de pequeno porte', 'Média empresa', 'Grande empresa'])
out['edicoes'] = vc(col(9), ['Primeira participação', '2 a 3 edições', '4 a 5 edições', 'Mais de 5 edições'])

# origem municipio
def origem(m):
    m = norm(m)
    if 'santamaria' in m: return 'Santa Maria'
    if any(x in m for x in ['santacatarina', 'minas', 'blumenau', 'guaruja', 'sobril']): return 'Outros estados'
    if any(x in m for x in ['sobradinho']): return 'Centro-Serra (Sobradinho)'
    return 'Outras regiões do RS'
d['_orig'] = d[col(4)].map(origem)
out['origem_municipio'] = vc('_orig', ['Santa Maria', 'Centro-Serra (Sobradinho)', 'Outras regiões do RS', 'Outros estados'])
out['municipios_raw'] = d[col(4)].tolist()

# pessoas
d['_pes'] = pd.to_numeric(d[col(7)], errors='coerce')
out['pessoas_total'] = int(d['_pes'].sum()); out['pessoas_med'] = float(d['_pes'].median())

# motivos (multi)
mot = {}
for v in d[col(11)]:
    for m in [x.strip() for x in v.split(',') if x.strip()]:
        mot[m] = mot.get(m, 0) + 1
out['motivos'] = sorted(mot.items(), key=lambda x: -x[1])

# ratings
rat_cols = {
 'Avaliação geral da feira': 12,
 'Localização e acesso': 13, 'Estrutura do pavilhão/estande': 14, 'Volume de público': 15,
 'Qualidade do público': 16, 'Datas e horário': 17, 'Programação paralela': 18,
 'Networking entre expositores': 33,
 'Clareza das informações': 34, 'Inscrição e contratação': 35, 'Custo x retorno do espaço': 36,
 'Atendimento da organização': 37, 'Montagem e desmontagem': 38, 'Divulgação da feira': 39}
rat = {}
for k, i in rat_cols.items():
    s = pd.to_numeric(d[C[i]], errors='coerce').dropna().astype(int)
    rat[k] = {'media': round(float(s.mean()), 2), 'dist': [int((s == v).sum()) for v in range(1, 6)], 'n': int(len(s))}
out['ratings'] = rat

out['perfil_publico'] = vc(col(19), ['Sim', 'Em parte', 'Não'])
out['comparacao'] = vc(col(20), ['Melhor', 'Igual', 'Pior', 'Não participo de outras feiras'])
out['retorno_prox'] = vc(col(21), ['Sim', 'Talvez', 'Não'])

inv_o = ['Até R$ 5 mil', 'R$ 5 a 15 mil', 'R$ 15 a 30 mil', 'R$ 30 a 50 mil', 'Acima de R$ 50 mil']
inv_mid = {'Até R$ 5 mil': (0, 2500, 5000), 'R$ 5 a 15 mil': (5000, 10000, 15000), 'R$ 15 a 30 mil': (15000, 22500, 30000),
           'R$ 30 a 50 mil': (30000, 40000, 50000), 'Acima de R$ 50 mil': (50000, 60000, 80000)}
ven_o = ['Não houve vendas', 'Até R$ 10 mil', 'R$ 10 a 50 mil', 'R$ 50 a 100 mil', 'R$ 100 a 500 mil']
ven_mid = {'Não houve vendas': (0, 0, 0), 'Até R$ 10 mil': (0, 5000, 10000), 'R$ 10 a 50 mil': (10000, 30000, 50000),
           'R$ 50 a 100 mil': (50000, 75000, 100000), 'R$ 100 a 500 mil': (100000, 300000, 500000)}
pip_o = ['Nenhum', 'Até R$ 10 mil', 'R$ 10 a 50 mil', 'R$ 50 a 100 mil', 'R$ 100 a 500 mil', 'Acima de R$ 500 mil']
pip_mid = dict(ven_mid); pip_mid['Nenhum'] = (0, 0, 0); pip_mid['Acima de R$ 500 mil'] = (500000, 600000, 750000)
out['investimento'] = vc(col(23), inv_o)
out['vendas'] = vc(col(24), ven_o)
out['pipeline'] = vc(col(25), pip_o)
out['cobriu'] = vc(col(26), ['Já cobriu', 'Deve cobrir com os negócios encaminhados', 'Não deve cobrir'])

AVISOS = []
def _g(mp, v):
    if v not in mp:
        AVISOS.append(f'faixa desconhecida: {v!r}'); return (0, 0, 0)
    return mp[v]
def tot(colname, mp):
    lo = sum(_g(mp, v)[0] for v in d[colname]); mi = sum(_g(mp, v)[1] for v in d[colname]); hi = sum(_g(mp, v)[2] for v in d[colname])
    return lo, mi, hi
out['inv_tot'] = tot(col(23), inv_mid); out['ven_tot'] = tot(col(24), ven_mid); out['pip_tot'] = tot(col(25), pip_mid)
# concentração: top 3 vendas share (midpoint)
vm = sorted([_g(ven_mid, v)[1] for v in d[col(24)]], reverse=True)
out['ven_top3_share'] = sum(vm[:3]) / sum(vm)
out['ven_top3'] = d.assign(_v=d[col(24)].map(lambda v: _g(ven_mid, v)[1])).sort_values('_v', ascending=False)[['Empresa', col(24)]].head(5).values.tolist()
pm = d.assign(_v=d[col(25)].map(lambda v: _g(pip_mid, v)[1])).sort_values('_v', ascending=False)[['Empresa', col(25)]].head(5).values.tolist()
out['pip_top'] = pm
# medianas
import statistics
out['ven_mediana'] = statistics.median([_g(ven_mid, v)[1] for v in d[col(24)]])
out['inv_mediana'] = statistics.median([_g(inv_mid, v)[1] for v in d[col(24 - 1)]])

# empregos locais
def emp(v):
    v = v.strip()
    return int(v) if v.isdigit() else 0
d['_emp'] = d[col(27)].map(emp)
out['emp_total'] = int(d['_emp'].sum()); out['emp_empresas'] = int((d['_emp'] > 0).sum())

lead_o = ['Até 20', '21 a 50', '51 a 100', '101 a 300', 'Mais de 300']
lead_mid = {'Até 20': (1, 10, 20), '21 a 50': (21, 35, 50), '51 a 100': (51, 75, 100), '101 a 300': (101, 200, 300), 'Mais de 300': (301, 350, 400)}
out['leads'] = vc(col(28), lead_o)
out['leads_tot'] = tot(col(28), lead_mid)
out['novos'] = vc(col(29), ['Até 25%', '26 a 50%', '51 a 75%', 'Mais de 75%'])
# origem contatos (multi)
oc = {}
for v in d[col(30)]:
    for m in [x.strip() for x in v.split(',') if x.strip()]:
        oc[m] = oc.get(m, 0) + 1
out['origem_contatos'] = sorted(oc.items(), key=lambda x: -x[1])
tc = {}
for v in d[col(31)]:
    for m in [x.strip() for x in v.split(',') if x.strip()]:
        tc[m] = tc.get(m, 0) + 1
out['tipo_contatos'] = sorted(tc.items(), key=lambda x: -x[1])
out['novo_mercado'] = d[col(32)].tolist()

nps = pd.to_numeric(d[col(43)], errors='coerce').dropna().astype(int)
prom = int((nps >= 9).sum()); det = int((nps <= 6).sum()); neu = len(nps) - prom - det
out['nps'] = {'prom': prom, 'neu': neu, 'det': det, 'score': round(100 * (prom - det) / len(nps)), 'media': round(float(nps.mean()), 1),
              'dist': [int((nps == v).sum()) for v in range(0, 11)]}

def code(series, rules):
    res = {k: 0 for k in rules}
    for v in series:
        t = norm(v)
        for k, kws in rules.items():
            if any(kw in t for kw in kws): res[k] += 1
    return sorted(res.items(), key=lambda x: -x[1])

out['problemas'] = code(d[col(40)], {
 'Público e poder de compra': ['publico', 'compra', 'vendas', 'consumidor'],
 'Calor / climatização': ['calor', 'climatiz'],
 'Localização do estande': ['localiza', 'afastado'],
 'Infraestrutura (internet, energia)': ['internet', 'fogo', 'luz', 'goteira'],
 'Data e atrações': ['data', 'show'],
 'Barulho da praça de alimentação': ['barulho'],
 'Divulgação tardia': ['divulga'],
})
out['sem_problema'] = int(sum(norm(v) in ('nao', 'nenhum') for v in d[col(40)]))
out['melhorias'] = code(d[col(42)], {
 'Climatização / ventilação': ['climatiz', 'ar condicionado'.replace(' ', ''), 'ventila', 'quente'],
 'Estacionamento, carga e descarga': ['estaciona', 'descarga'],
 'Banheiros, limpeza e água': ['banheir', 'limpeza', 'agua', 'lixeira'],
 'Data e atrações (shows)': ['data', 'show', 'atracao'],
 'Setorização dos pavilhões': ['segment', 'setor', 'ramo', 'categoria'],
 'Divulgação antecipada': ['divulga', 'midia'],
 'Ingresso / cobrança na entrada': ['ingresso', 'cobranca', 'entrada'],
 'Internet e energia': ['internet', 'energia'],
 'Credenciamento e acesso ao estande': ['credencia', 'chegar'],
 'Som da praça de alimentação': ['som', 'barulho'],
 'Espaço kids': ['kids'],
})
out['manter'] = code(d[col(41)], {
 'Organização em geral': ['organiza'],
 'Estrutura e pavilhões': ['estrutura', 'pavilh', 'espaco'],
 'Limpeza e decoração': ['limpeza', 'decora', 'estetica'],
 'Programação e shows': ['show', 'programa', 'mascote'],
 'Diversidade de expositores': ['diversidade'],
 'Divulgação': ['divulga'],
})
# cruzamentos
x = d.copy()
x['_novo'] = x[col(9)] == 'Primeira participação'
out['cobriu_por_estreia'] = pd.crosstab(x['_novo'], x[col(26)]).to_dict()
out['nps_estreantes'] = float(pd.to_numeric(x.loc[x['_novo'], col(43)], errors='coerce').mean())
out['nps_veteranos'] = float(pd.to_numeric(x.loc[~x['_novo'], col(43)], errors='coerce').mean())
out['retorno_por_perfil'] = pd.crosstab(x[col(19)], x[col(21)]).to_dict()
# por porte
pp = []
for p in ['MEI', 'Microempresa', 'Empresa de pequeno porte', 'Média empresa', 'Grande empresa']:
    s_ = x[x[col(6)] == p]
    if len(s_) == 0: continue
    pp.append({'porte': p, 'n': int(len(s_)), 'ger': float(pd.to_numeric(s_[col(12)], errors='coerce').mean()),
               'pos': float((s_[col(26)] != 'Não deve cobrir').mean()), 'volta': float((s_[col(21)] == 'Sim').mean()),
               'nps': float(pd.to_numeric(s_[col(43)], errors='coerce').mean())})
out['por_porte'] = pp
out['sem_outras_feiras'] = int((d[col(20)] == 'Não participo de outras feiras').sum())
top = d.assign(_v=d[col(24)].map(lambda v: _g(ven_mid, v)[1])).sort_values('_v', ascending=False).head(3)
out['top3_setores'] = top[col(5)].tolist()
out['avisos'] = sorted(set(AVISOS))
json.dump(out, open('data/metrics.json', 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
