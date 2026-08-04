"""FunASR 语音识别服务 — 支持热词持久化（data/stt_hotwords.json）"""
import json as _json
import logging
import os
import tempfile
import threading

from backend.config import BASE_DIR

logger = logging.getLogger(__name__)

_HOTWORDS_FILE = BASE_DIR / "data" / "stt_hotwords.json"

_model = None
_model_loading = False
_model_ready = False
_hotwords: list[str] = []


def _load_hotwords():
    global _hotwords
    try:
        if _HOTWORDS_FILE.exists():
            with open(_HOTWORDS_FILE, "r", encoding="utf-8") as f:
                _hotwords = _json.load(f)
    except Exception:
        pass


def _save_hotwords():
    try:
        _HOTWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_HOTWORDS_FILE, "w", encoding="utf-8") as f:
            _json.dump(_hotwords, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"保存热词失败: {e}")


_load_hotwords()


def _load_model():
    global _model, _model_loading, _model_ready
    _model_loading = True
    try:
        from funasr import AutoModel

        logger.info("FunASR: 加载模型（首次可能需要 1-2 分钟下载）...")
        _model = AutoModel(
            model="paraformer-zh",
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            device="cpu",
        )
        _model_ready = True
        logger.info("FunASR: 模型就绪")
    except Exception as e:
        logger.error(f"FunASR 加载失败: {e}")
        _model = None
    _model_loading = False


# 后台线程预热模型
threading.Thread(target=_load_model, daemon=True).start()


def is_ready() -> bool:
    return _model_ready


def is_loading() -> bool:
    return _model_loading


async def speech_to_text(audio_bytes: bytes, hotwords: list[str] = None) -> str:
    """语音转文字 + 热词增强"""
    if not _model_ready:
        if _model_loading:
            return "[模型加载中，请稍后重试...]"
        return "[语音识别模型加载失败，请检查 PyTorch + FunASR 安装]"
    if _model is None:
        return "[语音识别模型未就绪]"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        kwargs = {}
        if hotwords:
            kwargs["hotword"] = " ".join(hotwords)
        result = _model.generate(input=tmp_path, **kwargs)
        if result and len(result) > 0:
            return str(result[0].get("text", "")).strip()
        return ""
    except Exception as e:
        logger.error(f"STT error: {e}")
        return f"[识别失败: {str(e)[:50]}]"
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def add_hotwords(words: list[str]):
    """添加全局热词并持久化"""
    global _hotwords
    _hotwords = list(set(_hotwords + words))
    _save_hotwords()


def get_hotwords() -> list[str]:
    return list(_hotwords)
