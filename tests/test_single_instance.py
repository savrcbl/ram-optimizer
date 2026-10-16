import single_instance


def test_always_true_off_windows(monkeypatch):
    monkeypatch.setattr(single_instance.sys, "platform", "linux")
    assert single_instance.acquire() is True
    assert single_instance.acquire() is True
