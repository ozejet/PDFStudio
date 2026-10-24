from pdfstudio.app import create_app


def test_reminders_persist_across_launches_with_independent_defaults(tmp_path):
    data = tmp_path / "data"
    app = create_app(data, testing=True)
    headers = {"X-Studio-Token": app.config["STUDIO_TOKEN"]}
    client = app.test_client()
    assert all(client.get("/api/config", headers=headers).json["preferences"].values())
    saved = client.post("/api/preferences", headers=headers, json={"confirmQuit": False}).json
    assert not saved["confirmQuit"] and saved["confirmCloseDocument"] and saved["confirmRefreshPdf"]
    assert client.post("/api/preferences", headers=headers, json={"confirmQuit": "false"}).status_code == 400
    assert client.post("/api/preferences", headers=headers, json={"everything": False}).status_code == 400
    app.extensions["workspace"].close()
    another = create_app(data, testing=True)
    try:
        headers = {"X-Studio-Token": another.config["STUDIO_TOKEN"]}
        client = another.test_client()
        assert client.get("/api/config", headers=headers).json["preferences"] == saved
        assert client.post("/api/preferences", headers=headers, json=dict.fromkeys(saved, True)).json == dict.fromkeys(saved, True)
    finally:
        another.extensions["workspace"].close()


def test_invalid_preference_file_falls_back_to_reminders_enabled(tmp_path):
    from pdfstudio.preferences import Preferences
    preferences = Preferences(tmp_path)
    preferences.path.write_text("not valid JSON", encoding="utf-8")
    assert all(preferences.read().values())
