"""Gera os comandos SQL (upsert, sem apagar nada) a partir de data/metrics.json e data/visit.json.
Saída: data/update_sql.json (lista de comandos) — executar no Neon numa transação.
"""
import json
M = json.load(open('data/metrics.json'))
V = json.load(open('data/visit.json' if __import__('os').path.exists('data/visit.json') else 'pipeline/visit.json'))
N = M['n_empresas']

def q(s): return "NULL" if s is None else "'" + str(s).replace("'", "''") + "'"
def br(x, d=0):
    s = f"{x:,.{d}f}"; return s.replace(',', 'X').replace('.', ',').replace('X', '.')
def money(v):
    if v >= 1e6:
        x = v / 1e6; return f"R$ {br(x, 2)} {'milhão' if x < 2 else 'milhões'}"
    return f"R$ {br(v/1e3)} mil"
def pct(a, b): return br(100 * a / b) + '%'

inv, ven, pip = M['inv_tot'], M['ven_tot'], M['pip_tot']
cob = dict(M['cobriu']); ret = dict(M['retorno_prox']); R = M['ratings']; nps = M['nps']
dias = V['dias']; real = [d for d in dias if d['situacao'] != 'a realizar']
entr = sum(d['entradas'] for d in dias)
fds = sum(d['entradas'] for d in dias[:3])
final = V['final']
status = 'final' if final else 'prévia'
porte = dict(M['porte'])
mei_micro = porte.get('MEI', 0) + porte.get('Microempresa', 0)
pp = {p['porte']: p for p in M['por_porte']}
fator = 235 / N
PL = {'MEI': 'MEIs', 'Microempresa': 'microempresas', 'Empresa de pequeno porte': 'empresas de pequeno porte', 'Média empresa': 'médias empresas', 'Grande empresa': 'grandes empresas'}

sql = []
# meta
import math
me = round(100 * 1.96 * math.sqrt(0.25 / N) * math.sqrt((235 - N) / 234))
meta = {'margem_erro': me, 'visitacao_status': status, 'visitacao_corte': V['corte'], 'pesquisa_n_respostas': M['n_respostas'],
        'pesquisa_n_empresas': N, 'atualizado_em': (V['corte'] or '')[:10]}
sql.append("insert into meta values " + ",".join(f"({q(k)},{q(v)})" for k, v in meta.items()) +
           " on conflict (chave) do update set valor=excluded.valor")

