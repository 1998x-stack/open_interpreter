"""
tests/test_config.py — 配置模块单元测试
"""

import os
import sys
import pytest
from pathlib import Path

# 确保导入路径正确
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


@pytest.fixture(autouse=True)
def reset_config_cache():
    """每个测试前后重置 lru_cache"""
    from src.open_interpreter.config import reset_config
    reset_config()
    yield
    reset_config()


class TestSettings:

    def test_default_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("OPENAI_MODEL", raising=False)

        from src.open_interpreter.config import get_config
        cfg = get_config()
        assert cfg.openai_model == "gpt-4o"

    def test_custom_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-3.5-turbo")

        from src.open_interpreter.config import get_config
        cfg = get_config()
        assert cfg.openai_model == "gpt-3.5-turbo"

    def test_custom_base_url(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://my-proxy.example.com/v1")

        from src.open_interpreter.config import get_config
        cfg = get_config()
        assert cfg.openai_base_url == "https://my-proxy.example.com/v1"

    def test_auto_run_true(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("AUTO_RUN", "true")

        from src.open_interpreter.config import get_config
        cfg = get_config()
        assert cfg.auto_run is True

    def test_auto_run_variations(self, monkeypatch):
        """AUTO_RUN 接受 true/yes/1/on"""
        from src.open_interpreter.config import _parse_bool
        for truthy in ("true", "True", "TRUE", "1", "yes", "on"):
            assert _parse_bool(truthy) is True
        for falsy in ("false", "0", "no", "off", ""):
            assert _parse_bool(falsy) is False

    def test_debug_mode_default_false(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("DEBUG_MODE", raising=False)

        from src.open_interpreter.config import get_config
        cfg = get_config()
        assert cfg.debug_mode is False

    def test_max_output_chars(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("MAX_OUTPUT_CHARS", "5000")

        from src.open_interpreter.config import get_config
        cfg = get_config()
        assert cfg.max_output_chars == 5000

    def test_validate_raises_on_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        from src.open_interpreter.config import Settings
        settings = Settings(openai_api_key="")
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            settings.validate()

    def test_validate_passes_with_api_key(self, monkeypatch):
        from src.open_interpreter.config import Settings
        settings = Settings(openai_api_key="sk-valid-key")
        settings.validate()  # should not raise

    def test_lru_cache_singleton(self, monkeypatch):
        """同一进程中两次 get_config() 应返回同一对象"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        from src.open_interpreter.config import get_config
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2

    def test_temperature_default(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("TEMPERATURE", raising=False)

        from src.open_interpreter.config import get_config
        cfg = get_config()
        assert cfg.temperature == pytest.approx(0.01)

    def test_temperature_custom(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("TEMPERATURE", "0.7")

        from src.open_interpreter.config import get_config
        cfg = get_config()
        assert cfg.temperature == pytest.approx(0.7)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])