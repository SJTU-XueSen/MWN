import { useEffect, useRef, useState } from "react";
import { Calendar, Clock, MapPin, Plus, Send, Trash2, User, X } from "lucide-react";
import { useStudentActivityStore } from "@/hooks/useStudentActivityStore";
import { useUserStore } from "@/hooks/useUserStore";

export default function StudentActivityPage() {
  const { items, fetchAll, submit, remove } = useStudentActivityStore();
  const user = useUserStore((s) => s.user);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [location, setLocation] = useState("");
  const [organizer, setOrganizer] = useState("");
  const [contact, setContact] = useState("");
  const [showForm, setShowForm] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;
    const timeRange = time && endTime ? `${time} - ${endTime}` : time || endTime || "";
    const fullDate = date && timeRange ? `${date} ${timeRange}` : date || timeRange;
    await submit({ title, description, date: fullDate, location, organizer, contact });
    setTitle("");
    setDescription("");
    setDate("");
    setTime("");
    setEndTime("");
    setLocation("");
    setOrganizer("");
    setContact("");
    setShowForm(false);
  };

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div>
          <span className="hero-badge">学生自发</span>
          <h1>学生自主活动</h1>
          <p>由学生自行发起、组织的活动。填写信息即可发布，与其他同学分享。</p>
        </div>
        <button
          className="refresh-button"
          type="button"
          onClick={() => {
            if (!user) return;
            const opening = !showForm;
            setShowForm(opening);
            if (opening) {
              setOrganizer(user.realName || user.nickname);
              setContact(user.contact);
              setTimeout(() => titleRef.current?.focus(), 100);
            }
          }}
          style={!user ? { opacity: 0.5, cursor: "not-allowed" } : undefined}
          title={!user ? "请先登录" : undefined}
        >
          {showForm ? <X size={16} /> : <Plus size={16} />}
          {showForm ? "取消" : "发布活动"}
        </button>
      </section>

      {showForm && (
        <form className="memo-form" style={{ flexDirection: "column" }} onSubmit={handleSubmit}>
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
              placeholder="活动内容（必填）"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", background: "rgba(255,255,255,0.8)" }}>
              <Calendar size={15} style={{ color: "rgba(16,33,60,0.5)", flexShrink: 0 }} />
              <input
                type="date"
                style={{ border: 0, background: "transparent", outline: "none", font: "inherit", flex: 1, color: date ? "#10213c" : "rgba(16,33,60,0.36)" }}
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", background: "rgba(255,255,255,0.8)" }}>
                <Clock size={15} style={{ color: "rgba(16,33,60,0.5)", flexShrink: 0 }} />
                <input
                  type="time"
                  style={{ border: 0, background: "transparent", outline: "none", font: "inherit", flex: 1, color: time ? "#10213c" : "rgba(16,33,60,0.36)" }}
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", background: "rgba(255,255,255,0.8)" }}>
                <Clock size={15} style={{ color: "rgba(16,33,60,0.5)", flexShrink: 0 }} />
                <input
                  type="time"
                  style={{ border: 0, background: "transparent", outline: "none", font: "inherit", flex: 1, color: endTime ? "#10213c" : "rgba(16,33,60,0.36)" }}
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                />
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", background: "rgba(255,255,255,0.8)" }}>
                <MapPin size={15} style={{ color: "rgba(16,33,60,0.5)", flexShrink: 0 }} />
                <input
                  type="text"
                  style={{ border: 0, background: "transparent", outline: "none", font: "inherit", flex: 1, color: "#10213c" }}
                  placeholder="活动地点"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", background: "rgba(16,33,60,0.04)" }}>
                <User size={15} style={{ color: "rgba(16,33,60,0.5)", flexShrink: 0 }} />
                <input
                  type="text"
                  readOnly
                  style={{ border: 0, background: "transparent", outline: "none", font: "inherit", flex: 1, color: "#10213c" }}
                  placeholder="主办人"
                  value={organizer}
                />
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 12, border: "1px solid rgba(16,33,60,0.12)", background: "rgba(16,33,60,0.04)" }}>
              <Send size={15} style={{ color: "rgba(16,33,60,0.5)", flexShrink: 0 }} />
              <input
                type="text"
                readOnly
                style={{ border: 0, background: "transparent", outline: "none", font: "inherit", flex: 1, color: "#10213c" }}
                placeholder="联系方式"
                value={contact}
              />
            </div>
          </div>
          <button type="submit" className="search-submit" disabled={!title.trim() || !description.trim()} style={{ alignSelf: "flex-end" }}>
            <Send size={16} />
            发布
          </button>
        </form>
      )}

      {items.length > 0 && (
        <section style={{ marginTop: 20 }}>
          <div className="section-title">
            <div>
              <span>活动列表</span>
              <h2>共 {items.length} 场学生自主活动</h2>
            </div>
          </div>
          <div className="activity-list">
            {items.map((item) => (
              <article key={item.id} className="rec-card">
                <div className="rec-card__body">
                  <h3>{item.title}</h3>
                  <p>{item.description}</p>
                  <div className="rec-card__meta" style={{ flexWrap: "wrap" }}>
                    {item.date && (
                      <span className="rec-meta-item">
                        <span className="rec-meta-label"><Clock size={12} style={{ marginRight: 4 }} />时间</span>
                        <strong>{item.date}</strong>
                      </span>
                    )}
                    {item.location && (
                      <span className="rec-meta-item">
                        <span className="rec-meta-label"><MapPin size={12} style={{ marginRight: 4 }} />地点</span>
                        <strong>{item.location}</strong>
                      </span>
                    )}
                    {item.organizer && (
                      <span className="rec-meta-item">
                        <span className="rec-meta-label"><User size={12} style={{ marginRight: 4 }} />主办</span>
                        <strong>{item.organizer}</strong>
                      </span>
                    )}
                    {item.contact && (
                      <span className="rec-meta-item">
                        <span className="rec-meta-label"><Send size={12} style={{ marginRight: 4 }} />联系</span>
                        <strong>{item.contact}</strong>
                      </span>
                    )}
                  </div>
                </div>
                <div className="rec-card__actions">
                  <button
                    className="pill confirm-button"
                    type="button"
                    onClick={() => void remove(item.id)}
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

      {!showForm && items.length === 0 && (
        <div className="empty-state" style={{ marginTop: 20 }}>
          <h3>暂无学生自主活动</h3>
          <p>
            {user
              ? "点击上方\"发布活动\"按钮，发起你的第一个学生活动。"
              : "请先在导航栏点击\"登录\"填写个人信息，即可发布活动。"}
          </p>
        </div>
      )}
    </main>
  );
}
