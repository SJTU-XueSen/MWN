export type ActivityStatus = "ongoing";

export type ActivityItem = {
  id: string;
  title: string;
  url: string;
  publishDate: string;
  matchedKeywords: string[];
  extractedDates: string[];
  inferredEndDate: string | null;
  summary: string;
  status: ActivityStatus;
  relevanceReason: string;
  decisionReason: string;
};

export type ActivitiesStats = {
  scannedCount: number;
  publishDateEligibleCount: number;
  titleCandidateCount: number;
  matchedCount: number;
  filteredByReason: Record<string, number>;
};

export type ActivitiesResponse = {
  asOfDate: string;
  source: "https://www.sjtu.edu.cn/tg";
  stats: ActivitiesStats;
  items: ActivityItem[];
};