ind = [
 ('entradas', 'hero', 2, 'entradas registradas', entr, '', '', 0, ('total do evento' if final else f"prévia até {V['corte'][:5]}"), 'laranja'),
 ('vendas_amostra', 'hero', 3, 'em vendas declaradas', ven[1] / 1e6, 'R$ ', ' mi', 2, f'{N} expositores pesquisados', 'verde'),
 ('negocios_amostra', 'hero', 4, 'em negócios encaminhados', pip[1] / 1e6, 'R$ ', ' mi', 2, 'próximos 3 a 6 meses', 'azul'),
 ('ingressos_pagos', 'publico', 2, 'ingressos pagos', V['ingressos_pagos'], '', '', 0, f"inclui {br(V['passaportes'] or 0)} passaportes", 'roxo'),
 ('gratuitos', 'publico', 3, 'ingressos gratuitos', V['gratuitos'], '', '', 0, 'desconto integral', 'verde'),
 ('a_conferir', 'publico', 4, 'ingressos a conferir', V['a_conferir'], '', '', 0, 'fora dos confirmados', 'laranja'),
 ('cracha_expositores', 'publico', 5, 'crachás de expositores', V['cracha_expositores'], '', '', 0, 'representantes', 'azul'),
 ('nota_volume', 'publico', 6, 'nota do volume de público', R['Volume de público']['media'], '', '/5', 1, 'avaliação dos expositores', 'roxo'),
 ('nota_qualidade', 'publico', 7, 'nota da qualidade do público', R['Qualidade do público']['media'], '', '/5', 1, 'compradores e decisores', 'laranja'),
 ('investimento', 'faturamento', 1, 'investidos pelos pesquisados', inv[1] / 1e3, 'R$ ', ' mil', 0, f'faixa R$ {br(inv[0]/1e3)} a {br(inv[2]/1e3)} mil', 'laranja'),
 ('vendas', 'faturamento', 2, 'vendas fechadas na feira', ven[1] / 1e6, 'R$ ', ' mi', 2, f'faixa R$ {br(ven[0]/1e6,2)} a {br(ven[2]/1e6,2)} mi', 'verde'),
 ('negocios', 'faturamento', 3, 'negócios encaminhados', pip[1] / 1e6, 'R$ ', ' mi', 2, f'faixa R$ {br(pip[0]/1e6,2)} a {br(pip[2]/1e6,2)} mi', 'azul'),
 ('retorno', 'faturamento', 4, 'em negócios por real investido', (ven[1] + pip[1]) / inv[1], 'R$ ', '', 1, 'vendas + negócios / investimento', 'roxo'),
 ('venda_mediana', 'faturamento', 5, 'venda mediana por expositor', M['ven_mediana'] / 1e3, 'R$ ', ' mil', 0, None, 'laranja'),
 ('invest_mediano', 'faturamento', 6, 'investimento mediano', M['inv_mediana'] / 1e3, 'R$ ', ' mil', 0, None, 'laranja'),
 ('concentracao', 'faturamento', 7, 'das vendas em 3 empresas', round(M['ven_top3_share'] * 100), '', '%', 0, None, 'laranja'),
 ('universo_vendas_min', 'faturamento', 8, 'vendas: cenário conservador', ven[0] * fator / 1e6, 'R$ ', ' mi', 1, None, 'verde'),
 ('universo_vendas_med', 'faturamento', 9, 'vendas: cenário central', ven[1] * fator / 1e6, 'R$ ', ' mi', 1, None, 'verde'),
 ('universo_neg_min', 'faturamento', 10, 'negócios: cenário conservador', pip[0] * fator / 1e6, 'R$ ', ' mi', 1, None, 'azul'),
 ('universo_neg_med', 'faturamento', 11, 'negócios: cenário central', pip[1] * fator / 1e6, 'R$ ', ' mi', 1, None, 'azul'),
 ('leads', 'prospeccao', 1, 'contatos qualificados (leads)', round(M['leads_tot'][1], -2), '~', '', 0, f'{N} empresas pesquisadas', 'roxo'),
 ('novos_75', 'prospeccao', 2, 'com mais de 75% de clientes novos', round(100 * M['novos'][3][1] / N), '', '%', 0, f"{M['novos'][3][1]} empresas", 'azul'),
 ('contratacoes', 'prospeccao', 3, 'contratações locais', M['emp_total'], '', '', 0, f"por {M['emp_empresas']} empresas", 'verde'),
 ('estreantes', 'prospeccao', 4, 'estrearam na Feisma', round(100 * M['edicoes'][0][1] / N), '', '%', 0, f"{M['edicoes'][0][1]} de {N} empresas", 'laranja'),
 ('nps', 'satisfacao', 1, 'NPS de expositores', nps['score'], '', '', 0, f"{nps['prom']} promotores · {nps['det']} detratores", 'laranja'),
 ('nota_geral', 'satisfacao', 2, 'avaliação geral da feira', R['Avaliação geral da feira']['media'], '', '/5', 1, None, 'roxo'),
 ('voltam', 'satisfacao', 3, 'pretendem voltar', ret['Sim'], '', '', 0, f"+ {ret['Talvez']} talvez", 'verde'),
 ('cobrir', 'satisfacao', 4, 'esperam cobrir o investimento', round(100 * (cob['Já cobriu'] + cob['Deve cobrir com os negócios encaminhados']) / N), '', '%', 0, f"{cob['Já cobriu']} já cobriram", 'azul'),
]
sql.append("insert into indicadores values " + ",".join(
    f"({q(a)},{q(b)},{c},{q(d)},{round(e,4)},{q(f)},{q(g)},{h},{q(i)},{q(j)})" for a, b, c, d, e, f, g, h, i, j in ind) +
    " on conflict (chave) do update set rotulo=excluded.rotulo, valor=excluded.valor, prefixo=excluded.prefixo, sufixo=excluded.sufixo, casas=excluded.casas, nota=excluded.nota")

