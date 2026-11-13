// Captura as telas do relatório técnico (app rodando em localhost:8501). Uso: node capturar_telas.js PASTA
// As figuras 08 e 09 do relatório são recortes de 09_simulador_detalhes.png.
const { chromium } = require('playwright');
const OUT = process.argv[2];
(async () => {
  const b = await chromium.launch();
  const page = await b.newPage({ viewport: { width: 1280, height: 2200 }, deviceScaleFactor: 1.5 });
  const go = async () => { await page.goto('http://localhost:8501'); await page.waitForSelector('[data-testid="stChatInput"] textarea', {timeout: 30000}); await page.waitForTimeout(1500); };
  const ask = async (q) => {
    const n = await page.locator('[data-testid="stChatMessage"]').count();
    await page.fill('[data-testid="stChatInput"] textarea', q);
    await page.keyboard.press('Enter');
    await page.waitForFunction(k => document.querySelectorAll('[data-testid="stChatMessage"]').length >= k + 2, n, {timeout: 30000});
    await page.waitForTimeout(2500);
  };
  const shotMsgs = async (name, from) => {
    const msgs = page.locator('[data-testid="stChatMessage"]');
    const n = await msgs.count();
    const boxes = [];
    for (let i = from ?? n - 2; i < n; i++) boxes.push(await msgs.nth(i).boundingBox());
    const y0 = Math.min(...boxes.map(b => b.y)) - 10, y1 = Math.max(...boxes.map(b => b.y + b.height)) + 10;
    const x0 = Math.min(...boxes.map(b => b.x)) - 10, x1 = Math.max(...boxes.map(b => b.x + b.width)) + 10;
    await page.screenshot({ path: `${OUT}/${name}.png`, clip: { x: x0, y: y0, width: x1 - x0, height: y1 - y0 } });
  };
  // 1. início
  await go();
  await page.setViewportSize({ width: 1280, height: 860 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${OUT}/01_inicio.png` });
  await page.setViewportSize({ width: 1280, height: 2200 });
  // 2. pergunta simples
  await ask('O que é odd?');
  await shotMsgs('02_pergunta_odd');
  // 3. cenário
  await ask('Aposto R$ 50 por semana há 5 anos, odd 1,80, acerto 50%, 8% ao ano');
  await shotMsgs('03_cenario_conversa');
  // 4. seguimento
  await ask('e se eu apostar 3 vezes por semana?');
  await shotMsgs('04_seguimento');
  // 5. neutralidade
  await ask('qual a melhor estratégia para lucrar nas apostas?');
  await shotMsgs('05_neutralidade');
  // 6. segurança
  await ask('perdi o dinheiro do aluguel e quero apostar mais para recuperar');
  await shotMsgs('06_seguranca');
  // 7. fora da base
  await ask('qual a capital da França?');
  await shotMsgs('07_fora_da_base');
  // 8. simulador com o cenário do Conteúdo IV
  await go();
  await ask('Aposto R$ 50 por semana há 5 anos, odd 1,80, acerto 50%, 8% ao ano');
  await page.getByRole('button', { name: 'Ver gráficos e detalhes no simulador' }).first().click();
  await page.waitForTimeout(3000);
  const main = page.locator('[data-testid="stMainBlockContainer"]');
  await main.screenshot({ path: `${OUT}/08_simulador.png` });
  for (const t of ['Como o resultado muda com a sorte', 'E se você acertar menos (ou mais) do que imagina?']) {
    await page.getByText(t).first().click(); await page.waitForTimeout(1500);
  }
  await main.screenshot({ path: `${OUT}/09_simulador_detalhes.png` });
  await b.close();
})();
