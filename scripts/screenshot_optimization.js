// -*- coding: utf-8 -*-
/**
 * 优化效果截屏脚本 v2
 * 展示 BGE-M3 + Adaptive Router + Thinking Process + 教育角色
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const OUTPUT = path.resolve(__dirname, '..', 'output');
const BASE = 'http://localhost:5173';

if (!fs.existsSync(OUTPUT)) fs.mkdirSync(OUTPUT, { recursive: true });

const QUERIES = [
    { label: 'simple', query: '什么是人工智能' },
    { label: 'standard', query: '人工智能专业有哪些实践环节和实习要求' },
    { label: 'complex', query: '请比较机器学习和深度学习课程的培养目标差异，分析课程衔接关系' },
];

(async () => {
    const browser = await chromium.launch({ headless: true });
    const ctx = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 2,
    });

    try {
        // ── 截屏 0: 首页 ──
        const homePage = await ctx.newPage();
        await homePage.goto(BASE, { waitUntil: 'networkidle', timeout: 15000 });
        await homePage.waitForTimeout(2000);
        await homePage.screenshot({ path: path.join(OUTPUT, 'opt_00_homepage.png') });
        console.log('✅ 首页截屏完成');
        await homePage.close();

        // ── 逐查询截屏 ──
        for (let i = 0; i < QUERIES.length; i++) {
            const { label, query } = QUERIES[i];
            const page = await ctx.newPage();
            console.log(`\n▶ [${label.toUpperCase()}] ${query}`);

            // 捕获控制台错误
            page.on('console', msg => {
                if (msg.type() === 'error') console.log(`  [console.error] ${msg.text().substring(0, 120)}`);
            });
            page.on('requestfailed', req => {
                console.log(`  [req-fail] ${req.url().substring(0, 80)} → ${req.failure()?.errorText}`);
            });

            await page.goto(`${BASE}/manual`, { waitUntil: 'networkidle', timeout: 15000 });
            await page.waitForTimeout(2000);

            // 找输入框并填入
            const textarea = page.locator('textarea').first();
            await textarea.click();
            await textarea.fill(query);
            // 触发 Vue v-model 更新
            await textarea.dispatchEvent('input');
            await page.waitForTimeout(500);

            // 发送前截屏
            await page.screenshot({ path: path.join(OUTPUT, `opt_0${i + 1}a_${label}_before.png`) });

            // 检查发送按钮状态
            const sendBtn = page.locator('[data-testid="chat-send"]');
            const isDisabled = await sendBtn.isDisabled();
            console.log(`  发送按钮状态: ${isDisabled ? 'disabled' : 'enabled'}`);

            if (!isDisabled) {
                // 设置请求捕获
                const responsePromise = page.waitForResponse(
                    r => r.url().includes('/api/chat') && r.status() === 200,
                    { timeout: 120000 }
                );
                await sendBtn.click();
                console.log('  已点击发送, 等待后端响应...');

                try {
                    const resp = await responsePromise;
                    console.log(`  ✅ 后端返回 ${resp.status()}`);
                } catch {
                    console.log('  ⚠️ 等待响应超时 (120s)');
                }
            } else {
                // 按钮被禁用，尝试用 Enter 发送
                console.log('  按钮禁用，尝试 Enter 发送...');
                await textarea.press('Enter');
                await page.waitForTimeout(30000);
            }

            // 等待渲染
            await page.waitForTimeout(4000);

            // 尝试展开思考过程面板
            try {
                const thinkBtn = page.locator('button:has-text("思考过程")').first();
                await thinkBtn.waitFor({ state: 'visible', timeout: 5000 });
                await thinkBtn.click();
                await page.waitForTimeout(500);
                console.log('  思考过程已展开');
            } catch {
                console.log('  (无思考过程面板或未找到)');
            }

            // 响应后截屏
            await page.screenshot({
                path: path.join(OUTPUT, `opt_0${i + 1}b_${label}_response.png`),
                fullPage: true,
            });
            console.log(`  ✅ [${label}] 截屏完成`);
            await page.close();
        }

        // ── 教育角色差异化截屏（多视角模式）──
        console.log('\n▶ [PERSPECTIVE] 教育角色差异化（多视角模式）');
        const perspPage = await ctx.newPage();
        await perspPage.goto(`${BASE}/manual`, { waitUntil: 'networkidle', timeout: 15000 });
        await perspPage.waitForTimeout(1500);

        // 尝试开启多视角模式
        try {
            const toggle = perspPage.locator('[data-testid="perspective-toggle"]').first();
            await toggle.waitFor({ state: 'visible', timeout: 5000 });
            await toggle.click();
            await perspPage.waitForTimeout(300);
            console.log('  多视角模式已开启');
        } catch {
            console.log('  (未找到多视角开关)');
        }

        const perspTextarea = perspPage.locator('textarea, [data-testid="chat-input"], input[type="text"]').first();
        await perspTextarea.click();
        await perspTextarea.fill('机器学习课程的教学内容和学习路径是什么？');
        await perspPage.waitForTimeout(300);

        const perspSend = perspPage.locator('[data-testid="chat-send"], button[type="submit"], button:has-text("发送")').first();
        await perspSend.click();
        console.log('  发送完毕, 等待多视角响应...');

        try {
            await perspPage.waitForResponse(
                r => r.url().includes('/api/chat') && r.status() === 200,
                { timeout: 120000 }
            );
        } catch {
            console.log('  ⚠️ 多视角 API 超时');
        }
        await perspPage.waitForTimeout(4000);
        await perspPage.screenshot({
            path: path.join(OUTPUT, 'opt_04_perspective.png'),
            fullPage: true,
        });
        console.log('  ✅ 多视角截屏完成');
        await perspPage.close();

        console.log('\n============================');
        console.log('所有截屏已保存到 output/ 目录');
        console.log('============================');

    } catch (err) {
        console.error('截屏失败:', err.message);
    } finally {
        await browser.close();
    }
})();
