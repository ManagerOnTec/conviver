export default async function run(page, ui) {
  const snap = await ui.snapshot();
  const g = (label) => snap.match(new RegExp(`@(e\\d+) textbox "${label}"`))?.[1];
  await ui.fill(g('USUÁRIO'), 'admin');
  await ui.fill(g('SENHA'), 'abc123++');
  // captcha: precisa ler o código da própria página
  const code = await page.evaluate(() => {
    const el = document.querySelector('.captcha-codigo, .captcha-text, [class*=captcha]');
    if (!el) return null;
    return el.innerText.replace(/[^A-Za-z0-9]/g, '').slice(0, 8);
  });
  if (!code) return { error: 'captcha não lido' };
  await ui.fill(g('VERIFICAÇÃO DE SEGURANÇA'), code);
  await ui.fill(g('NÃO PREENCHA ESTE CAMPO'), '');
  await ui.click(snap.match(/@(e\d+) button "Entrar"/)?.[1]);
  await page.waitForTimeout(1500);
  return { url: page.url(), titulo: await page.title() };
}
