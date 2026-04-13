import { mkdirSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { execFile, spawn } from 'node:child_process';
import { promisify } from 'node:util';

import { chromium } from 'playwright';

const execFileAsync = promisify(execFile);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');
const backendDir = path.join(repoRoot, 'backend');
const screenshotDir = path.join(frontendDir, 'test-results');
const screenshotPath = path.join(screenshotDir, 'demo-flow.png');
const chatQuestion = '\u4eba\u5de5\u667a\u80fd\u4e13\u4e1a\u7684\u6838\u5fc3\u8bfe\u7a0b\u4e0e\u5b9e\u8df5\u73af\u8282\u5982\u4f55\u5b89\u6392\uff1f\u8bf7\u5206\u6bb5\u8bf4\u660e\u3002';
const testUsername = `u${Date.now().toString().slice(-8)}`;
const testPassword = 'Demo1234';
const testNickname = '\u6f14\u793a\u7528\u6237';

mkdirSync(screenshotDir, { recursive: true });

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function toWindowsCommand(command, args) {
  const quote = (value) => (value.includes(' ') ? `"${value}"` : value);
  return [command, ...args].map(quote).join(' ');
}

function getFreePort(preferredPort) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();

    const listen = (port) => {
      server.listen(port, '127.0.0.1');
    };

    server.on('error', (error) => {
      if (preferredPort && error.code === 'EADDRINUSE') {
        preferredPort = 0;
        listen(0);
        return;
      }
      reject(error);
    });

    server.on('listening', () => {
      const address = server.address();
      if (!address || typeof address === 'string') {
        reject(new Error('Unable to determine free port'));
        return;
      }
      const { port } = address;
      server.close(() => resolve(port));
    });

    listen(preferredPort);
  });
}

async function waitForHttp(url, timeoutMs = 120000) {
  const start = Date.now();
  let lastError;

  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
      lastError = new Error(`Unexpected status ${response.status} for ${url}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(1000);
  }

  throw lastError ?? new Error(`Timed out waiting for ${url}`);
}

async function registerDemoUser(baseUrl) {
  const start = Date.now();
  let lastError;

  while (Date.now() - start < 120000) {
    try {
      const response = await fetch(`${baseUrl}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          username: testUsername,
          password: testPassword,
          nickname: testNickname,
        }),
      });

      if (response.ok) return response.json();

      const errorBody = await response.text();
      lastError = new Error(`Register failed: ${response.status} ${errorBody}`);
      if (response.status >= 400 && response.status < 500) throw lastError;
    } catch (error) {
      lastError = error;
    }

    await sleep(1000);
  }

  throw lastError ?? new Error('Timed out registering demo user');
}

async function createDemoSpace(baseUrl) {
  const response = await fetch(`${baseUrl}/api/v1/spaces`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      name: '\u4eba\u5de5\u667a\u80fd\u4e13\u4e1a\u77e5\u8bc6\u7a7a\u95f4',
      description: '\u7528\u4e8e\u5168\u8def\u7531\u622a\u56fe\u56de\u5f52\u7684\u6f14\u793a\u7a7a\u95f4\u3002',
      icon: 'fa-solid fa-book-open-reader',
      color: 'text-amber-600',
    }),
  });

  if (!response.ok) {
    throw new Error(`Create space failed: ${response.status} ${await response.text()}`);
  }

  return response.json();
}

