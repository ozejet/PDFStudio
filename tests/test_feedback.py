import json
import webbrowser

import pytest

from pdfstudio.app import create_app
from pdfstudio.feedback import Feedback, form_url


@pytest.mark.parametrize("host", ["forms.office.com", "forms.cloud.microsoft", "forms.microsoft.com"])
def test_response_links_are_normalized_for_embedding(host):
    result = form_url(f"https://{host}/Pages/ResponsePage.aspx?id=synthetic&embed=false&lang=en-US")
    assert result == f"https://{host}/Pages/ResponsePage.aspx?id=synthetic&lang=en-US&embed=true"
    assert form_url(result) == result


@pytest.mark.parametrize("url", [
    "http://forms.office.com/Pages/ResponsePage.aspx?id=x",
    "https://forms.office.com.evil.example/Pages/ResponsePage.aspx?id=x",
    "https://evil.example/Pages/ResponsePage.aspx?id=x",
    "https://forms.office.com:444/Pages/ResponsePage.aspx?id=x",
    "https://user:password@forms.office.com/Pages/ResponsePage.aspx?id=x",
    "https://forms.office.com/Pages/DesignPageV2.aspx?id=x",
    "https://forms.office.com/Pages/ResponsePage.aspx",
    "https://forms.office.com/Pages/ResponsePage.aspx?id=x#fragment",
    "https://forms.office.com/Pages/ResponsePage.aspx?id=x\n",
    None, [], {"url": "example"},
])
def test_untrusted_links_and_editor_pages_are_rejected(url):
    with pytest.raises(ValueError):
        form_url(url)


def test_device_settings_override_bundle_and_can_be_cleared(tmp_path):
    bundle = tmp_path / "bundled.json"
    bundle.write_text(json.dumps({"url": "https://forms.office.com/r/Synthetic"}))
    settings = Feedback(tmp_path, bundle)
    assert settings.read()["url"].endswith("/r/Synthetic?embed=true")
    saved = settings.update({"url": "https://forms.cloud.microsoft/Pages/ResponsePage.aspx?id=test"})
    assert Feedback(tmp_path, bundle).read() == saved
    assert settings.update({"url": ""}) == {"url": ""}
    assert Feedback(tmp_path, bundle).read() == {"url": ""}
    assert not list(tmp_path.glob("*.tmp"))
    with pytest.raises(ValueError):
        settings.update({"url": "", "recipient": "unneeded"})


def test_invalid_settings_fall_back_without_breaking_document_startup(tmp_path):
    (tmp_path / "feedback-form.json").write_text("broken")
    assert Feedback(tmp_path).read() == {"url": ""}


def test_feedback_api_requires_authentication_and_preserves_workspace(tmp_path, monkeypatch):
    app = create_app(tmp_path, testing=True)
    try:
        client = app.test_client()
        token = {"X-Studio-Token": app.config["STUDIO_TOKEN"]}
        assert client.get("/api/feedback/settings").status_code == 403
        assert client.post("/api/feedback/settings", json={"url": ""}).status_code == 403
        assert client.post("/api/feedback/settings", headers=token, json={"url": ""}).status_code == 200
        assert client.post("/api/feedback/open", headers=token, json={}).status_code == 400
        before = client.get("/api/config", headers=token).json
        result = client.post("/api/feedback/settings", headers=token, json={"url": "https://forms.office.com/Pages/ResponsePage.aspx?id=synthetic"})
        assert result.status_code == 200
        after = client.get("/api/config", headers=token).json
        assert before["documents"] == after["documents"]
        assert before["preferences"] == after["preferences"]
        assert after["feedback"] == result.json
        calls = []
        monkeypatch.setattr(webbrowser, "open", lambda url, **kwargs: calls.append(url) or True)
        assert client.post("/api/feedback/open", headers=token, json={}).json == {"opened": True}
        assert calls == [result.json["url"]]
        assert client.post("/api/feedback/settings", headers=token, json={"url": "https://evil.example/"}).status_code == 400
        assert client.get("/api/feedback/settings", headers=token).json == result.json
        policy = client.get("/api/health").headers["Content-Security-Policy"]
        assert "frame-src 'self' https://forms.office.com" in policy
        assert "connect-src 'self'" in policy
        assert "frame-src *" not in policy
        assert client.post("/api/feedback/send", headers=token, json={}).status_code in (404, 405)
    finally:
        app.extensions["imports"].close()
        app.extensions["sources"].close()
        app.extensions["workspace"].close()
