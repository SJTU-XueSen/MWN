export type ResultSource = "campus" | "web";

export type ConfirmedNotification = {
  id: string;
  title: string;
  url: string;
  publishDate: string;
  inferredEndDate: string | null;
  summary: string;
  confirmedAt: string;
  studentQuery: string;
  matchReason: string;
  source: ResultSource;
};

export type AiSearchRequest = {
  query: string;
};

export type AiSearchResponse = {
  recommendations: ConfirmedNotification[];
  campusCount: number;
  webCount: number;
  reasoning: string;
};
