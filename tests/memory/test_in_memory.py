from memory import InMemoryStore


def test_memory_store_saves_and_searches_records() -> None:
    store = InMemoryStore()

    store.save("user", "明天上午提醒我复盘项目")
    store.save("assistant", "我会把提醒能力放进后续路线")

    results = store.search("提醒")

    assert results == [
        "user: 明天上午提醒我复盘项目",
        "assistant: 我会把提醒能力放进后续路线",
    ]


def test_memory_store_limits_search_results() -> None:
    store = InMemoryStore()
    store.save("user", "提醒 A")
    store.save("user", "提醒 B")
    store.save("user", "提醒 C")

    assert store.search("提醒", limit=2) == ["user: 提醒 B", "user: 提醒 C"]
