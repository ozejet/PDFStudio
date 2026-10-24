"""Read-only check of the configured live form; never submit a response."""
import json
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
config = json.loads((root / 'web/public/feedback-form.json').read_text())
with sync_playwright() as runtime:
    browser = runtime.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 1050})
    failed = []
    console_errors = []
    page.on('console', lambda message: console_errors.append(message.text[:600]) if message.type == 'error' else None)
    page.on('requestfailed', lambda request: failed.append({'host': urlsplit(request.url).hostname, 'error': request.failure}))
    page.goto('http://127.0.0.1:43916')
    expect(page.get_by_role('button', name='Add files', exact=True)).to_be_enabled()
    token = page.request.get('http://127.0.0.1:43916/api/config').json()['token']
    result = page.request.post('http://127.0.0.1:43916/api/feedback/settings', headers={'X-Studio-Token': token}, data=config)
    assert result.ok
    page.reload()
    expect(page.get_by_role('button', name='Add files', exact=True)).to_be_enabled()
    assert page.locator('.feedback-panel').is_hidden()
    button = page.get_by_role('button', name='Feedback', exact=True)
    if button.count():
        button.click()
    else:
        page.get_by_role('button', name='Settings', exact=True).click()
        page.get_by_role('button', name='Share feedback', exact=True).click()
    frame = page.frame_locator('iframe[title="PDF Studio feedback — Microsoft Forms"]')
    frame.locator('body').wait_for(timeout=60000)
    for _ in range(20):
        content = frame.locator('body').inner_text(timeout=10000)
        if 'How would you rate' in content or 'Sign in' in content or 'permission' in content.lower():
            break
        page.wait_for_timeout(1000)
    page.screenshot(path=str(root / 'tmp/live-feedback-0.1.016.png'))
    print(json.dumps({
        'form_host': urlsplit(config['url']).hostname,
        'rating_question_visible': 'How would you rate' in content,
        'comment_question_visible': 'What would you like to share' in content,
        'feature_question_visible': 'Which feature did you use' in content,
        'sign_in_shown': 'Sign in' in content,
        'submitted': False,
        'failed_requests': failed[:8],
        'frame_text_length': len(content),
        'console_errors': console_errors[:5],
    }))
    browser.close()
