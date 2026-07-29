import { CalendarRange, Link2, NotebookTabs, ScanText } from "lucide-react";
import type { ActivityItem } from "../../shared/activities";

type ActivityDetailPanelProps = {
  activity: ActivityItem | null;
};

export default function ActivityDetailPanel({ activity }: ActivityDetailPanelProps) {
  if (!activity) {
    return (
      <aside className="detail-panel detail-panel--empty">
        <p>左侧选中一条活动后，这里会展示时间判断依据和原文入口。</p>
      </aside>
    );
  }

  return (
    <aside className="detail-panel">
      <div className="detail-panel__header">
        <span className="pill pill--accent">已通过筛选</span>
        <h2>{activity.title}</h2>
      </div>

      <section className="detail-block">
        <h3>
          <CalendarRange size={17} />
          时间判断
        </h3>
        <p>{activity.decisionReason}</p>
        <ul className="date-list">
          {activity.extractedDates.map((date) => (
            <li key={date}>{date}</li>
          ))}
        </ul>
      </section>

      <section className="detail-block">
        <h3>
          <ScanText size={17} />
          学生相关性
        </h3>
        <p>{activity.relevanceReason}</p>
      </section>

      <section className="detail-block">
        <h3>
          <NotebookTabs size={17} />
          摘要
        </h3>
        <p>{activity.summary}</p>
      </section>

      <a className="detail-link" href={activity.url} target="_blank" rel="noreferrer">
        打开学校原始通告
        <Link2 size={16} />
      </a>
    </aside>
  );
}
