import dayjs, { type Dayjs } from "dayjs";

const strongStudentKeywords = [
  "本科生",
  "研究生",
  "留学生",
  "同学",
  "毕业生",
  "新生",
  "助教",
  "学员",
  "在校生",
  "学生",
];

const broadAudienceKeywords = ["同学们"];

const activityKeywords = [
  "活动",
  "报名",
  "招募",
  "征集",
  "参赛",
  "比赛",
  "竞赛",
  "大赛",
  "讲座",
  "论坛",
  "培训",
  "公开课",
  "献血",
  "招生",
  "典礼",
  "邀请函",
  "申请",
  "申报",
  "评选",
  "计划",
  "遴选",
];

const excludeKeywords = [
  "教职工",
  "教师",
  "妇科",
  "课题",
  "基金",
  "评审结果",
  "获奖名单",
  "公示",
  "工作安排",
  "调课安排",
];

export type DateMention = {
  value: string;
  isoDate: string;
  context: string;
  priority: number;
};

export type NoticeAnalysis = {
  isStudentRelated: boolean;
  matchedKeywords: string[];
  inferredEndDate: string | null;
  extractedDates: string[];
  relevanceReason: string;
  decisionReason: string;
};

function unique(items: string[]) {
  return Array.from(new Set(items));
}

function normalizeText(value: string) {
  return value
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .replace(/[ ]/g, " ")
    .trim();
}

function collectKeywordMatches(text: string, keywords: string[]) {
  return keywords.filter((keyword) => text.includes(keyword));
}

function getDatePriority(context: string) {
  if (/(截止|截至|报名截止|申报截止|申请截止|最后一天|最终|结束)/.test(context)) {
    return 4;
  }

  if (/(活动|举办|举行|典礼|培训|讲座|公开课|时间|日期|献血|报到)/.test(context)) {
    return 3;
  }

  if (/(开放|开始|启动|发布|公示)/.test(context)) {
    return 1;
  }

  return 2;
}

function parseDateMention(
  rawYear: string | undefined,
  month: string,
  day: string,
  fallbackYear: number,
  publishDate: string,
) {
  const year = rawYear ? Number(rawYear) : fallbackYear;
  let parsed = dayjs(`${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`);

  if (!parsed.isValid()) {
    return null;
  }

  if (!rawYear) {
    const publishDay = dayjs(publishDate);
    if (parsed.isBefore(publishDay.subtract(60, "day"))) {
      parsed = parsed.add(1, "year");
    }
  }

  return parsed;
}

export function extractDateMentions(text: string, publishDate: string): DateMention[] {
  const normalized = normalizeText(text);
  const publishYear = dayjs(publishDate).year();
  const pattern = /(?:(20\d{2})年)?\s*(\d{1,2})月\s*(\d{1,2})日/g;
  const mentions: DateMention[] = [];
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(normalized))) {
    const parsed = parseDateMention(match[1], match[2], match[3], publishYear, publishDate);

    if (!parsed) {
      continue;
    }

    const start = Math.max(0, match.index - 14);
    const end = Math.min(normalized.length, match.index + match[0].length + 14);
    const context = normalized.slice(start, end);

    mentions.push({
      value: match[0],
      isoDate: parsed.format("YYYY-MM-DD"),
      context,
      priority: getDatePriority(context),
    });
  }

  return mentions;
}

function inferEndDate(mentions: DateMention[], publishDate: string): Dayjs | null {
  if (!mentions.length) {
    return null;
  }

  const publishDay = dayjs(publishDate);
  const highPriorityMentions = mentions.filter((mention) => mention.priority >= 3);
  const candidateMentions = highPriorityMentions.length ? highPriorityMentions : mentions;
  const candidateDates = candidateMentions
    .map((mention) => dayjs(mention.isoDate))
    .filter((date) => date.isValid());

  if (!candidateDates.length) {
    return null;
  }

  const inferred = candidateDates.reduce((latest, current) =>
    current.isAfter(latest) ? current : latest,
  );

  const onlyPublishDate =
    candidateDates.length === 1 &&
    inferred.isSame(publishDay, "day") &&
    candidateMentions[0]?.priority < 3;

  if (onlyPublishDate) {
    return null;
  }

  return inferred;
}

export function buildSummary(text: string) {
  const normalized = normalizeText(text);
  return normalized.length > 140 ? `${normalized.slice(0, 140)}...` : normalized;
}

export function looksLikeTitleCandidate(title: string) {
  const normalized = normalizeText(title);
  const titleMatches = collectKeywordMatches(normalized, [
    ...strongStudentKeywords,
    ...broadAudienceKeywords,
    ...activityKeywords,
    "学生",
  ]);

  if (!titleMatches.length) {
    return false;
  }

  const excluded = collectKeywordMatches(normalized, excludeKeywords);
  return excluded.length < titleMatches.length;
}

export function analyzeNotice(title: string, body: string, publishDate: string): NoticeAnalysis {
  const normalizedTitle = normalizeText(title);
  const normalizedBody = normalizeText(body);
  const joinedText = `${normalizedTitle} ${normalizedBody}`;

  const strongMatches = collectKeywordMatches(joinedText, strongStudentKeywords);
  const audienceMatches = collectKeywordMatches(joinedText, broadAudienceKeywords);
  const activityMatches = collectKeywordMatches(joinedText, activityKeywords);
  const excludedMatches = collectKeywordMatches(joinedText, excludeKeywords);
  const targetedStudentMention =
    /学生/.test(normalizedTitle) ||
    /(全体学生|学生报名|学生参加|学生参与|学生申请|学生申报|学生提交|学生可|在校学生|面向[^。；，]{0,8}学生|欢迎[^。；，]{0,8}学生)/.test(
      joinedText,
    );

  // 教师/教职工活动信号：即使正文出现"学生"，若标题或内容明确指向教职工则排除
  const facultySignalPattern = /队伍建设|中青年骨干|党务工作|思政教育工作队伍|教职工队伍|干部培训|教师教学/;
  const hasFacultySignal =
    facultySignalPattern.test(normalizedTitle) ||
    (facultySignalPattern.test(joinedText) && !/学生/.test(normalizedTitle));

  const hasStudentAudience =
    strongMatches.length > 0 || targetedStudentMention;
  const hasActivitySignal = activityMatches.length > 0;
  const onlyTeacherAudience =
    /老师|教师/.test(joinedText) && strongMatches.length === 0 && !targetedStudentMention;

  const mentions = extractDateMentions(joinedText, publishDate);
  const inferredEnd = inferEndDate(mentions, publishDate);

  const isStudentRelated =
    !onlyTeacherAudience &&
    !hasFacultySignal &&
    hasActivitySignal &&
    hasStudentAudience &&
    !(excludedMatches.length > 0 && strongMatches.length === 0 && !targetedStudentMention);

  const matchedKeywords = unique([
    ...strongMatches,
    ...(targetedStudentMention ? ["学生"] : []),
    ...audienceMatches,
    ...activityMatches,
  ]);

  return {
    isStudentRelated,
    matchedKeywords,
    inferredEndDate: inferredEnd ? inferredEnd.format("YYYY-MM-DD") : null,
    extractedDates: unique(mentions.map((mention) => mention.isoDate)),
    relevanceReason: isStudentRelated
      ? `命中关键词：${matchedKeywords.join("、") || "无"}`
      : `未满足学生受众与活动信号同时出现的条件`,
    decisionReason: inferredEnd
      ? `根据正文中的时间信息，推断活动结束日为 ${inferredEnd.format("YYYY-MM-DD")}`
      : "正文中未提取到足以判定活动结束时间的日期",
  };
}
