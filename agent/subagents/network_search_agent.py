# 目标： 创建网络搜索子智能体
# 方式1： dict -> deepagents  方式： compiledSubAgent -> langchain langgraph
from agent.prompts import sub_agents_content
from tools.zhihu_search_tool import internet_search


network_search_agent = {
    "name":sub_agents_content['zhihu']['name'],
    "description":sub_agents_content['zhihu']['description'],
    "system_prompt":sub_agents_content['zhihu']['system_prompt'],
    "tools":[internet_search]
}
