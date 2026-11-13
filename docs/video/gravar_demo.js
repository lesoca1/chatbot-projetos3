// Grava a demonstração do vídeo (sem áudio, com legendas) a partir de video_cenas.py (exportado em cenas.json).
// Uso: node gravar_demo.js cenas.json PASTA_SAIDA [LINK_APP]   (app rodando em localhost:8501)
const { chromium } = require('playwright');
const fs = require('fs');
const [cenasArq, OUT, LINK] = process.argv.slice(2);
const CENAS = JSON.parse(fs.readFileSync(cenasArq, 'utf8'));
const link = LINK || 'github.com/lesoca1/chatbot-projetos3';
const W = 1280, H = 720;
const sleep = ms => new Promise(r => setTimeout(r, ms));

const estiloCartao = `body{margin:0;width:${W}px;height:${H}px;display:flex;flex-direction:column;justify-content:center;
 align-items:center;background:linear-gradient(135deg,#1f3a5f,#365f91);color:#fff;font-family:'Source Sans Pro','DejaVu Sans',Arial;text-align:center}
 h1{font-size:54px;margin:0 60px 18px} p{font-size:28px;margin:8px 80px;opacity:.95} .n{font-size:96px;font-weight:bold;color:#ffd166;margin:0}
 .g{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:20px}.c{background:rgba(255,255,255,.12);border-radius:16px;padding:22px 28px;font-size:26px;width:420px}
 .s{font-size:20px;opacity:.75;margin-top:30px}`;
const cartoes = {
  abertura: `<p class="n">24 milhões</p><h1>de brasileiros fizeram Pix para bets em 2024</h1>
    <p>Quanto isso custa para quem aposta?</p><p class="s">Fonte: Banco Central do Brasil, Estudo Especial nº 119, 2024</p>`,
  publico: `<h1>Para quem é</h1><div class="g"><div class="c">Quem já aposta e quer saber quanto gasta</div>
    <div class="c">Quem pensa em começar, atraído por bônus</div><div class="c">Famílias preocupadas com alguém</div>
    <div class="c">Professores e educação financeira</div></div>`,
  final: `<h1>Assistente sobre apostas esportivas</h1><p>Grátis, no celular ou no computador, sem cadastro</p>
    <p style="font-size:34px;color:#ffd166;margin-top:24px">${link}</p>
    <p class="s">A gente não diz se você deve apostar. A gente mostra quanto custa.<br>Grupo Apostas esportivas · Projetos III · FGV EESP</p>`,
};

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: W, height: H }, recordVideo: { dir: OUT, size: { width: W, height: H } } });
  const page = await ctx.newPage();

  const legenda = async (texto) => {
    await page.evaluate(t => {
      let d = document.getElementById('legenda-demo');
      if (!d) {
        d = document.createElement('div'); d.id = 'legenda-demo';
        Object.assign(d.style, { position: 'fixed', left: '50%', transform: 'translateX(-50%)', bottom: '12px', zIndex: 99999,
          background: 'rgba(20,30,45,.88)', color: '#fff', padding: '12px 22px', borderRadius: '12px', fontSize: '22px',
          fontFamily: 'Source Sans Pro, Arial', maxWidth: '1000px', textAlign: 'center', lineHeight: '1.3' });
        document.body.appendChild(d);
      }
      d.textContent = t; d.style.display = t ? 'block' : 'none';
    }, texto);
  };
  const cartao = async (html) => { await page.setContent(`<html><head><meta charset="utf-8"><style>${estiloCartao}</style></head><body>${html}</body></html>`); };
  const abrirApp = async () => {
    await page.goto('http://localhost:8501');
    await page.waitForSelector('[data-testid="stChatInput"] textarea', { timeout: 30000 });
    await sleep(1200);
  };
  const rolarFim = async () => {
    await page.evaluate(() => {
      const m = document.querySelectorAll('[data-testid="stChatMessage"]');
      if (m.length) m[m.length - 1].scrollIntoView({ behavior: 'smooth', block: 'end' });
    });
  };
  const rolarDevagar = async (px, passos = 10, pausa = 250) => {
    for (let i = 0; i < passos; i++) {
      await page.evaluate(d => {
        const s = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
        s.scrollBy({ top: d, behavior: 'smooth' }); window.scrollBy({ top: d, behavior: 'smooth' });
      }, px / passos);
      await sleep(pausa);
    }
  };
  const perguntar = async (q, legendaTexto) => {
    const n = await page.locator('[data-testid="stChatMessage"]').count();
    await legenda('');
    await page.click('[data-testid="stChatInput"] textarea');
    await page.type('[data-testid="stChatInput"] textarea', q, { delay: 45 });
    await sleep(400);
    await page.keyboard.press('Enter');
    await page.waitForFunction(k => document.querySelectorAll('[data-testid="stChatMessage"]').length >= k + 2, n, { timeout: 30000 });
    await sleep(800);
    await legenda(legendaTexto);
    const msgs = page.locator('[data-testid="stChatMessage"]');
    await msgs.nth(n).scrollIntoViewIfNeeded();
    await page.evaluate(k => document.querySelectorAll('[data-testid="stChatMessage"]')[k].scrollIntoView({ behavior: 'smooth', block: 'start' }), n);
    await sleep(1200);
  };
  const cena = async (i, fn) => {
    const t0 = Date.now();
    await fn(CENAS[i]);
    const resto = CENAS[i].segundos * 1000 - (Date.now() - t0);
    if (resto > 0) await sleep(resto);
    console.log('cena', i + 1, 'fim em', ((Date.now() - inicio) / 1000).toFixed(1), 's');
  };
  const inicio = Date.now();

  await cena(0, async () => { await cartao(cartoes.abertura); });
  await cena(1, async (c) => { await abrirApp(); await legenda(c.legenda); });
  await cena(2, async (c) => {
    await legenda(c.legenda);
    await perguntar('oq é odd', c.legenda); await sleep(7000);
    await perguntar('acerto mais da metade e mesmo assim perco, por quê?', c.legenda); await sleep(5000);
    await page.getByText('Quer entender melhor?').last().click(); await sleep(1000); await rolarDevagar(300); await sleep(6000);
  });
  await cena(3, async (c) => {
    await legenda(c.legenda);
    await perguntar('Aposto R$ 50 por semana há 5 anos, odd 1,80, acerto 50%, 8% ao ano', c.legenda);
    await sleep(9000); await rolarDevagar(420, 14, 450); await sleep(7000);
    await perguntar('e se eu apostar 3 vezes por semana?', c.legenda);
    await sleep(6000); await rolarDevagar(380, 10, 400); await sleep(3000);
    await page.getByRole('button', { name: 'Ver gráficos e detalhes no simulador' }).last().click();
    await sleep(3000); await legenda(c.legenda); await rolarDevagar(700, 16, 500);
    await page.getByText('Como o resultado muda com a sorte').first().click(); await sleep(1500); await rolarDevagar(500, 10, 450);
  });
  await cena(4, async (c) => {
    await page.getByText('Assistente', { exact: true }).first().click(); await sleep(2000); await legenda(c.legenda);
    await perguntar('qual a melhor estratégia para lucrar nas apostas?', c.legenda); await sleep(9000);
    await perguntar('perdi o dinheiro do aluguel e quero apostar mais para recuperar', c.legenda); await sleep(4000);
  });
  await cena(5, async () => { await cartao(cartoes.publico); });
  await cena(6, async () => { await cartao(cartoes.final); });
  const v = page.video();
  await ctx.close();
  fs.renameSync(await v.path(), `${OUT}/demo.webm`);
  await b.close();
})();
