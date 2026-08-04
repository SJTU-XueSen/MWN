import { useEffect, useRef, useState } from "react";

/** 语音输入 — 录音 → /api/mirror/stt → 文本回填 */
export default function VoiceInput({ onText }: { onText: (text: string) => void }) {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    return () => {
      mediaRef.current?.stop();
    };
  }, []);

  async function toggle() {
    if (recording) {
      mediaRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setRecording(false);
        setBusy(true);
        try {
          const form = new FormData();
          form.append("audio", blob, "voice.webm");
          const resp = await fetch("/api/mirror/stt", {
            method: "POST",
            credentials: "include",
            body: form,
          });
          const data = await resp.json();
          if (data.ok && data.text && !data.text.startsWith("[")) {
            onText(data.text);
          }
        } catch {
          // 网络错误静默
        } finally {
          setBusy(false);
        }
      };
      recorder.start();
      mediaRef.current = recorder;
      setRecording(true);
    } catch {
      alert("无法访问麦克风，请检查权限");
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={busy}
      title={recording ? "点击结束录音" : "语音输入"}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 38,
        height: 38,
        borderRadius: 10,
        border: "1px solid var(--border)",
        background: recording ? "rgba(248,113,113,0.15)" : "var(--input-bg)",
        color: recording ? "#F87171" : "var(--text3)",
        cursor: "pointer",
        fontSize: "0.95rem",
      }}
    >
      {busy ? "⏳" : recording ? "⏹" : "🎤"}
    </button>
  );
}
