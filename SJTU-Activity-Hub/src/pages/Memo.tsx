import { useEffect, useRef, useState } from "react";
import { Calendar, Plus, StickyNote, Trash2, X } from "lucide-react";
import { useMemoStore } from "@/hooks/useMemoStore";

export default function MemoPage() {
  const { memos, fetchMemos, addMemo, removeMemo } = useMemoStore();
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [deadline, setDeadline] = useState("");
  const [showForm, setShowForm] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void fetchMemos();
  }, [fetchMemos]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    await addMemo(title, note, deadline);
    setTitle("");
    setNote("");
    setDeadline("");
    setShowForm(false);
  };

  const formatDate = (d: string) => {
    if (!d) return "";
    return d.replace(/T.*/, "");
  };

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div>
          <span className="hero-badge">个人工具</span>
          <h1>我的备忘录</h1>
          <p>记录你计划参加的竞赛活动，随时查看和管理。</p>
        </div>
        <button
          className="refresh-button"
          type="button"
          onClick={() => {
            setShowForm(!showForm);
            if (!showForm) setTimeout(() => titleRef.current?.focus(), 100);
          }}
        >
          {showForm ? <X size={16} /> : <Plus size={16} />}
          {showForm ? "取消" : "新建备忘"}
        </button>
      </section>

      {showForm && (
        <form className="memo-form" onSubmit={handleSubmit}>
          <div className="memo-form__fields">
            <input
              ref={titleRef}
              className="search-input"
              style={{ fontSize: "1rem", padding: "10px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", width: "100%" }}
              type="text"
              placeholder="活动名称（必填）"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <textarea
              className="search-input"
              style={{ fontSize: "0.95rem", padding: "10px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", width: "100%", minHeight: 80, resize: "vertical" }}
              placeholder="备注说明（可选）"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", background: "rgba(255,255,255,0.8)" }}>
              <Calendar size={16} style={{ color: "rgba(16,33,60,0.5)", flexShrink: 0 }} />
              <input
                type="date"
                style={{ border: 0, background: "transparent", outline: "none", font: "inherit", flex: 1, color: "#10213c" }}
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
              />
            </div>
          </div>
          <button type="submit" className="search-submit" disabled={!title.trim()}>
            <Plus size={16} />
            保存
          </button>
        </form>
      )}

      {memos.length > 0 && (
        <section style={{ marginTop: 20 }}>
          <div className="section-title">
            <div>
              <span>备忘列表</span>
              <h2>共 {memos.length} 条记录</h2>
            </div>
          </div>
          <div className="recommendation-list">
            {memos.map((memo) => (
              <article key={memo.id} className="rec-card">
                <div className="rec-card__body">
                  <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <StickyNote size={16} style={{ color: "#8b1e2b" }} />
                    {memo.title}
                  </h3>
                  {memo.note && <p>{memo.note}</p>}
                  <div className="rec-card__meta">
                    {memo.deadline && (
                      <span className="rec-meta-item">
                        <span className="rec-meta-label">截止日期</span>
                        <strong>{formatDate(memo.deadline)}</strong>
                      </span>
                    )}
                    <span className="rec-meta-item">
                      <span className="rec-meta-label">创建时间</span>
                      <strong>{formatDate(memo.createdAt)}</strong>
                    </span>
                  </div>
                </div>
                <div className="rec-card__actions">
                  <button
                    className="pill confirm-button"
                    type="button"
                    onClick={() => void removeMemo(memo.id)}
                  >
                    <Trash2 size={14} />
                    删除
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {!showForm && memos.length === 0 && (
        <div className="empty-state" style={{ marginTop: 20 }}>
          <h3>暂无备忘</h3>
          <p>点击上方"新建备忘"按钮，记录你计划参加的活动。</p>
        </div>
      )}
    </main>
  );
}
