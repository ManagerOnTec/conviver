export default async function run(page, ui) {
  const snap = await ui.snapshot();
  const g = (label) => snap.match(new RegExp(`@(e\\d+) textbox "${label}"`))?.[1];
  await ui.fill(g('USUÁRIO'), 'admin');
  await ui.fill(g('SENHA'), 'abc123++');
  const code = await page.evaluate(() => {
    const el = document.querySelector('[class*=captcha]');
    return el ? el.innerText.replace(/[^A-Za-z0-9]/g, '') : null;
  });
  await ui.fill(g('VERIFICAÇÃO DE SEGURANÇA'), code);
  await ui.fill(g('NÃO PREENCHA ESTE CAMPO'), '');
  await ui.click(snap.match(/@(e\d+) button "Entrar"/)?.[1]);
  await page.waitForTimeout(2000);
  return { url: page.url() };
}
