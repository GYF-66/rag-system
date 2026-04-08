import { mkdirSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');
const backendDir = path.join(repoRoot, 'backend');
const screenshotDir = path.join(frontendDir, 'test-results');
const screenshotPath = path.join(screenshotDir, 'demo-flow.png');
const viteCliPath = path.join(frontendDir, 'node_modules', 'vite', 'bin', 'vite.js');

const backendPortSeed = 8012;
const frontendPortSeed = 4273;
const firstQuery = '\u57f9\u517b\u76ee\u6807\u662f\u4ec0\u4e48';
const secondQuery = '\u6bd5\u4e1a\u8981\u6c42\u662f\u4ec0\u4e48';

mkdirSync(screenshotDir, { recursive: true });

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function pipeLogs(prefix, stream) {
  stream?.on('data', (chunk) => {
    const text = chunk.toString().trim();
    if (!text) {
      return;
    }

    for (const line of text.split(/\r?\n/)) {
      console.log(`[${prefix}] ${line}`);
    }
  });
}

async function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.on('error', () => resolve(false));
    server.listen(port, '127.0.0.1', () => {
      server.close(() => resolve(true));
    });
  });
}

async function findAvailablePort(startPort, attempts = 30) {
  for (let port = startPort; port < startPort + attempts; port += 1) {
    if (await isPortFree(port)) {
      return port;
    }
  }

  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      if (!address || typeof address === 'string') {
        server.close(() => reject(new Error('Failed to resolve an ephemeral port.')));
        return;
      }

      const { port } = address;
      server.close(() => resolve(port));
    });
  });
}

function startProcess(name, command, args, options = {}) {
  const child = spawn(command, args, {
    cwd: options.cwd,
    env: { ...process.env, ...options.env },
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: false,
    windowsHide: true,
  });

  pipeLogs(name, child.stdout);
  pipeLogs(name, child.stderr);
  return child;
}

async function stopProcess(child) {
  if (!child || child.exitCode !== null) {
    return;
  }

  if (process.platform === 'win32') {
    await new Promise((resolve) => {
      const killer = spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], {
        stdio: 'ignore',
        windowsHide: true,
      });
      killer.on('exit', () => resolve());
      killer.on('error', () => resolve());
    });
    await sleep(500);
    return;
  }

  child.kill('SIGTERM');
  await sleep(1500);

  if (child.exitCode === null) {
    child.kill('SIGKILL');
  }
}

async function waitForHttp(url, timeoutMs = 120000) {
  const start = Date.now();
  let lastError;

  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url, { method: 'GET' });
      if (response.ok) {
        return;
      }

      lastError = new Error(`Unexpected status ${response.status} for ${url}`);
    } catch (error) {
      lastError = error;
    }

    await sleep(1000);
  }

  throw lastError ?? new Error(`Timed out waiting for ${url}`);
}

async function launchBrowser() {
  try {
    return await chromium.launch({ headless: true, channel: 'chrome' });
  } catch (error) {
    console.warn(`[playwright] Falling back to bundled Chromium: ${error instanceof Error ? error.message : String(error)}`);
    return chromium.launch({ headless: true });
  }
}

const backendPort = await findAvailablePort(backendPortSeed);
const frontendPort = await findAvailablePort(frontendPortSeed);
const backendOrigin = `http://127.0.0.1:${backendPort}`;
const frontendOrigin = `http://127.0.0.1:${frontendPort}`;
const backendHealthUrl = `${backendOrigin}/health`;
const manualUrl = `${frontendOrigin}/manual`;

let backendProcess;
let frontendProcess;
let browser;
let page;
const consoleMessages = [];
const failedRequests = [];

try {
  backendProcess = startProcess(
    'backend',
    'python',
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(backendPort)],
    {
      cwd: backendDir,
      env: {
        PUBLIC_DEMO_MODE: 'true',
        MONGODB_URL: '',
        LLM_API_KEY: '',
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1',
      },
    },
  );

  await waitForHttp(backendHealthUrl, 60000);

  frontendProcess = startProcess(
    'frontend',
    process.execPath,
    [viteCliPath, '--host', '127.0.0.1', '--port', String(frontendPort), '--strictPort'],
    {
      cwd: frontendDir,
      env: {
        VITE_PUBLIC_DEMO_MODE: 'true',
        VITE_API_BASE_URL: backendOrigin,
      },
    },
  );

  await waitForHttp(manualUrl, 60000);

  browser = await launchBrowser();
  page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  page.on('console', (message) => {
    consoleMessages.push(`[${message.type()}] ${message.text()}`);
  });
  page.on('requestfailed', (request) => {
    const failure = request.failure();
    failedRequests.push(`${request.method()} ${request.url()} :: ${failure?.errorText ?? 'failed'}`);
  });

  await page.goto(manualUrl, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="manual-page"]', { timeout: 60000 });
  await page.waitForSelector('[data-testid="chat-input"]', { timeout: 60000 });
  await page.waitForFunction(
    () => document.querySelector('[data-testid="connection-status"]')?.getAttribute('data-connected') === 'true',
    null,
    { timeout: 60000 },
  );

  await page.getByTestId('chat-input').fill(firstQuery);
  await page.getByTestId('chat-send').click();
  await page.waitForSelector('[data-testid="answer-block"]', { timeout: 120000 });
  await page.waitForSelector('[data-testid="source-card"]', { timeout: 120000 });

  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="chat-input"]', { timeout: 60000 });

  const answerCountAfterReload = await page.locator('[data-testid="answer-block"]').count();
  if (answerCountAfterReload < 1) {
    throw new Error('Expected at least one answer block after reload.');
  }

  await page.getByTestId('chat-input').fill(secondQuery);
  await page.getByTestId('chat-send').click();
  await page.waitForFunction(
    (previousCount) => document.querySelectorAll('[data-testid="answer-block"]').length > previousCount,
    answerCountAfterReload,
    { timeout: 120000 },
  );
  await page.waitForSelector('[data-testid="source-card"]', { timeout: 120000 });

  await page.screenshot({ path: screenshotPath, fullPage: true });

  const finalAnswerCount = await page.locator('[data-testid="answer-block"]').count();
  const finalSourceCount = await page.locator('[data-testid="source-card"]').count();

  console.log(JSON.stringify({
    status: 'ok',
    frontendUrl: manualUrl,
    backendUrl: backendOrigin,
    screenshotPath,
    answerCount: finalAnswerCount,
    sourceCount: finalSourceCount,
  }, null, 2));
} catch (error) {
  const diagnostics = {
    manualUrl,
    backendHealthUrl,
    connectionStatus: page
      ? await page.locator('[data-testid="connection-status"]').getAttribute('data-connected').catch(() => null)
      : null,
    consoleMessages: consoleMessages.slice(-20),
    failedRequests: failedRequests.slice(-20),
  };

  console.error(JSON.stringify({
    status: 'failed',
    message: error instanceof Error ? error.message : String(error),
    diagnostics,
  }, null, 2));
  throw error;
} finally {
  if (browser) {
    await browser.close();
  }

  await stopProcess(frontendProcess);
  await stopProcess(backendProcess);
}
