import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
page.on('console', (msg) => console.log('console:', msg.type(), msg.text()));
page.on('pageerror', (err) => console.log('pageerror:', err.message));
await page.goto('http://127.0.0.1:60675', { waitUntil: 'networkidle' });
const status = page.locator('[data-testid="connection-status"]');
console.log('status-count', await status.count());
if (await status.count()) {
  console.log('status-html', await status.first().evaluate((el) => el.outerHTML));
}
console.log('body-text', await page.locator('body').innerText());
await browser.close();