S = []
def add(g, items):
    for i, (l, v) in enumerate(items): S.append((g, i + 1, l, v))
for g in ['porte', 'edicoes', 'origem_contatos', 'perfil_publico', 'investimento', 'vendas', 'pipeline', 'leads', 'novos',
          'tipo_contatos', 'retorno_prox', 'problemas', 'manter']:
    add(g, M[g] if g not in ('manter',) else M[g][:4])
add('origem_amostra', M['origem_municipio'])
add('motivos', [(l.replace('Relacionamento com clientes atuais', 'Relação com clientes atuais'), v) for l, v in M['motivos'][:6]])
add('comparacao', M['comparacao'][:3]); add('melhorias', M['melhorias'][:8])
add('cobriu', [('Já cobriu', cob['Já cobriu']), ('Deve cobrir', cob['Deve cobrir com os negócios encaminhados']), ('Não deve cobrir', cob['Não deve cobrir'])])
add('nps_dist', [(str(i), v) for i, v in enumerate(nps['dist'])])
add('porte_nps', [(p['porte'], round(p['nps'], 1)) for p in M['por_porte']])
add('porte_volta', [(p['porte'], round(100 * p['volta'])) for p in M['por_porte']])
T = V.get('tipos') or {}
add('ingressos_tipo', [('Feisma · Dia', T.get('Feisma • Dia', 0)), ('Feisma · Passaporte', T.get('Feisma • Passaporte', 0)),
                       ('Santa Summit · Dia', T.get('Santa Summit • Dia', 0)), ('Santa Summit · Passaporte', T.get('Santa Summit • Passaporte', 0))])
sql.append("insert into series(grafico,ordem,rotulo,valor) values " + ",".join(f"({q(g)},{o},{q(l)},{v})" for g, o, l, v in S) +
           " on conflict (grafico, ordem) do update set rotulo=excluded.rotulo, valor=excluded.valor")

sql.append("insert into visitacao_diaria values " + ",".join(
    f"({q(d['data'])},{q(d['dia_semana'])},{d['entradas']},{d['capacidade'] or 'NULL'},{q(d['situacao'])})" for d in dias) +
    " on conflict (data) do update set dia_semana=excluded.dia_semana, entradas=excluded.entradas, capacidade=excluded.capacidade, situacao=excluded.situacao")

order = sorted(R.items(), key=lambda kv: -kv[1]['media'])
sql.append("insert into avaliacoes values " + ",".join(
    f"({q(k)},{i+1},{','.join(str(x) for x in v['dist'])},{v['media']})" for i, (k, v) in enumerate(order)) +
    " on conflict (aspecto) do update set ordem=excluded.ordem, n1=excluded.n1, n2=excluded.n2, n3=excluded.n3, n4=excluded.n4, n5=excluded.n5, media=excluded.media")

