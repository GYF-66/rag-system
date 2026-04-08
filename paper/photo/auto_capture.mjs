import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';

const baseUrl = 'http://127.0.0.1:4173';
const outDir = path.resolve('E:/项目/人工智能专业培养rag系统/paper/photo');

async function shot(page, route, filename, wait = 1500) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'networkidle' });
  await page.setViewportSize({ width: 1440, height: 1024 });
  await page.waitForTimeout(wait);
  await page.screenshot({ path: path.join(outDir, filename), fullPage: true });
}

const edgePaths = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
];

const executablePath = edgePaths.find((item) => existsSync(item));

const browser = await chromium.launch({
  headless: true,
  executablePath,
  channel: executablePath ? undefined : 'msedge',
});
const page = await browser.newPage();

await fs.mkdir(outDir, { recursive: true });

try {
  await shot(page, '/', '图2_系统首页.png');
  await shot(page, '/login', '图3_登录界面.png');
  await shot(page, '/manual', '图4_问答工作台.png');
  await shot(page, '/graph', '图5_知识图谱.png', 2500);
  console.log('截图完成');
} catch (error) {
  console.error('截图失败:', error);
  process.exitCode = 1;
} finally {
  await browser.close();
}
