import { neon } from '@neondatabase/serverless';

export default async function handler(req, res) {
  try {
    const sql = neon(process.env.DATABASE_URL);
    const [meta, indicadores, series, visitacao, avaliacoes, textos] = await Promise.all([
      sql`select chave, valor from meta`,
      sql`select chave, capitulo, ordem, rotulo, valor::float as valor, prefixo, sufixo, casas, nota, tom from indicadores order by capitulo, ordem`,
      sql`select grafico, ordem, rotulo, valor::float as valor, destaque, nota from series order by grafico, ordem`,
      sql`select to_char(data,'DD/MM') as dia, dia_semana, entradas, capacidade, situacao from visitacao_diaria order by data`,
      sql`select aspecto, ordem, n1, n2, n3, n4, n5, media::float as media from avaliacoes order by ordem`,
      sql`select chave, capitulo, ordem, titulo, corpo from textos order by capitulo, ordem`,
    ]);
    const s = {};
    for (const r of series) (s[r.grafico] ||= []).push(r);
    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=3600');
    res.status(200).json({
      meta: Object.fromEntries(meta.map(r => [r.chave, r.valor])),
      indicadores: Object.fromEntries(indicadores.map(r => [r.chave, r])),
      series: s, visitacao, avaliacoes,
      textos: Object.fromEntries(textos.map(r => [r.chave, r])),
    });
  } catch (e) {
    console.error(e);
    res.status(500).json({ erro: 'Falha ao carregar os dados' });
  }
}
