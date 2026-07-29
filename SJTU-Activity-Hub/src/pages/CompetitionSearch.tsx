import { useEffect, useRef } from "react";
import { ArrowRight, Bell, Globe, Loader2, School, Search, X } from "lucide-react";
import { useAiSearchStore, useNotificationStore } from "@/hooks/useNotificationStore";

function LoadingMessage() {
  return (
    <div className="ai-message ai-message--assistant">
      <div className="ai-typing-dots">
        <span />
        <span />
        <span />
      </div>
      <span className="ai-typing-text">AI 正在分析你的兴趣方向，匹配合适的竞赛活动...</span>
    </div>
  );
}

export default function CompetitionSearch() {
  const {
    query,
    reasoning,
    recommendations,
    campusCount,
    webCount,
    loading,
    searched,
    setQuery,
    search,
    reset,
  } = useAiSearchStore();

  const notificationStore = useNotificationStore();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void notificationStore.fetchNotifications();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    void search();
  };

  const handleConfirm = (item: typeof recommendations[number]) => {
    void notificationStore.confirmNotification(item);
  };

  const handleRemove = (id: string) => {
    void notificationStore.removeNotification(id);
  };

  const isAlreadyNotified = (id: string) =>
    notificationStore.notifications.some((n) => n.id === id);

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div>
          <span className="hero-badge">AI 智能匹配 + 联网搜索</span>
          <h1>竞赛活动智能检索</h1>
          <p>
            描述你感兴趣的领域或方向，AI 会先从上海交通大学通知公告中匹配，同时从互联网搜索相关竞赛官网，一并展示。
            确认后，推荐结果会同步通知到活动聚合页。
          </p>
        </div>
      </section>

      <section className="search-area">
        <form className="search-box" onSubmit={handleSearch}>
          <Search size={18} className="search-icon" />
          <input
            ref={inputRef}
            className="search-input"
            type="text"
            placeholder="例如：编程竞赛、数学建模、创新创业..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          {query && (
            <button
              type="button"
              className="search-clear"
              onClick={() => {
                setQuery("");
                inputRef.current?.focus();
              }}
            >
              <X size={16} />
            </button>
          )}
          <button type="submit" className="search-submit" disabled={loading || !query.trim()}>
            {loading ? <Loader2 size={16} className="spin" /> : <Search size={16} />}
            搜索
          </button>
        </form>
      </section>

      {loading && <LoadingMessage />}

      {searched && !loading && (
        <section className="ai-result">
          {recommendations.length > 0 && (
            <>
              <div className="section-title" style={{ marginTop: 20 }}>
                <div>
                  <span>推荐结果</span>
                  <h2>
                    共 {recommendations.length} 条推荐
                    {campusCount > 0 && <span className="source-tag source-tag--campus"><School size={12} />校内 {campusCount}</span>}
                    {webCount > 0 && <span className="source-tag source-tag--web"><Globe size={12} />互联网 {webCount}</span>}
                  </h2>
                </div>
              </div>

              <div className="recommendation-list">
                {recommendations.map((item) => {
                  const notified = isAlreadyNotified(item.id);
                  return (
                    <article key={item.id} className={`rec-card ${notified ? "rec-card--notified" : ""}`}>
                      <div className="rec-card__body">
                        <h3>
                          {item.title}
                          <span className={`source-tag source-tag--${item.source}`}>
                            {item.source === "campus" ? <><School size={11} />校内通告</> : <><Globe size={11} />互联网</>}
                          </span>
                        </h3>
                        <p>{item.summary.slice(0, 200)}</p>
                        <div className="rec-card__meta">
                          {item.publishDate && (
                            <span className="rec-meta-item">
                              <span className="rec-meta-label">发布时间</span>
                              <strong>{item.publishDate}</strong>
                            </span>
                          )}
                          {item.inferredEndDate && (
                            <span className="rec-meta-item">
                              <span className="rec-meta-label">截止日期</span>
                              <strong>{item.inferredEndDate}</strong>
                            </span>
                          )}
                        </div>
                        <p className="rec-match-reason">
                          匹配理由：{item.matchReason}
                        </p>
                      </div>
                      <div className="rec-card__actions">
                        <a className="pill" href={item.url} target="_blank" rel="noopener noreferrer">
                          查看原文
                        </a>
                        {notified ? (
                          <button
                            className="pill pill--accent"
                            type="button"
                            onClick={() => handleRemove(item.id)}
                          >
                            <X size={14} />
                            取消通知
                          </button>
                        ) : (
                          <button
                            className="pill confirm-button"
                            type="button"
                            onClick={() => handleConfirm(item)}
                          >
                            <Bell size={14} />
                            确认通知
                          </button>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            </>
          )}

          {recommendations.length === 0 && (
            <div className="empty-state">
              <h3>暂无匹配结果</h3>
              <p>请尝试输入竞赛完整名称（如"ICPC 国际大学生程序设计竞赛""挑战杯全国大学生课外学术科技作品竞赛""全国大学生数学建模竞赛"），而非简短关键词。</p>
            </div>
          )}

          <div className="search-actions">
            <button className="pill" type="button" onClick={() => void reset()}>
              重新搜索
            </button>
          </div>
        </section>
      )}

      {!loading && !searched && (
        <section className="search-hint">
          <div className="hint-card">
            <span>使用建议</span>
            <ul>
              <li>输入竞赛完整名称效果最佳，如"ICPC""挑战杯""全国大学生数学建模竞赛"</li>
              <li>也可以描述方向如"人工智能相关竞赛""创新创业比赛"</li>
              <li>AI 会分析你的意图，从全校通知中筛选合适竞赛</li>
              <li>确认后，竞赛信息会同步通知到活动聚合首页</li>
            </ul>
          </div>
        </section>
      )}

      {notificationStore.notifications.length > 0 && (
        <section className="notification-preview">
          <div className="section-title">
            <div>
              <span>已确认通知</span>
              <h2>共 {notificationStore.notifications.length} 条已通知竞赛</h2>
            </div>
            <span className="section-tip">
              这些通知已同步到首页
              <ArrowRight size={15} />
            </span>
          </div>
          <div className="notification-mini-list">
            {notificationStore.notifications.slice(0, 5).map((n) => (
              <div key={n.id} className="notification-mini-item">
                <Bell size={14} />
                <span>{n.title}</span>
                <button
                  type="button"
                  className="notification-mini-remove"
                  onClick={() => handleRemove(n.id)}
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
