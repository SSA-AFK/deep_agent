"""Preserve public source URLs returned by research tools in final answers."""

import re


_URL_PATTERN = re.compile(r"https?://[^\s<>\"'\])}]+")
_SOURCE_REQUEST_MARKERS = ("来源", "链接", "公开信息", "公开资料")


def append_source_links(answer: str, message_contents: list[object]) -> str:
    """Append deduplicated tool-source links when the model omitted them."""
    urls: list[str] = []
    for content in message_contents:
        for url in _URL_PATTERN.findall(str(content)):
            if url not in urls and url not in answer:
                urls.append(url)
    if not urls:
        return answer
    return answer.rstrip() + "\n\n### 来源链接\n" + "\n".join(f"- {url}" for url in urls)


def requests_public_sources(query: str) -> bool:
    return any(marker in query for marker in _SOURCE_REQUEST_MARKERS)
