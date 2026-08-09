import importlib


def test_prompts_use_consistent_research_scenario(capsys):
    prompts = importlib.import_module("agent.prompts")
    importlib.reload(prompts)

    rendered = str(prompts.prompt_yaml_content)
    assert set(prompts.sub_agents_content) == {"zhihu", "db"}
    assert "空调" not in rendered
    assert "药品" not in rendered
    assert "知乎" in rendered
    assert "live/demo" in rendered
    assert capsys.readouterr().out == ""
