import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
page.on('console', (msg) => console.log('console:', msg.type(), msg.text()));
page.on('pageerror', (err) => console.log('pageerror:', err.message));
await page.goto('http://127.0.0.1:54244', { waitUntil: 'networkidle' });
console.log(await page.locator('[data-testid="connection-status"]').first().evaluate((el) => el.outerHTML));
await browser.close();