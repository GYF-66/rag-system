import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { chromium } from 'playwright';

const rootDir = process.cwd();
const frontendDir = path.join(rootDir, 'frontend');
const backendDir = path.join(rootDir, 'backend');
const screenshotDir = path.join(frontendDir, 'test-results');
const screenshotPath = path.join(screenshotDir, 'demo-flow.png');

const backendPort = 8010;
const frontendPort = 5173;
const backendUrl = `http://127.0.0.1:${backendPort}`;
const frontendUrl = `http://127.0.0.1:${frontendPort}`;

const firstQuery = '\u57f9\u517b\u76ee\u6807\u662f\u4ec0\u4e48';
const secondQuery = '\u6bd5\u4e1a\u8981\u6c42\u662f\u4ec0\u4e48';

function commandName(base) {
  if (process.platform !== 'win32') {
    return base;
  }

  if (base === 'npm') {
    return 'npm.cmd';
  }

  return `${base}.exe`;
}

function log(prefix, chunk) {
  const text = chunk.toString().trim();
  if (!text) {
    return;
  }

  for (const line of text.split(/\r?\n/)) {
    console.log(`[${prefix}] ${line}`);
  }
}

function spawnProcess(name, command, args, cwd, extraEnv) {
  const child = spawn(command, args, {
    cwd,
    env: { ...process.env, ...extraEnv },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  child.stdout?.on('data', (chunk) => log(name, chunk));
  child.stderr?.on('data', (chunk) => log(name, chunk));

  return child;
}

async function isReachable(url) {
  try {
    const response = await fetch(url, { method: 'GET' });
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForHttp(url, timeoutMs) {
  const started = Date.now();

  while (Date.now() - started < timeoutMs) {
    if (await isReachable(url)) {
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw new Error(`Timed out waiting for ${url}`);
}

async function launchBrowser() {
  try {
    return await chromium.launch({ headless: true, channel: 'chrome' });
  } catch (error) {
    console.warn(`[playwright] Falling back to bundled Chromium: ${error instanceof Error ? error.message : String(error)}`);
    return chromium.launch({ headless: true });
  }
}

function terminate(child) {
  if (!child || child.killed) {
    return;
  }

  child.kill();
}

let backendChild = null;
let frontendChild = null;

try {
  await mkdir(screenshotDir, { recursive: true });

  if (!(await isReachable(`${backendUrl}/health`))) {
    backendChild = spawnProcess(
      'backend',
      commandName('python'),
      ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(backendPort)],
      backendDir,
      {
        PUBLIC_DEMO_MODE: 'true',
        MONGODB_URL: '',
        LLM_API_KEY: '',
        PYTHONIOENCODING: 'utf-8',
      },
    );
  }

  await waitForHttp(`${backendUrl}/health`, 60000);

  if (!(await isReachable(frontendUrl))) {
    frontendChild = spawnProcess(
      'frontend',
      commandName('npm'),
      ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(frontendPort)],
      frontendDir,
      {
        VITE_API_BASE_URL: backendUrl,
        VITE_PUBLIC_DEMO_MODE: 'true',
      },
    );
  }

  await waitForHttp(frontendUrl, 60000);

  const browser = await launchBrowser();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });

  await page.goto(frontendUrl, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="chat-input"]', { timeout: 30000 });

  await page.fill('[data-testid="chat-input"]', firstQuery);
  await page.click('[data-testid="send-button"]');
  await page.waitForSelector('[data-testid="answer-block"]', { timeout: 90000 });
  await page.waitForSelector('[data-testid="source-card"]', { timeout: 90000 });

  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="chat-input"]', { timeout: 30000 });

  const answerCountAfterReload = await page.locator('[data-testid="answer-block"]').count();
  if (answerCountAfterReload < 1) {
    throw new Error('Expected at least one answer block after reload.');
  }

  await page.fill('[data-testid="chat-input"]', secondQuery);
  await page.click('[data-testid="send-button"]');
  await page.waitForFunction(
    (previousCount) => document.querySelectorAll('[data-testid="answer-block"]').length > previousCount,
    answerCountAfterReload,
    { timeout: 90000 },
  );

  await page.waitForSelector('[data-testid="source-card"]', { timeout: 90000 });
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const finalAnswerCount = await page.locator('[data-testid="answer-block"]').count();
  const finalSourceCount = await page.locator('[data-testid="source-card"]').count();

  await browser.close();

  console.log(JSON.stringify({
    status: 'ok',
    frontendUrl,
    backendUrl,
    screenshotPath,
    answerCount: finalAnswerCount,
    sourceCount: finalSourceCount,
  }, null, 2));
} catch (error) {
  console.error(error instanceof Error ? error.stack : error);
  process.exitCode = 1;
} finally {
  terminate(frontendChild);
  terminate(backendChild);
}
