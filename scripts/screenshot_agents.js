// -*- coding: utf-8 -*-
/**
 * 三视角 Agent 交互截屏脚本 (高品质版)
 * 2x 分辨率 · 元素级截取 · 推理步骤展开 · 逐 Tab 截屏
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const OUTPUT = path.resolve(__dirname, '..', 'output');
const BASE = 'http://localhost:5173';

if (!fs.existsSync(OUTPUT)) fs.mkdirSync(OUTPUT, { recursive: true });

(async () => {
    const browser = await chromium.launch({ headless: true });
    const ctx = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 2,  // 2x 高清截屏
    });
    const page = await ctx.newPage();

    page.on('console', msg => {
        if (msg.type() === 'error' && !msg.text().includes('service-worker'))
            console.log(`  [ERR] ${msg.text().substring(0, 150)}`);
    });

    try {
        // ── 1. 进入聊天页面 ──
        console.log('▶ 进入聊天页面...');
        await page.goto(`${BASE}/manual`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(2000);

        // ── 2. 开启多视角模式 ──
        console.log('▶ 开启多视角模式...');
        const perspectiveBtn = page.locator('[data-testid="perspective-toggle"]');
        await perspectiveBtn.click();
        await page.waitForTimeout(500);
        console.log(`  按钮: ${await perspectiveBtn.textContent()}`);

        // ── 3. 填入问题 ──
        const question = '机器学习课程的教学内容和学习路径是什么？';
        console.log(`▶ 发送: ${question}`);
        const textarea = page.locator('[data-testid="chat-input"]');
        await textarea.click();
        await textarea.fill(question);
        await page.waitForTimeout(300);

        // ── 截屏 0: 发送前状态 ──
        await page.screenshot({ path: path.join(OUTPUT, 'agent_00_before_send.png') });
        console.log('  ✅ 发送前截屏');

        // ── 4. 点发送 + 等待 API ──
        const sendBtn = page.locator('[data-testid="chat-send"]');
        const responsePromise = page.waitForResponse(
            r => r.url().includes('/api/chat/perspectives') && r.status() === 200,
            { timeout: 180000 }
        );
        await sendBtn.click();
        console.log('▶ 等待 API 响应...');
        const resp = await responsePromise;
        console.log(`  ✅ API ${resp.status()}`);

        // 等待 Vue 渲染 + Markdown 解析
        await page.waitForTimeout(4000);

        // ── 截屏 1: 全页面响应 ──
        await page.screenshot({ path: path.join(OUTPUT, 'agent_01_full_response.png'), fullPage: true });
        console.log('  ✅ 全页面截屏');

        // ── 5. 定位视角容器 ──
        const container = page.locator('.perspective-container');
        try {
            await container.waitFor({ state: 'visible', timeout: 10000 });
        } catch {
            console.log('  ⚠️ 视角容器未出现，保存调试截屏');
            await page.screenshot({ path: path.join(OUTPUT, 'agent_debug.png'), fullPage: true });
            return;
        }

        const allTabs = container.locator('button').filter({ hasNotText: '▶' });
        const tabCount = await allTabs.count();
        console.log(`▶ 检测到 ${tabCount} 个视角 Tab`);

        const tabLabels = ['student', 'teacher', 'admin'];

        for (let i = 0; i < Math.min(tabCount, 3); i++) {
            const tab = allTabs.nth(i);
            const tabText = (await tab.textContent()).trim();
            const label = tabLabels[i] || `tab${i}`;
            console.log(`\n── 视角 ${i + 1}: ${tabText} ──`);

            // 切换 Tab
            await tab.click();
            await page.waitForTimeout(1500);

            // 展开推理步骤（如果有 ▶ 按钮）
            const stepsToggle = container.locator('button').filter({ hasText: '推理步骤' });
            if (await stepsToggle.count() > 0) {
                await stepsToggle.click();
                await page.waitForTimeout(500);
                console.log('  → 推理步骤已展开');
            }

            // 滚动到视角容器
            await container.scrollIntoViewIfNeeded();
            await page.waitForTimeout(300);

            // ── 单视角截屏（元素级） ──
            await container.screenshot({
                path: path.join(OUTPUT, `agent_${label}_element.png`),
            });
            console.log(`  ✅ agent_${label}_element.png (元素级)`);

            // ── 单视角截屏（带上下文的窗口级） ──
            await page.screenshot({
                path: path.join(OUTPUT, `agent_${label}_page.png`),
            });
            console.log(`  ✅ agent_${label}_page.png (窗口级)`);

            // 收起推理步骤（为下一个 Tab 重置）
            if (await stepsToggle.count() > 0) {
                const isExpanded = await container.locator('.rotate-90').count() > 0;
                if (isExpanded) {
                    await stepsToggle.click();
                    await page.waitForTimeout(200);
                }
            }
        }

        // ── 6. 最终全页面总览 ──
        // 切回第一个 Tab 显示完整状态
        if (tabCount > 0) await allTabs.nth(0).click();
        await page.waitForTimeout(1000);

        await page.screenshot({
            path: path.join(OUTPUT, 'agent_final_overview.png'),
            fullPage: true,
        });
        console.log('\n  ✅ agent_final_overview.png');

        console.log(`\n🎉 高品质截屏完成！共 ${2 + tabCount * 2 + 1} 张，保存在 output/`);

    } catch (err) {
        console.error('❌ 错误:', err.message);
        await page.screenshot({ path: path.join(OUTPUT, 'agent_error.png') });
    } finally {
        await browser.close();
    }
})();
