import { chromium } from 'playwright';
import { existsSync } from 'node:fs';
import path from 'node:path';

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
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
const svgPath = path.resolve('E:/项目/人工智能专业培养rag系统/paper/photo/图1_系统功能架构图.svg');
const outPath = path.resolve('E:/项目/人工智能专业培养rag系统/paper/photo/图1_系统功能架构图.png');
await page.goto(`file:///${svgPath.replace(/\\/g, '/')}`, { waitUntil: 'load' });
await page.screenshot({ path: outPath });
await browser.close();
console.log('FIG1_DONE');
