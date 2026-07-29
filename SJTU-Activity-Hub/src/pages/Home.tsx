import { useEffect, useState } from "react";
import { ArrowRight, Bell, Calendar, ChevronDown, ChevronUp, Globe, RefreshCw, School, StickyNote, X } from "lucide-react";
import ActivityCard from "@/components/ActivityCard";
import ActivityDetailPanel from "@/components/ActivityDetailPanel";
import Empty from "@/components/Empty";
import { useActivitiesStore } from "@/hooks/useActivitiesStore";
import { useDismissedStore } from "@/hooks/useDismissedStore";
import { useMemoStore } from "@/hooks/useMemoStore";
import { useNotificationStore } from "@/hooks/useNotificationStore";

function formatDateLabel(date: string | undefined) {
  return date ? date.replace(/-/g, ".") : "当前日期";
}

function LoadingCards() {
  return (
    <div className="loading-grid" aria-hidden="true">
      {Array.from({ length: 4 }, (_, index) => (
        <div className="loading-card" key={index} />
      ))}
    </div>
  );
}

export default function Home() {
  const { data, error, loading, selectedId, fetchActivities, selectActivity } = useActivitiesStore();
  const { notifications, fetchNotifications, removeNotification } = useNotificationStore();
  const { memos, fetchMemos, removeMemo } = useMemoStore();
  const { dismiss, restore, isDismissed } = useDismissedStore();
  const [showDismissed, setShowDismissed] = useState(false);

  useEffect(() => {
    void fetchActivities();
    void fetchNotifications();
    void fetchMemos();
  }, [fetchActivities, fetchNotifications, fetchMemos]);

  const allItems = data?.items ?? [];
  const activeItems = allItems.filter((item) => !isDismissed(item.id));
  const dismissedItems = allItems.filter((item) => isDismissed(item.id));
  const selectedActivity = data?.items.find((item) => item.id === selectedId) ?? null;
  const asOfDateLabel = formatDateLabel(data?.asOfDate);

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div>
          <span className="hero-badge">按当前日期筛选：{asOfDateLabel}</span>
          <h1>上海交大学生活动通告聚合页</h1>
          <p>
            汇聚上海交通大学通告网中面向学生且仍在进行中的活动信息。
          </p>
        </div>
        <button className="refresh-button" type="button" onClick={() => void fetchActivities()}>
          <RefreshCw size={16} />
          刷新
        </button>
      </section>

      {notifications.length > 0 && (
        <section className="notification-bar">
          <div className="notification-bar__header">
            <Bell size={16} />
            <h2>AI 推荐通知（{notifications.length}）</h2>
            <span className="notification-bar__tip">来自竞赛智能检索的确认结果</span>
          </div>
          <div className="notification-bar__list">
            {notifications.map((n) => (
              <div key={n.id} className="notification-item">
                <div className="notification-item__info">
                  <strong>
                    {n.title}
                    <span className={`source-tag source-tag--${n.source || "campus"}`}>
                      {n.source === "web" ? <><Globe size={10} />互联网</> : <><School size={10} />校内</>}
                    </span>
                  </strong>
                  <span>检索词：{n.studentQuery}</span>
                </div>
                <a className="pill" href={n.url} target="_blank" rel="noopener noreferrer">
                  查看原文
                </a>
                <button
                  type="button"
                  className="notification-item__remove"
                  onClick={() => void removeNotification(n.id)}
                  aria-label="移除通知"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {memos.length > 0 && (
        <section className="notification-bar">
          <div className="notification-bar__header">
            <StickyNote size={16} />
            <h2>我的备忘（{memos.length}）</h2>
            <span className="notification-bar__tip">计划参加的活动记录</span>
          </div>
          <div className="notification-bar__list">
            {memos.map((m) => (
              <div key={m.id} className="notification-item">
                <div className="notification-item__info">
                  <strong>{m.title}</strong>
                  <span>
                    {m.deadline && <><Calendar size={10} style={{ marginRight: 4 }} />{m.deadline.replace(/T.*/, "")} </>}
                    {m.note && `— ${m.note.slice(0, 40)}${m.note.length > 40 ? "..." : ""}`}
                  </span>
                </div>
                <button
                  type="button"
                  className="notification-item__remove"
                  onClick={() => void removeMemo(m.id)}
                  aria-label="删除备忘"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {error ? (
        <Empty title="抓取失败" description={`接口暂时没拿到数据：${error}`} />
      ) : null}

      {loading && !data ? <LoadingCards /> : null}

      {data && !data.items.length ? (
        <Empty
          title="没有符合条件的活动"
          description="当前暂无面向学生且仍在进行中的活动。"
        />
      ) : null}

      {data && activeItems.length > 0 ? (
        <section className="content-grid">
          <div className="cards-column">
            <div className="section-title">
              <div>
                <span>活动列表</span>
                <h2>共 {activeItems.length} 条可展示活动</h2>
              </div>
              <span className="section-tip">
                点击卡片查看详情
                <ArrowRight size={15} />
              </span>
            </div>
            <div className="activity-list">
              {activeItems.map((activity) => (
                <ActivityCard
                  key={activity.id}
                  activity={activity}
                  selected={activity.id === selectedId}
                  onSelect={selectActivity}
                  onDismiss={dismiss}
                />
              ))}
            </div>
          </div>
          <ActivityDetailPanel activity={selectedActivity} />
        </section>
      ) : null}

      {data && activeItems.length === 0 && allItems.length > 0 && (
        <Empty
          title="活动已全部折叠"
          description="所有活动已被折叠，请在下方已折叠区域展开。"
        />
      )}

      {dismissedItems.length > 0 && (
        <section className="dismissed-section" style={{ marginTop: 20 }}>
          <button
            className="dismissed-toggle"
            type="button"
            onClick={() => setShowDismissed(!showDismissed)}
          >
            {showDismissed ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            已折叠的活动（{dismissedItems.length}）
          </button>
          {showDismissed && (
            <div className="activity-list" style={{ marginTop: 12 }}>
              {dismissedItems.map((activity) => (
                <ActivityCard
                  key={activity.id}
                  activity={activity}
                  selected={activity.id === selectedId}
                  onSelect={selectActivity}
                  onRestore={restore}
                  dismissed
                />
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
