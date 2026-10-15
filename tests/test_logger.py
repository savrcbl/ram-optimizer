import logging

import config
import logger as logger_mod


def test_logger_writes_file_in_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    name = "ram_optimizer_test"
    logging.getLogger(name).handlers.clear()
    lg = logger_mod.get_logger(name)
    lg.info("hello")
    for h in lg.handlers:
        h.flush()
    assert (config.get_config_dir() / "ram_optimizer.log").exists()


def test_no_duplicate_handlers(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    name = "ram_optimizer_test2"
    logging.getLogger(name).handlers.clear()
    logger_mod.get_logger(name)
    logger_mod.get_logger(name)
    assert len(logging.getLogger(name).handlers) == 1
