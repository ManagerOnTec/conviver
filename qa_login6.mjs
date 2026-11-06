export default async function run(page, ui) {
  const snap = await ui.snapshot();
  const g = (label) => snap.match(new RegExp(`@(e\\d+) textbox "${label}"`))?.[1];
  await ui.fill(g('USUÁRIO'), 'admin');
  await ui.fill(g('SENHA'), 'abc123++');
  // ler o código captcha do SVG/texto da página
  const code = await page.evaluate(() => {
    const el = document.querySelector('[class*=captcha]');
    const txt = el ? el.innerText : '';
    // pega os caracteres isolados (Q 3 B 3 L) antes das linhas "AI:"
    const chars = txt.split('\n').map(s => s.trim()).filter(s => /^[A-Za-z0-9]$/.test(s));
    return chars.join('');
  });
  await ui.fill(g('VERIFICAÇÃO DE SEGURANÇA'), code);
  await ui.fill(g('NÃO PREENCHA ESTE CAMPO'), '');
  await ui.click(snap.match(/@(e\d+) button "Entrar"/)?.[1]);
  await page.waitForTimeout(2500);
  return { url: page.url(), code };
}