function startProcess(command, args, options = {}) {
  let spawnCommand = command;
  let spawnArgs = args;

  if (process.platform === 'win32') {
    spawnCommand = process.env.ComSpec || 'cmd.exe';
    spawnArgs = ['/d', '/s', '/c', toWindowsCommand(command, args)];
  }

  const child = spawn(spawnCommand, spawnArgs, {
    cwd: options.cwd,
    env: { ...process.env, ...options.env },
    shell: false,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  child.stdout?.on('data', (chunk) => process.stdout.write(`[${options.name}] ${chunk}`));
  child.stderr?.on('data', (chunk) => process.stderr.write(`[${options.name}] ${chunk}`));

  return child;
}

async function stopProcess(child) {
  if (!child || child.exitCode !== null) return;

  if (process.platform === 'win32') {
    try {
      await execFileAsync('taskkill', ['/pid', String(child.pid), '/t', '/f']);
    } catch {
      child.kill('SIGKILL');
    }
    await sleep(1500);
    return;
  }

  child.kill('SIGTERM');
  await sleep(1500);
  if (child.exitCode === null) child.kill('SIGKILL');
}

async function captureRoute(page, baseUrl, descriptor) {
  await page.goto(`${baseUrl}${descriptor.path}`, { waitUntil: 'networkidle' });
  if (descriptor.waitFor) {
    await page.waitForSelector(descriptor.waitFor, { timeout: 60000 });
  }
  const filePath = path.join(screenshotDir, `${descriptor.name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  return filePath;
}

async function createAuthenticatedContext(browser, authData) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  await context.addInitScript(({ accessToken, refreshToken, user }) => {
    window.localStorage.setItem('auth_access_token', accessToken);
    window.localStorage.setItem('auth_refresh_token', refreshToken);
    window.localStorage.setItem('auth_user', JSON.stringify(user));
  }, {
    accessToken: authData.access_token,
    refreshToken: authData.refresh_token,
    user: authData.user,
  });
  return context;
}

async function exerciseManualFlow(page, baseUrl) {
  const result = { degraded: false, reason: null };

  await page.goto(`${baseUrl}/manual`, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="manual-page"]', { timeout: 60000 });
  await page.waitForSelector('[data-testid="chat-input"]', { timeout: 60000 });

  try {
    const initialAnswers = await page.locator('[data-testid="answer-block"]').count();
    await page.getByTestId('chat-input').fill(chatQuestion);
    await page.getByTestId('chat-send').click();

    await page.waitForFunction(
      (expected) => document.querySelectorAll('[data-testid="answer-block"]').length > expected,
      initialAnswers,
      { timeout: 30000 },
    );

    await page.waitForFunction(
      () => Boolean(
        document.querySelector('[data-testid="thinking-process"]')
        || document.querySelector('[data-testid="trace-status"]')
        || document.querySelector('[data-testid="streaming-cursor"]'),
      ),
      { timeout: 30000 },
    );

    await page.waitForSelector('[data-testid="source-card"]', { timeout: 30000 });

    result.hasThinkingPanel = await page.locator('[data-testid="thinking-process"]').count() > 0;
    result.hasTraceStatus = await page.locator('[data-testid="trace-status"]').count() > 0;
  } catch (error) {
    result.degraded = true;
    result.reason = error instanceof Error ? error.message : 'manual flow degraded';
  }

  await page.screenshot({ path: screenshotPath, fullPage: true });
  return result;
}

const backendPort = await getFreePort(8011);
const frontendPort = await getFreePort(4173);
const backendUrl = `http://127.0.0.1:${backendPort}/health`;
const frontendUrl = `http://127.0.0.1:${frontendPort}`;

let backendProcess;
let frontendProcess;
let browser;

try {
  backendProcess = startProcess('python', ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(backendPort)], {
    cwd: backendDir,
    env: {
      PUBLIC_DEMO_MODE: 'true',
      ENVIRONMENT: 'development',
    },
    name: 'backend',
  });

  frontendProcess = startProcess('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(frontendPort), '--strictPort'], {
    cwd: frontendDir,
    env: {
      VITE_PUBLIC_DEMO_MODE: 'true',
      VITE_API_BASE_URL: `http://127.0.0.1:${frontendPort}`,
      VITE_PROXY_TARGET: `http://127.0.0.1:${backendPort}`,
    },
    name: 'frontend',
  });

  await waitForHttp(backendUrl);
  await waitForHttp(frontendUrl);

  const authData = await registerDemoUser(frontendUrl);
  const demoSpace = await createDemoSpace(frontendUrl);

  browser = await chromium.launch({ headless: true });

  const guestContext = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const guestPage = await guestContext.newPage();

  const authContext = await createAuthenticatedContext(browser, authData);
  const authPage = await authContext.newPage();

  const screenshots = [];

  screenshots.push(await captureRoute(guestPage, frontendUrl, { name: 'route-home', path: '/', waitFor: '.landing-title' }));
  screenshots.push(await captureRoute(guestPage, frontendUrl, { name: 'route-login', path: '/login', waitFor: '.auth-form' }));
  screenshots.push(await captureRoute(guestPage, frontendUrl, { name: 'route-register', path: '/register', waitFor: '.auth-form' }));

  const manualFlow = await exerciseManualFlow(authPage, frontendUrl);
  screenshots.push(path.join(screenshotDir, 'demo-flow.png'));
  screenshots.push(await captureRoute(authPage, frontendUrl, { name: 'route-manual', path: '/manual', waitFor: '[data-testid="manual-page"]' }));
  screenshots.push(await captureRoute(authPage, frontendUrl, { name: 'route-history', path: '/history', waitFor: 'main' }));
  screenshots.push(await captureRoute(authPage, frontendUrl, { name: 'route-spaces', path: '/spaces', waitFor: 'main' }));
  screenshots.push(await captureRoute(authPage, frontendUrl, { name: 'route-finance', path: '/finance', waitFor: 'main' }));
  screenshots.push(await captureRoute(authPage, frontendUrl, { name: 'route-space-detail', path: `/space/${demoSpace.id}`, waitFor: 'main' }));
  screenshots.push(await captureRoute(guestPage, frontendUrl, { name: 'route-not-found', path: '/this-route-does-not-exist', waitFor: 'main' }));

  await guestContext.close();
  await authContext.close();

  console.log(JSON.stringify({
    status: 'ok',
    screenshotPath,
    screenshots,
    frontendUrl,
    backendUrl,
    testUsername,
    demoSpaceId: demoSpace.id,
    degradedManualFlow: manualFlow.degraded,
    degradedReason: manualFlow.reason,
    hasThinkingPanel: manualFlow.hasThinkingPanel ?? false,
    hasTraceStatus: manualFlow.hasTraceStatus ?? false,
  }, null, 2));
} finally {
  if (browser) {
    await browser.close();
  }
  await stopProcess(frontendProcess);
  await stopProcess(backendProcess);
}
