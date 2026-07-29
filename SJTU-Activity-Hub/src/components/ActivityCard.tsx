import { CalendarDays, ChevronDown, ChevronUp, Clock3, ExternalLink, Sparkles } from "lucide-react";
import type { ActivityItem } from "../../shared/activities";

type ActivityCardProps = {
  activity: ActivityItem;
  selected: boolean;
  onSelect: (id: string) => void;
  onDismiss?: (id: string) => void;
  onRestore?: (id: string) => void;
  dismissed?: boolean;
};

export default function ActivityCard({ activity, selected, onSelect, onDismiss, onRestore, dismissed }: ActivityCardProps) {
  return (
    <article className={`activity-card${selected ? " is-selected" : ""}`}>
      <div className="activity-card__header">
        <span className="pill pill--accent">学生相关</span>
        <span className="pill">{activity.status === "ongoing" ? "未结束" : "未知"}</span>
        {onDismiss && !dismissed && (
          <button
            type="button"
            className="pill fold-btn"
            onClick={(e) => { e.stopPropagation(); onDismiss(activity.id); }}
            title="折叠此项"
          >
            <ChevronUp size={14} />
            折叠
          </button>
        )}
        {onRestore && dismissed && (
          <button
            type="button"
            className="pill fold-btn fold-btn--restore"
            onClick={(e) => { e.stopPropagation(); onRestore(activity.id); }}
            title="取消折叠"
          >
            <ChevronDown size={14} />
            展开
          </button>
        )}
      </div>
      <button className="activity-card__body" type="button" onClick={() => onSelect(activity.id)}>
        <h3>{activity.title}</h3>
        <p>{activity.summary}</p>
      </button>
      <dl className="activity-card__meta">
        <div>
          <dt>
            <CalendarDays size={16} />
            发布时间
          </dt>
          <dd>{activity.publishDate}</dd>
        </div>
        <div>
          <dt>
            <Clock3 size={16} />
            推断结束日
          </dt>
          <dd>{activity.inferredEndDate ?? "未识别"}</dd>
        </div>
      </dl>
      <div className="activity-card__footer">
        <div className="keyword-list">
          {activity.matchedKeywords.slice(0, 4).map((keyword) => (
            <span className="keyword" key={keyword}>
              <Sparkles size={14} />
              {keyword}
            </span>
          ))}
        </div>
        <a href={activity.url} target="_blank" rel="noreferrer">
          查看原文
          <ExternalLink size={15} />
        </a>
      </div>
    </article>
  );
}
