from tools.ragflow_tools import get_assistant_list


def test_ragflow_unconfigured_uses_demo_knowledge(monkeypatch):
    monkeypatch.setattr("tools.ragflow_tools.get_ragflow_client", lambda: (_ for _ in ()).throw(RuntimeError("unavailable")))

    result = get_assistant_list.invoke({})

    assert '"mode":"demo"' in result
    assert "RAGFLOW_UNAVAILABLE" in result
