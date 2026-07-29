import { Filter, ScanSearch, ScrollText, TriangleAlert } from "lucide-react";
import type { ActivitiesStats } from "../../shared/activities";

type StatsPanelProps = {
  stats: ActivitiesStats;
};

const cards = [
  {
    key: "scannedCount",
    label: "抓取通告数",
    icon: ScanSearch,
  },
  {
    key: "publishDateEligibleCount",
    label: "发布时间合规",
    icon: Filter,
  },
  {
    key: "titleCandidateCount",
    label: "进入详情判定",
    icon: ScrollText,
  },
  {
    key: "matchedCount",
    label: "最终展示",
    icon: TriangleAlert,
  },
] as const;

export default function StatsPanel({ stats }: StatsPanelProps) {
  return (
    <section className="stats-grid" aria-label="统计概览">
      {cards.map(({ key, label, icon: Icon }) => (
        <article className="stats-card" key={key}>
          <div className="stats-card__icon">
            <Icon size={18} />
          </div>
          <span>{label}</span>
          <strong>{stats[key]}</strong>
        </article>
      ))}
    </section>
  );
}
