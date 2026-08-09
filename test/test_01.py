from api.server import app


def test_api_application_title():
    assert app.title == "DeepAgents API"
