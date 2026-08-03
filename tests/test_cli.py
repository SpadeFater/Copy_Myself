from cli import format_response


def test_format_response_returns_assistant_line() -> None:
    output = format_response({"response": "收到"})

    assert output == "Copy_Myself: 收到"


def test_format_response_handles_missing_response() -> None:
    output = format_response({})

    assert output == "Copy_Myself: 暂无回复。"
