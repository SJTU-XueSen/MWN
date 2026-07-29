import axios from "axios";
import * as cheerio from "cheerio";
import dayjs, { type Dayjs } from "dayjs";
import { createHash } from "node:crypto";
import type { ActivitiesResponse, ActivityItem } from "../../shared/activities.js";
import { analyzeNotice, buildSummary, looksLikeTitleCandidate } from "./activityRules.js";

const BASE_URL = "https://www.sjtu.edu.cn";
const LIST_URL = `${BASE_URL}/tg`;
const REQUEST_HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
};
const CACHE_TTL_MS = 1000 * 60 * 30;
const PAGE_CONCURRENCY = 6;
const DETAIL_CONCURRENCY = 5;

type ListNotice = {
  title: string;
  url: string;
  publishDate: string;
};

type CachedResult = {
  expiresAt: number;
  payload: ActivitiesResponse;
};

let cache: CachedResult | null = null;

function getAsOfDate() {
  return dayjs().startOf("day");
}

function sanitizeTitle(raw: string) {
  const result = raw
    .replace(/[\u00a0\u0000-\u001f\u007f\u2000-\u200f\u2028-\u202f\u205f\u3000\r\n\t]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  return result;
}

async function mapLimit<T, R>(items: T[], limit: number, mapper: (item: T) => Promise<R>) {
  const results: R[] = [];
  const queue = [...items];

  async function worker() {
    while (queue.length > 0) {
      const item = queue.shift();

      if (item === undefined) {
        return;
      }

      results.push(await mapper(item));
    }
  }

  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, () => worker()));
  return results;
}

function buildListUrl(page: number) {
  return page === 1 ? `${LIST_URL}/index.html` : `${LIST_URL}/index_${page}.html`;
}

async function fetchHtml(url: string) {
  const response = await axios.get<string>(url, {
    headers: REQUEST_HEADERS,
    responseType: "text",
    timeout: 15000,
  });

  return response.data;
}

function parseTotalPages(html: string) {
  const matched = html.match(/totalPage:\s*(\d+)/);
  return matched ? Number(matched[1]) : 1;
}

function parseListPage(html: string) {
  const $ = cheerio.load(html);
  const notices: ListNotice[] = [];

  $("ul.list-date li").each((_, element) => {
    const anchor = $(element).find("a").first();
    const time = $(element).find(".time").text().trim();
    const rawTitle = anchor.attr("title")?.trim() || anchor.text().trim();
    const href = anchor.attr("href");

    if (!rawTitle || !href || !time) {
      return;
    }

    notices.push({
      title: sanitizeTitle(rawTitle),
      url: new URL(href, BASE_URL).toString(),
      publishDate: dayjs(time.replace(/\./g, "-")).format("YYYY-MM-DD"),
    });
  });

  return notices;
}

function extractArticleText(html: string) {
  const $ = cheerio.load(html);
  const selectors = [
    ".Article_content",
    ".article-content",
    "#vsb_content",
    ".v_news_content",
    ".content",
    ".pageMain",
  ];

  for (const selector of selectors) {
    const text = $(selector).text().replace(/\s+/g, " ").trim();
    if (text.length > 80) {
      return text;
    }
  }

  return $("body").text().replace(/\s+/g, " ").trim();
}

function createId(url: string) {
  return createHash("md5").update(url).digest("hex").slice(0, 12);
}

async function evaluateNotice(notice: ListNotice, asOfDate: Dayjs) {
  try {
    const html = await fetchHtml(notice.url);
    const articleText = extractArticleText(html);
    const analysis = analyzeNotice(notice.title, articleText, notice.publishDate);

    if (!analysis.isStudentRelated) {
      return { reason: "not-student-related", item: null as ActivityItem | null };
    }

    if (!analysis.inferredEndDate) {
      return { reason: "no-end-date", item: null as ActivityItem | null };
    }

    if (dayjs(analysis.inferredEndDate).isBefore(asOfDate, "day")) {
      return { reason: "already-ended", item: null as ActivityItem | null };
    }

    const item: ActivityItem = {
      id: createId(notice.url),
      title: notice.title,
      url: notice.url,
      publishDate: notice.publishDate,
      matchedKeywords: analysis.matchedKeywords,
      extractedDates: analysis.extractedDates,
      inferredEndDate: analysis.inferredEndDate,
      summary: buildSummary(articleText),
      status: "ongoing",
      relevanceReason: analysis.relevanceReason,
      decisionReason: analysis.decisionReason,
    };

    return { reason: "matched", item };
  } catch {
    return { reason: "fetch-failed", item: null as ActivityItem | null };
  }
}

export async function getActivities() {
  const asOfDate = getAsOfDate();
  const asOfDateText = asOfDate.format("YYYY-MM-DD");

  if (cache && cache.expiresAt > Date.now() && cache.payload.asOfDate === asOfDateText) {
    return cache.payload;
  }

  const firstPageHtml = await fetchHtml(buildListUrl(1));
  const totalPages = parseTotalPages(firstPageHtml);
  const listPageNumbers = Array.from({ length: totalPages }, (_, index) => index + 1);

  const listPageHtml = await mapLimit(listPageNumbers, PAGE_CONCURRENCY, async (pageNumber) => {
    if (pageNumber === 1) {
      return firstPageHtml;
    }

    return fetchHtml(buildListUrl(pageNumber));
  });

  const allNotices = listPageHtml.flatMap((html) => parseListPage(html));
  const seen = new Set<string>();
  const eligibleByDate = allNotices.filter((notice) => {
    if (seen.has(notice.url)) {
      return false;
    }

    seen.add(notice.url);
    return !dayjs(notice.publishDate).isAfter(asOfDate, "day");
  });

  const titleCandidates = eligibleByDate.filter((notice) => looksLikeTitleCandidate(notice.title));
  const evaluated = await mapLimit(titleCandidates, DETAIL_CONCURRENCY, async (notice) =>
    evaluateNotice(notice, asOfDate),
  );

  const filteredByReason: Record<string, number> = {
    "not-student-related": 0,
    "no-end-date": 0,
    "already-ended": 0,
    "fetch-failed": 0,
  };

  const items = evaluated
    .map((result) => {
      if (result.reason !== "matched") {
        filteredByReason[result.reason] = (filteredByReason[result.reason] || 0) + 1;
      }

      return result.item;
    })
    .filter((item): item is ActivityItem => Boolean(item))
    .sort((left, right) => {
      const leftEnd = left.inferredEndDate ? dayjs(left.inferredEndDate).valueOf() : 0;
      const rightEnd = right.inferredEndDate ? dayjs(right.inferredEndDate).valueOf() : 0;

      if (rightEnd !== leftEnd) {
        return rightEnd - leftEnd;
      }

      return dayjs(right.publishDate).valueOf() - dayjs(left.publishDate).valueOf();
    });

  const payload: ActivitiesResponse = {
    asOfDate: asOfDateText,
    source: "https://www.sjtu.edu.cn/tg",
    stats: {
      scannedCount: allNotices.length,
      publishDateEligibleCount: eligibleByDate.length,
      titleCandidateCount: titleCandidates.length,
      matchedCount: items.length,
      filteredByReason,
    },
    items,
  };

  cache = {
    expiresAt: Date.now() + CACHE_TTL_MS,
    payload,
  };

  return payload;
}