melhor, pior = order[0][0], order[-1][0]
grandes = pp.get('Grande empresa'); low = min(M['por_porte'], key=lambda p: p['volta'])
cf = sum(d['entradas'] for d in dias[3:] if d['situacao'] == 'realizado')
nuteis = len([d for d in dias[3:] if d['situacao'] == 'realizado'])
tx = {
 'lead_publico': ('publico', 0, 'Quem visitou',
   f"Entradas registradas no controle de acesso do evento conjunto Feisma/Santa Summit. O fim de semana de abertura e o feriado de Finados concentraram {pct(fds, entr)} do fluxo; nos {nuteis} dias seguintes, a média foi de {br(cf / max(nuteis,1))} entradas por dia, bem abaixo da capacidade."),
 'lead_faturamento': ('faturamento', 0, 'O que a feira gerou',
   f"Investimento, vendas e negócios encaminhados declarados por {N} expositores pesquisados. Respostas por faixa de valor, somadas pelo ponto médio de cada faixa."),
 'lead_prospeccao': ('prospeccao', 0, 'Contatos e mercado',
   f"A Feisma é essencialmente uma feira de varejo: {dict(M['tipo_contatos']).get('Clientes finais',0)} das {N} empresas atenderam clientes finais, e {pct(dict(M['origem_contatos']).get('Santa Maria',0), N)} citam Santa Maria como origem dos principais contatos."),
 'lead_satisfacao': ('satisfacao', 0, 'Como os expositores avaliaram',
   f"O aspecto mais bem avaliado foi {melhor.lower()} ({br(order[0][1]['media'],1)} de 5); o pior, {pior.lower()} ({br(order[-1][1]['media'],1)}). " +
   (f"As grandes empresas saíram mais satisfeitas (recomendação média {br(grandes['nps'],1)}); entre as {PL[low['porte']]}, " + ("nenhuma confirmou a próxima edição." if low['volta'] == 0 else f"só {pct(low['volta'],1)} confirmam a próxima edição.") if grandes else '')),
 'cap_porte': ('caps', 1, None, f"MEIs e microempresas são {pct(mei_micro, N)} da amostra: a feira é vitrine para pequenos negócios."),
 'cap_edicoes': ('caps', 2, None, f"{pct(M['edicoes'][0][1], N)} das empresas estrearam nesta edição."),
 'cap_pvo': ('caps', 3, None, (f"As grandes empresas são as mais satisfeitas (recomendação média {br(grandes['nps'],1)}). " if grandes else '') +
             (f"Nenhuma das {PL[low['porte']]} confirmou o retorno." if low['volta'] == 0 else f"Entre as {PL[low['porte']]}, {pct(low['volta'],1)} confirmam o retorno.")),
 'cap_cmp': ('caps', 4, None, f"{M['sem_outras_feiras']} empresas não participam de outras feiras"),
 'cap_conc': ('caps', 5, None, f"<b>{'Concentração' if M['ven_top3_share'] >= 0.5 else 'Distribuição'}.</b> As três maiores vendas somam {round(M['ven_top3_share']*100)}% do total estimado. Para o expositor típico (venda mediana de R$ {br(M['ven_mediana']/1e3)} mil, investimento mediano de R$ {br(M['inv_mediana']/1e3)} mil), o retorno depende dos negócios encaminhados."),
 'parecer_2': ('parecer', 2, 'Escala e base produtiva local',
   f"Com 242 estandes ocupados por 235 expositores e público estimado de {br(round(entr*1.25))} visitas ({br(entr)} entradas registradas mais 25% referente a expositores{'' if final else ', prévia'}), a Feisma é um evento de grande porte para o interior do estado. 58% dos expositores são da Região Central: o dinheiro investido em estandes, montagem, equipes e serviços e o faturamento gerado ficam em boa parte na própria região. Na amostra, {M['emp_empresas']} das {N} empresas contrataram pessoas ou fornecedores locais."),
 'parecer_3': ('parecer', 3, 'Geração de negócios',
   f"Os {N} expositores pesquisados declararam cerca de {money(ven[1])} em vendas e {money(pip[1])} em negócios encaminhados, frente a cerca de {money(inv[1])} investidos: perto de R$ {br((ven[1]+pip[1])/inv[1],1)} em negócios por real investido. Expandido para toda a feira, o resultado fica na ordem de R$ {br(ven[0]*fator/1e6)} a {br(ven[1]*fator/1e6)} milhões em vendas diretas, sem contar o gasto dos visitantes com alimentação, transporte e hospedagem."),
 'parecer_4': ('parecer', 4, 'Porta de entrada para pequenos negócios',
   f"MEIs e microempresas são {pct(mei_micro, N)} da amostra e {pct(M['edicoes'][0][1], N)} das empresas expuseram pela primeira vez. A feira cumpre papel de política de desenvolvimento: dá visibilidade a quem não tem loja própria, testa produtos e ajuda a ampliar empreendimentos locais, incluindo artesanato e produtos tradicionalistas."),
 'parecer_5': ('parecer', 5, 'Onde está o gargalo',
   f"O problema não é a quantidade de visitantes, mas a conversão. A qualidade do público como comprador recebeu nota {br(R['Qualidade do público']['media'],1)} de 5 e a venda mediana (R$ {br(M['ven_mediana']/1e3)} mil) ficou abaixo do investimento mediano (R$ {br(M['inv_mediana']/1e3)} mil). " + ("O resultado está concentrado em poucas empresas de maior porte, e o NPS" if M['ven_top3_share'] >= 0.5 else "O expositor típico depende dos negócios futuros para pagar a participação, e o NPS") + f" de expositores ({nps['score']}) é sinal de alerta: sem melhorar a conversão, a renovação de expositores pode virar rotatividade."),
}
sql.append("insert into textos values " + ",".join(f"({q(k)},{q(c)},{o},{q(t)},{q(b)})" for k, (c, o, t, b) in tx.items()) +
           " on conflict (chave) do update set titulo=coalesce(excluded.titulo, textos.titulo), corpo=excluded.corpo")
