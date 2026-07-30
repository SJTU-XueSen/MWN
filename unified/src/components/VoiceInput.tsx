import { useState, useRef } from "react";

interface Props {
  onText: (text: string) => void;
  hotwords?: string;
  className?: string;
}

export default function VoiceInput({ onText, hotwords, className }: Props) {
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [modelReady, setModelReady] = useState<boolean | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  async function checkModel() {
    if (modelReady !== null) return modelReady;
    try {
      const r = await fetch("/api/mirror/stt/status");
      const d = await r.json();
      setModelReady(d.ready);
      return d.ready;
    } catch { return false; }
  }

  async function start() {
    const ready = await checkModel();
    if (!ready) { alert("语音模型加载中，请稍后再试"); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorder.current = mr;
      chunks.current = [];

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data);
      };

      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        if (chunks.current.length === 0) return;
        setLoading(true);
        const blob = new Blob(chunks.current, { type: "audio/webm" });
        const fd = new FormData();
        fd.append("audio", blob, "recording.webm");
        if (hotwords) fd.append("hotwords", hotwords);

        try {
          const r = await fetch("/api/mirror/stt", { method: "POST", body: fd });
          const d = await r.json();
          if (d.ok && d.text) onText(d.text);
        } catch {}
        setLoading(false);
      };

      mr.start();
      setRecording(true);
    } catch {
      alert("无法访问麦克风");
    }
  }

  function stop() {
    if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
      mediaRecorder.current.stop();
    }
    setRecording(false);
  }

  return (
    <button
      type="button"
      onClick={recording ? stop : start}
      disabled={loading}
      className={className}
      title={recording ? "停止录音" : "语音输入"}
      style={{
        width: 32, height: 32, borderRadius: "50%", border: "none", cursor: "pointer",
        display: "flex", alignItems: "center", justifyContent: "center",
        background: recording ? "#ef4444" : loading ? "var(--accent-bg3)" : "transparent",
        color: recording ? "#fff" : loading ? "var(--accent)" : "var(--text4)",
        fontSize: "1rem", transition: "all 0.15s",
      }}
    >
      {loading ? (
        <div style={{ width: 14, height: 14, border: "2px solid var(--accent)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.6s linear infinite" }} />
      ) : recording ? (
        <span>⏹</span>
      ) : (
        <span>🎤</span>
      )}
    </button>
  );
}
