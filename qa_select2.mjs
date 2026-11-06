export default async function run(page, ui) {
  // login completo
  await page.goto('http://localhost:8000/login/');
  await page.waitForTimeout(1500);
  const snap = await ui.snapshot();
  const g = (label) => snap.match(new RegExp(`@(e\\d+) textbox "${label}"`))?.[1];
  await ui.fill(g('USUÁRIO'), 'admin');
  await ui.fill(g('SENHA'), 'abc123++');
  const code = await page.evaluate(() => {
    const el = document.querySelector('[class*=captcha]');
    return el ? el.innerText.replace(/[^A-Za-z0-9]/g, '') : null;
  });
  if (!code) return { error: 'captcha não lido' };
  await ui.fill(g('VERIFICAÇÃO DE SEGURANÇA'), code);
  await ui.fill(g('NÃO PREENCHA ESTE CAMPO'), '');
  await ui.click(snap.match(/@(e\d+) button "Entrar"/)?.[1]);
  await page.waitForTimeout(2500);

  await page.goto('http://localhost:8000/admin/auth/user/2/change/');
  await page.waitForTimeout(2500);

  const info = await page.evaluate(() => {
    const sel = document.querySelector('select[name$="-estabelecimento"], select[name="estabelecimento"]');
    if (!sel) return { erro: 'select estabelecimento ausente', url: location.href };
    const s2 = window.jQuery && window.jQuery(sel).data('select2');
    return {
      name: sel.name,
      classes: sel.className,
      ajax: sel.getAttribute('data-ajax--url'),
      options: sel.querySelectorAll('option').length,
      temSelect2: !!s2,
      visibleSelect2: !!document.querySelector('.select2-container--admin-autocomplete'),
    };
  });

  // abrir o select2 e verificar as opções carregadas
  let abertura = null;
  if (info.temSelect2) {
    await page.click('.select2-container--admin-autocomplete .select2-selection--multiple');
    await page.waitForTimeout(1500);
    abertura = await page.evaluate(() => {
      const dropdown = document.querySelector('.select2-dropdown');
      const opts = [...document.querySelectorAll('.select2-results__option')].map(o => o.innerText.trim());
      const msg = document.querySelector('.select2-results__message');
      return { dropdownAberto: !!dropdown, opcoes: opts, mensagem: msg ? msg.innerText : null };
    });
    await page.screenshot({ path: '/tmp/perfil_estab.png' });
  }
  return { info, abertura };
}