import sys
if '--so-pesquisa' in sys.argv:
    # atualização automática: não mexe em nada que venha do relatório de visitação
    VIS_IND = {'entradas', 'ingressos_pagos', 'gratuitos', 'a_conferir', 'cracha_expositores'}
    meta_p = {k: v for k, v in meta.items() if k in ('margem_erro', 'pesquisa_n_respostas', 'pesquisa_n_empresas')}
    from datetime import datetime; from zoneinfo import ZoneInfo
    meta_p['atualizado_em'] = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y')
    sql = ["insert into meta values " + ",".join(f"({q(k)},{q(v)})" for k, v in meta_p.items()) + " on conflict (chave) do update set valor=excluded.valor"]
    ind_p = [r for r in ind if r[0] not in VIS_IND]
    sql.append("insert into indicadores values " + ",".join(
        f"({q(a)},{q(b)},{c},{q(d)},{round(e,4)},{q(f)},{q(g)},{h},{q(i)},{q(j)})" for a, b, c, d, e, f, g, h, i, j in ind_p) +
        " on conflict (chave) do update set rotulo=excluded.rotulo, valor=excluded.valor, prefixo=excluded.prefixo, sufixo=excluded.sufixo, casas=excluded.casas, nota=excluded.nota")
    S_p = [r for r in S if r[0] != 'ingressos_tipo']
    sql.append("insert into series(grafico,ordem,rotulo,valor) values " + ",".join(f"({q(g)},{o},{q(l)},{v})" for g, o, l, v in S_p) +
               " on conflict (grafico, ordem) do update set rotulo=excluded.rotulo, valor=excluded.valor")
    sql.append("insert into avaliacoes values " + ",".join(
        f"({q(k)},{i+1},{','.join(str(x) for x in v['dist'])},{v['media']})" for i, (k, v) in enumerate(order)) +
        " on conflict (aspecto) do update set ordem=excluded.ordem, n1=excluded.n1, n2=excluded.n2, n3=excluded.n3, n4=excluded.n4, n5=excluded.n5, media=excluded.media")
    tx_p = {k: v for k, v in tx.items() if k not in ('lead_publico', 'parecer_2')}
    sql.append("insert into textos values " + ",".join(f"({q(k)},{q(c)},{o},{q(t)},{q(b)})" for k, (c, o, t, b) in tx_p.items()) +
               " on conflict (chave) do update set titulo=coalesce(excluded.titulo, textos.titulo), corpo=excluded.corpo")
    sql.append(f"update textos set corpo=regexp_replace(corpo, 'Na amostra, [0-9]+ das [0-9]+ empresas', 'Na amostra, {M['emp_empresas']} das {N} empresas') where chave='parecer_2'")
json.dump(sql, open('data/update_sql.json', 'w'), ensure_ascii=False)
print(f'{len(sql)} comandos; entradas={entr}; status={status}; empresas={N}; avisos={M.get("avisos")}')
