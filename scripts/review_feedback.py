"""Visual and interaction checks against an isolated, synthetic local session."""
from pathlib import Path
import fitz
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp/feedback-review-0.1.016"
OUT.mkdir(parents=True, exist_ok=True)
source = OUT / "team-handbook.pdf"
doc = fitz.open()
for index in range(3):
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(44, 44, 551, 50), fill=(.125, .212, .357), color=None)
    page.insert_text((44, 97), "Team handbook", fontsize=29, fontname="hebo", color=(.125, .212, .357))
    page.insert_text((44, 124), "A practical guide for everyday work", fontsize=14, color=(.3, .36, .43))
    page.insert_textbox(fitz.Rect(44, 155, 545, 225), "Prepare clear, useful documents for your team. Keep original files, check every exported page, and share the saved result with the right people.", fontsize=12, lineheight=1.7, color=(.2, .25, .3))
    page.insert_text((44, 261), "Getting started", fontsize=20, fontname="hebo", color=(.125, .212, .357))
    rows = [("Task", "Useful PDF Studio workflow"), ("Review a document", "Read, search and use Focus view"), ("Prepare a training pack", "Organize, reorder and combine pages"), ("Complete a form", "Edit / Fill, preview and save a copy"), ("Reuse table data", "Tools: export to Excel or CSV")]
    for row, (left, right) in enumerate(rows):
        y = 287 + row * 49
        page.draw_rect(fitz.Rect(44, y, 551, y + 49), fill=(.125, .212, .357) if row == 0 else (.97, .98, .99), color=(.75, .79, .84), width=.6)
        color = (1, 1, 1) if row == 0 else (.15, .2, .28)
        page.insert_text((56, y + 29), left, fontsize=11, color=color)
        page.insert_text((241, y + 29), right, fontsize=11, color=color)
    page.insert_text((44, 593), "Before sharing", fontsize=18, fontname="hebo", color=(.125, .212, .357))
    page.insert_textbox(fitz.Rect(44, 613, 545, 710), "Check page order, spelling and sensitive information. Use Redact content when information must be removed. Save your result before closing the application.", fontsize=12, lineheight=1.7, color=(.2, .25, .3))
    page.insert_text((44, 794), f"Synthetic training example  |  {index + 1} / 3", fontsize=9, color=(.4, .45, .5))
doc.save(source)
doc.close()

with sync_playwright() as runtime:
    browser = runtime.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 1050}, device_scale_factor=1)
    page.route('https://forms.office.com/**', lambda route: route.fulfill(status=200, content_type='text/html', body='<!doctype html><title>Synthetic form fixture</title><label>Test answer<textarea id="answer"></textarea></label>'))
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:43916")
    expect(page.get_by_role("button", name="Add files", exact=True)).to_be_enabled()
    initial = page.request.get('http://127.0.0.1:43916/api/config').json()
    token = initial['token']
    for document in initial['documents']:
        page.request.delete('http://127.0.0.1:43916/api/documents/' + document['id'], headers={'X-Studio-Token': token})
    page.request.post('http://127.0.0.1:43916/api/feedback/settings', headers={'X-Studio-Token': token}, data={'url': ''})
    page.reload()
    expect(page.get_by_role("button", name="Add files", exact=True)).to_be_enabled()
    page.locator('input[type="file"]').first.set_input_files(source)
    page.locator('.source.active').filter(has_text="team-handbook.pdf").wait_for()
    page.locator('.reader .pdf-page canvas').first.wait_for()
    page.wait_for_timeout(700)
    while page.locator('.toast-dismiss').count():
        page.locator('.toast-dismiss').first.click()
    page.screenshot(path=str(OUT / "studio-reader.png"))
    reader = page.locator('.reader').element_handle()
    page.get_by_role('button', name='Feedback', exact=True).click()
    page.get_by_role('heading', name='Feedback', exact=True).wait_for()
    assert page.locator('.feedback-preview').is_visible()
    assert page.locator('.forms-preview-submit').is_disabled()
    assert page.locator('iframe[title="PDF Studio feedback — Microsoft Forms"]').count() == 0
    assert page.evaluate('(reader)=>reader===document.querySelector(".reader")', reader)
    page.screenshot(path=str(OUT / "feedback-setup.png"))
    page.get_by_role('button', name='Close feedback', exact=True).click()
    assert page.get_by_role('button', name='Feedback', exact=True).evaluate('(button)=>button===document.activeElement')
    page.get_by_role('button', name='Settings', exact=True).click()
    if not page.get_by_role('textbox', name='Microsoft Forms response URL', exact=True).is_visible():
        page.get_by_text('Form connection', exact=True).click()
    field = page.get_by_role('textbox', name='Microsoft Forms response URL', exact=True)
    field.fill('https://evil.example/Pages/ResponsePage.aspx?id=synthetic')
    page.get_by_role('button', name='Save form link', exact=True).click()
    page.get_by_role('alert').filter(has_text='HTTPS response link').wait_for()
    field.fill('https://forms.office.com/Pages/ResponsePage.aspx?id=synthetic-test')
    page.get_by_role('button', name='Save form link', exact=True).click()
    page.get_by_role('status').filter(has_text='Form link saved.').wait_for()
    page.get_by_role('button', name='Done', exact=True).click()
    page.get_by_role('button', name='Feedback', exact=True).click()
    frame = page.frame_locator('iframe[title="PDF Studio feedback — Microsoft Forms"]')
    frame.locator('#answer').fill('Draft preserved across panel closure')
    page.get_by_role('button', name='Close feedback', exact=True).click()
    page.get_by_role('button', name='Feedback', exact=True).click()
    assert frame.locator('#answer').input_value() == 'Draft preserved across panel closure'
    page.get_by_role('button', name='Reload feedback form', exact=True).click()
    page.get_by_role('button', name='Keep current form', exact=True).click()
    assert frame.locator('#answer').input_value() == 'Draft preserved across panel closure'
    page.get_by_role('button', name='Close feedback', exact=True).click()
    page.get_by_role('button', name='Settings', exact=True).click()
    if not page.get_by_role('textbox', name='Microsoft Forms response URL', exact=True).is_visible():
        page.get_by_text('Form connection', exact=True).click()
    page.get_by_role('textbox', name='Microsoft Forms response URL', exact=True).fill('')
    page.get_by_role('button', name='Save form link', exact=True).click()
    page.get_by_role('status').filter(has_text='Form link saved.').wait_for()
    page.get_by_role('button', name='Done', exact=True).click()
    page.get_by_role('button', name='Feedback', exact=True).click()
    page.get_by_role('button', name='Use dark appearance', exact=True).click()
    page.screenshot(path=str(OUT / 'feedback-dark.png'))
    page.get_by_role('button', name='Use light appearance', exact=True).click()
    for width, height in [(375, 812), (812, 375), (1024, 768)]:
        page.set_viewport_size({"width": width, "height": height})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert page.locator('.feedback-panel').is_visible()
        expect(page.get_by_role('button', name='Feedback', exact=True)).to_be_visible()
        expect(page.get_by_role('button', name='Settings', exact=True)).to_be_visible()
        page.screenshot(path=str(OUT / f'feedback-{width}.png'))
    assert not errors, errors
    browser.close()
print("Feedback visual checks passed: reader preserved, settings validation, draft retention, reload cancellation, light/dark and three viewport sizes.")
