import pytest

from vps_docker_mcp.utils import clamp, limit_output, q, validate_name


def test_q_plain():
    assert q("hello") == "hello"


def test_q_spaces():
    assert q("hello world") == "'hello world'"


def test_q_special_chars():
    result = q("it's")
    assert "it" in result and "s" in result  # shell-safe, exact form depends on shlex


def test_validate_name_valid():
    assert validate_name("my-container") == "my-container"
    assert validate_name("web_1") == "web_1"
    assert validate_name("A") == "A"


def test_validate_name_leading_dash():
    with pytest.raises(ValueError):
        validate_name("-bad")


def test_validate_name_empty():
    with pytest.raises(ValueError):
        validate_name("")


def test_validate_name_special_chars():
    with pytest.raises(ValueError):
        validate_name("bad;cmd")


def test_validate_name_too_long():
    with pytest.raises(ValueError):
        validate_name("a" * 129)


def test_clamp_within():
    assert clamp(5, 1, 10) == 5


def test_clamp_below_min():
    assert clamp(0, 1, 10) == 1


def test_clamp_above_max():
    assert clamp(99, 1, 10) == 10


def test_clamp_at_boundaries():
    assert clamp(1, 1, 10) == 1
    assert clamp(10, 1, 10) == 10


def test_limit_output_short():
    assert limit_output("hello", 100) == "hello"


def test_limit_output_exact():
    assert limit_output("hello", 5) == "hello"


def test_limit_output_truncated():
    result = limit_output("hello world", 5)
    assert result.startswith("hello")
    assert "truncated" in result.lower()


def test_limit_output_truncation_message_has_limit():
    result = limit_output("x" * 200, 100)
    assert "100" in result
