const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    // Test 1: Direct fetch from browser to backend
    console.log('=== Test 1: Browser → Backend (8001) ===');
    const r1 = await page.evaluate(async () => {
        try {
            const resp = await fetch('http://localhost:8001/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: 'hello', use_rag: true, enable_thinking: true }),
            });
            return { status: resp.status, ok: resp.ok, text: (await resp.text()).substring(0, 200) };
        } catch (e) {
            return { error: e.message };
        }
    });
    console.log(JSON.stringify(r1, null, 2));

    // Test 2: Through Vite proxy
    console.log('\n=== Test 2: Browser → Vite Proxy (5173) ===');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 10000 });
    const r2 = await page.evaluate(async () => {
        try {
            const resp = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: 'hello', use_rag: true, enable_thinking: true }),
            });
            return { status: resp.status, ok: resp.ok, text: (await resp.text()).substring(0, 200) };
        } catch (e) {
            return { error: e.message };
        }
    });
    console.log(JSON.stringify(r2, null, 2));

    await browser.close();
})();
