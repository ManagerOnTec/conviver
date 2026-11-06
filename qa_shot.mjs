export default async function run(page, ui) {
  // já logado na sessão qa1? navega direto
  await page.goto('http://localhost:8000/admin/auth/user/2/change/');
  await page.waitForTimeout(1500);
  if (page.url().includes('/login/')) return { error: 'precisa logar' };
  const el = await page.$('#perfil .perfil-add-btn, .perfil-add-btn');
  const n = await page.evaluate(() => document.querySelectorAll('.perfil-add-btn').length);
  return { url: page.url(), botoes: n, visivel: el ? await el.isVisible() : false };
}
