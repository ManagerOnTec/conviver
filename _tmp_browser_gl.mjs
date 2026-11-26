export default async function run(page, ui) {
  const sessionid = process.env.SESSIONID;
  await page.context().addCookies([{ name: 'sessionid', value: sessionid,
      domain: 'localhost', path: '/', httpOnly: true, sameSite: 'Lax' }]);
  await page.goto('http://localhost:8000/leitos/leito_mapa/',
      { timeout: 120000, waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  const abrir = await page.evaluate(() => {
    const b = document.querySelector('[data-bs-target="#modal-ocupar"]');
    if (!b) return 'sem botão';
    b.click();
    return 'ok';
  });
  await page.waitForTimeout(1200);
  const estado = await page.evaluate(() => {
    const modal = document.getElementById('modal-ocupar');
    if (!modal) return { erro: 'modal ausente' };
    const leito = modal.querySelector('select[name="leito"]');
    const at = modal.querySelector('select[name="atendimento"]');
    const s2 = document.querySelector('#id_atendimento.select2-hidden-accessible, .select2');
    return {
      show: modal.classList.contains('show'),
      leitoOptions: leito ? leito.options.length : -1,
      leitoVisivel: leito ? leito.getBoundingClientRect().height > 0 : false,
      atendimentoPresente: !!at,
      select2Inicializado: !!s2,
      erros: [],
    };
  });
  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  await page.screenshot({ path: '/tmp/modal_ocupar.png' });
  return { abrir, estado, consoleErrors: consoleErrors.slice(0, 5) };
}
