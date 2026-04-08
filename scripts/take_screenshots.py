"""Take screenshots of the frontend application for demo purposes."""
from playwright.sync_api import sync_playwright
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output', 'screenshots')
os.makedirs(OUTPUT_DIR, exist_ok=True)

PAGES = [
    ('home', 'http://localhost:5173/', '首页'),
    ('manual', 'http://localhost:5173/manual', '工作台'),
    ('login', 'http://localhost:5173/login', '登录页'),
    ('register', 'http://localhost:5173/register', '注册页'),
    ('history', 'http://localhost:5173/history', '历史记录'),
    ('spaces', 'http://localhost:5173/spaces', '知识空间'),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})

    for name, url, label in PAGES:
        print(f'Capturing {label} ({url})...')
        page.goto(url)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(1500)

        path = os.path.join(OUTPUT_DIR, f'{name}.png')
        page.screenshot(path=path, full_page=True)
        print(f'  Saved to {path}')

    # Test actual chat interaction on the manual page
    print('Capturing 工作台-联调问答...')
    page.goto('http://localhost:5173/manual')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1500)

    # Check connection status
    status_el = page.locator('[data-testid="connection-status"]')
    if status_el.count() > 0:
        connected = status_el.get_attribute('data-connected')
        print(f'  Connection status: {connected}')

    # Type a question and send
    chat_input = page.locator('[data-testid="chat-input"]')
    if chat_input.count() > 0:
        chat_input.fill('人工智能专业的核心课程有哪些？')
        page.wait_for_timeout(500)
        # Screenshot with question typed
        page.screenshot(path=os.path.join(OUTPUT_DIR, 'manual_typed.png'))
        print('  Saved typed state')

        send_btn = page.locator('[data-testid="chat-send"]')
        if send_btn.count() > 0 and send_btn.is_enabled():
            send_btn.click()
            print('  Sent question, waiting for response...')
            # Wait for response (up to 60s)
            page.wait_for_timeout(3000)
            # Wait for loading to finish
            try:
                page.wait_for_function(
                    "() => !document.querySelector('[data-testid=\"chat-send\"]')?.textContent?.includes('生成中')",
                    timeout=90000
                )
            except Exception:
                print('  Response timed out, taking screenshot anyway')
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(OUTPUT_DIR, 'manual_response.png'), full_page=True)
            print('  Saved response state')

    # Mobile screenshots
    print('Capturing 首页-移动端...')
    mobile_page = browser.new_page(viewport={'width': 390, 'height': 844})
    mobile_page.goto('http://localhost:5173/')
    mobile_page.wait_for_load_state('networkidle')
    mobile_page.wait_for_timeout(1500)
    mobile_page.screenshot(path=os.path.join(OUTPUT_DIR, 'home_mobile.png'), full_page=True)
    print('  Saved')
    mobile_page.close()

    browser.close()
    print('All screenshots captured successfully!')
