"""FunASR 语音识别服务 — 支持热词"""
import logging
import os
import tempfile
import threading

logger = logging.getLogger(__name__)

_model = None
_model_loading = False
_model_ready = False
_hotwords = []

def _load_model():
    global _model, _model_loading, _model_ready
    _model_loading = True
    try:
        from funasr import AutoModel
        logger.info("FunASR: downloading/loading model (may take 1-2 min first time)...")
        _model = AutoModel(
            model="paraformer-zh",
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            device="cpu",
        )
        _model_ready = True
        logger.info("FunASR: model ready")
    except Exception as e:
        logger.error(f"FunASR load failed: {e}")
        _model = None
    _model_loading = False

# 后台线程预热模型
threading.Thread(target=_load_model, daemon=True).start()

def get_model():
    return _model

def is_ready():
    return _model_ready

def is_loading():
    return _model_loading

async def speech_to_text(audio_bytes: bytes, hotwords: list[str] = None) -> str:
    """语音转文字 + 热词增强"""
    if not _model_ready:
        if _model_loading:
            return "[模型加载中，请稍后重试...]"
        return "[语音识别模型加载失败，请检查 PyTorch + FunASR 安装]"

    model = _model
    if model is None:
        return "[语音识别模型未就绪]"

    # 写入临时文件
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        kwargs = {}
        if hotwords:
            kwargs["hotword"] = " ".join(hotwords)
        result = model.generate(input=tmp_path, **kwargs)
        if result and len(result) > 0:
            text = result[0].get("text", "")
            return text.strip()
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
    """添加全局热词"""
    global _hotwords
    _hotwords = list(set(_hotwords + words))

def get_hotwords() -> list[str]:
    return list(_hotwords)
