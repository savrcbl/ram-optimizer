import json

import pytest

import config


@pytest.fixture(autouse=True)
def fake_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_defaults_when_no_file():
    assert config.load_config() == config.DEFAULT_CONFIG


def test_load_does_not_create_file(fake_appdata):
    config.load_config()
    assert not config.get_config_path().exists()


def test_save_then_load_roundtrip():
    cfg = config.load_config()
    cfg["trim_threshold_percent"] = 90
    config.save_config(cfg)
    assert config.load_config()["trim_threshold_percent"] == 90


def test_save_creates_folder(fake_appdata):
    config.save_config(dict(config.DEFAULT_CONFIG))
    assert config.get_config_path().exists()


def test_broken_json_returns_defaults():
    config.get_config_dir().mkdir(parents=True)
    config.get_config_path().write_text("{not json", encoding="utf-8")
    assert config.load_config() == config.DEFAULT_CONFIG


def test_missing_keys_filled_from_defaults():
    config.get_config_dir().mkdir(parents=True)
    config.get_config_path().write_text(json.dumps({"auto_mode": True}), encoding="utf-8")
    cfg = config.load_config()
    assert cfg["auto_mode"] is True
    assert cfg["cooldown_seconds"] == 120


def test_wrong_type_value_ignored():
    config.get_config_dir().mkdir(parents=True)
    config.get_config_path().write_text(
        json.dumps({"trim_threshold_percent": "high"}), encoding="utf-8"
    )
    assert config.load_config()["trim_threshold_percent"] == 85


def test_returned_dict_is_a_copy():
    a = config.load_config()
    a["trim_threshold_percent"] = 1
    assert config.load_config()["trim_threshold_percent"] == 85


def test_excluded_list_is_not_shared_between_loads():
    a = config.load_config()
    a["excluded_apps"].append("game.exe")
    assert config.load_config()["excluded_apps"] == []
    assert config.DEFAULT_CONFIG["excluded_apps"] == []


def test_excluded_list_roundtrip_and_non_strings_dropped():
    config.get_config_dir().mkdir(parents=True)
    config.get_config_path().write_text(
        json.dumps({"excluded_apps": ["game.exe", 5, None, "obs64.exe"]}), encoding="utf-8")
    assert config.load_config()["excluded_apps"] == ["game.exe", "obs64.exe"]
