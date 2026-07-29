import axios from "axios";
import * as cheerio from "cheerio";
import { createHash } from "node:crypto";
import type { ActivityItem } from "../../shared/activities.js";
import type { ConfirmedNotification, ResultSource } from "../../shared/notifications.js";

const DEEPSEEK_BASE = "https://api.deepseek.com/v1/chat/completions";
const DEEPSEEK_MODEL = "deepseek-chat";

function getApiKey() {
  return process.env.DEEPSEEK_API_KEY || "";
}

function buildCampusSystemPrompt() {
  return [
    "你是一个竞赛推荐助手。学生会描述他们感兴趣的领域或方向，你需要从提供的活动列表中找出最匹配的条目。",
    "你将收到一个 JSON 数组，每个元素包含 id、title、summary、publishDate、inferredEndDate。",
    "你需要：",
    "1. 分析学生的查询意图，提取关键词和兴趣方向",
    "2. 从活动列表中筛选出与学生查询相关的条目（最多 5 条）",
    "3. 对每条推荐给出简短的匹配理由（不超过20字）",
    "",
    "重要：本平台面向大学生，请过滤掉明确面向中小学生（K-12）的比赛。",
    "",
    "请严格按以下 JSON 格式返回，不要包含任何其他文字：",
    '{ "recommendationIds": ["id1","id2"], "reasoning": "整体分析说明（不超过80字）", "matches": [{"id":"id1","reason":"匹配理由"}] }',
  ].join("\n");
}

function buildWebSearchPrompt(query: string, searchResults: string) {
  return [
    "推荐大学生竞赛。学生查询：" + query,
    "",
    "参考信息（可能不准确，仅当内容与查询主题匹配时才采纳）：",
    searchResults,
    "",
    "请直接推荐与「" + query + "」领域相关的知名大学生竞赛。",
    "如果参考信息与该领域完全无关，忽略它，用你的知识推荐。",
    "最多5条，JSON格式：",
    '{ "items": [{"title":"名称","url":"","summary":"简介(不超过150字)","date":""}], "reasoning":"说明" }',
  ].join("\n");
}

async function fetchPageContent(url: string): Promise<string> {
  try {
    const response = await axios.get<string>(url, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
      },
      timeout: 8000,
      maxRedirects: 3,
    });

    const $ = cheerio.load(response.data);

    // Remove non-content elements
    $("script, style, nav, footer, header, .sidebar, .nav, .footer, .header, .menu, .advertisement").remove();

    // Extract main content
    const title = $("title").text().trim();
    const bodyText = $("body").text().replace(/\s+/g, " ").trim().slice(0, 3000);

    return `页面标题：${title}\n\n页面正文：${bodyText}`;
  } catch {
    return "";
  }
}

function buildDeepExtractPrompt(query: string, pageContent: string) {
  return [
    "你是一个竞赛信息提取助手。请从以下网页内容中提取竞赛官方网站的简介。",
    "用户查询：" + query,
    "",
    "网页内容：",
    pageContent,
    "",
    "请以 JSON 格式返回该官网的信息：",
    '{ "title": "竞赛名称/官网名称", "summary": "官网简介（不超过200字，说明该竞赛是什么、由谁主办、面向什么群体）", "date": "" }',
    "如果页面与竞赛无关、无法提取信息、或该竞赛主要面向中小学生（K-12），返回空 JSON：{}",
    "只返回 JSON，不要任何其他文字。",
  ].join("\n");
}

function parseDeepExtract(content: string) {
  try {
    const cleaned = content.replace(/```json\s*/g, "").replace(/```\s*/g, "").trim();
    return JSON.parse(cleaned) as {
      title?: string;
      summary?: string;
      date?: string;
      details?: Record<string, string>;
    };
  } catch {
    return {};
  }
}

async function searchWeb(query: string) {
  const url = "https://www.bing.com/search";
  const response = await axios.get<string>(url, {
    params: { q: query, setlang: "zh-Hans", count: 10 },
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9",
    },
    timeout: 12000,
  });

  const $ = cheerio.load(response.data);
  const results: Array<{ title: string; snippet: string; url: string }> = [];

  $("li.b_algo").each((_, el) => {
    const titleEl = $(el).find("h2 a");
    const snippetEl = $(el).find(".b_caption p");
    const title = titleEl.text().trim();
    const snippet = snippetEl.text().trim();
    const href = titleEl.attr("href") || "";

    if (title && snippet) {
      results.push({ title, snippet, url: href });
    }
  });

  // Fallback: try alternative selectors if b_algo not found
  if (results.length === 0) {
    $("ol#b_results > li").each((_, el) => {
      const titleEl = $(el).find("h2 a, a[href]").first();
      const snippetEl = $(el).find("p");
      const title = titleEl.text().trim();
      const snippet = snippetEl.first().text().trim();
      const href = titleEl.attr("href") || "";

      if (title && snippet && href && !results.some((r) => r.url === href)) {
        results.push({ title, snippet, url: href });
      }
    });
  }

  return results.slice(0, 8);
}

export async function searchByAi(
  query: string,
  activities: ActivityItem[],
): Promise<{
  recommendations: ConfirmedNotification[];
  campusCount: number;
  webCount: number;
  reasoning: string;
}> {
  const apiKey = getApiKey();

  // 第一步：校内匹配
  let campusResults: ConfirmedNotification[] = [];
  let campusReasoning = "";

  if (apiKey) {
    try {
      const response = await fetch(DEEPSEEK_BASE, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: DEEPSEEK_MODEL,
          messages: [
            { role: "system", content: buildCampusSystemPrompt() },
            { role: "user", content: buildCampusUserPrompt(query, activities) },
          ],
          temperature: 0.3,
          max_tokens: 1200,
        }),
      });

      if (response.ok) {
        const data = (await response.json()) as {
          choices: Array<{ message: { content: string } }>;
        };
        const content = data.choices[0]?.message?.content || "";
        const parsed = parseAiResponse(content);
        campusReasoning = parsed.reasoning;

        campusResults = parsed.recommendationIds
          .map((id) => {
            const item = activities.find((a) => a.id === id);
            if (!item) return null;
            const matchInfo = parsed.matches.find((m) => m.id === id);
            return {
              id: item.id,
              title: item.title,
              url: item.url,
              publishDate: item.publishDate,
              inferredEndDate: item.inferredEndDate,
              summary: item.summary,
              confirmedAt: new Date().toISOString(),
              studentQuery: query,
              matchReason: matchInfo?.reason || "匹配学生兴趣",
              source: "campus" as ResultSource,
            } satisfies ConfirmedNotification;
          })
          .filter(Boolean) as ConfirmedNotification[];
      }
    } catch (err) {
      console.log("[campus] error:", err instanceof Error ? err.message : err);
      // fall through to keyword matching
    }
  }

  if (!apiKey && campusResults.length === 0) {
    const kwResult = keywordMatchCampus(query, activities);
    campusResults = kwResult.recommendations;
    campusReasoning = kwResult.reasoning;
  }

  // 第二步：联网搜索
  let webResults: ConfirmedNotification[] = [];
  let webReasoning = "";

  if (apiKey) {
    try {
      // 用 DeepSeek 直接推荐，不依赖搜索引擎结果
      const response = await fetch(DEEPSEEK_BASE, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: DEEPSEEK_MODEL,
          messages: [
            {
              role: "system",
              content: [
                "你是一个大学生竞赛推荐助手。根据学生输入的关键词，推荐该领域内主流的大学生竞赛。",
                "只推荐与关键词直接相关的竞赛，不要推荐无关竞赛。",
                "排除中小学生竞赛。以 JSON 格式返回：",
                '{ "items": [{"title":"竞赛名称","url":"","summary":"简介(不超过150字)"}], "reasoning":"推荐理由(不超过60字)" }',
              ].join("\n"),
            },
            { role: "user", content: query },
          ],
          temperature: 0.3,
          max_tokens: 1500,
        }),
      });

      if (response.ok) {
        const data = (await response.json()) as {
          choices: Array<{ message: { content: string } }>;
        };
        const content = data.choices[0]?.message?.content || "";
        const parsed = parseWebResponse(content);
        webReasoning = parsed.reasoning;

        webResults = parsed.items.map((item) => ({
          id: createId(item.title + Date.now()),
          title: item.title,
          url: item.url || "",
          publishDate: "",
          inferredEndDate: item.date || null,
          summary: item.summary,
          confirmedAt: new Date().toISOString(),
          studentQuery: query,
          matchReason: "AI 推荐",
          source: "web" as ResultSource,
        } satisfies ConfirmedNotification));
      }
    } catch (webErr) {
      console.log("[webSearch] error:", webErr instanceof Error ? webErr.message : webErr);
    }
  }

  const allRecommendations = [...campusResults, ...webResults];

  const reasoningParts: string[] = [];
  if (campusReasoning) reasoningParts.push("【校内】" + campusReasoning);
  if (webReasoning) reasoningParts.push("【互联网】" + webReasoning);
  if (reasoningParts.length === 0) reasoningParts.push("未找到匹配的竞赛活动");

  return {
    recommendations: allRecommendations,
    campusCount: campusResults.length,
    webCount: webResults.length,
    reasoning: reasoningParts.join("\n"),
  };
}

function buildCampusUserPrompt(query: string, activities: ActivityItem[]) {
  const candidates = activities.map((item) => ({
    id: item.id,
    title: item.title,
    summary: item.summary.slice(0, 300),
    publishDate: item.publishDate,
    inferredEndDate: item.inferredEndDate,
  }));

  return ["学生查询：" + query, "", "可推荐活动列表：", JSON.stringify(candidates, null, 2)].join("\n");
}

function parseAiResponse(content: string) {
  try {
    const cleaned = content.replace(/```json\s*/g, "").replace(/```\s*/g, "").trim();
    const parsed = JSON.parse(cleaned) as {
      recommendationIds?: string[];
      reasoning?: string;
      matches?: Array<{ id: string; reason: string }>;
    };
    return {
      recommendationIds: parsed.recommendationIds || [],
      reasoning: parsed.reasoning || "基于 AI 分析推荐",
      matches: parsed.matches || [],
    };
  } catch {
    return { recommendationIds: [], reasoning: "AI 结果解析异常", matches: [] };
  }
}

function parseWebResponse(content: string) {
  try {
    const cleaned = content.replace(/```json\s*/g, "").replace(/```\s*/g, "").trim();
    const parsed = JSON.parse(cleaned) as {
      items?: Array<{ title: string; url?: string; summary: string; date?: string }>;
      reasoning?: string;
    };
    return {
      items: parsed.items || [],
      reasoning: parsed.reasoning || "",
    };
  } catch {
    return { items: [], reasoning: "" };
  }
}

function cleanText(text: string): string {
  return text
    .replace(/[\u0000-\u001f\u007f\u00a0\u2000-\u200f\u2028-\u202f\u205f\u3000\r\n\t]+/g, "")
    .trim();
}

function createId(input: string) {
  return createHash("md5").update(input).digest("hex").slice(0, 12);
}

function keywordMatchCampus(query: string, activities: ActivityItem[]) {
  const keywords = query
    .split(/[\s,，、]+/)
    .filter(Boolean)
    .filter((kw) => kw.length > 0);

  const scored = activities
    .map((item) => {
      let score = 0;
      const title = cleanText(item.title);
      const summary = cleanText(item.summary);
      for (const kw of keywords) {
        if (title.indexOf(kw) !== -1) score += 3;
        if (summary.indexOf(kw) !== -1) score += 1;
      }
      return { item, score };
    })
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);

  return {
    recommendations: scored.map(
      ({ item }) =>
        ({
          id: item.id,
          title: item.title,
          url: item.url,
          publishDate: item.publishDate,
          inferredEndDate: item.inferredEndDate,
          summary: item.summary,
          confirmedAt: new Date().toISOString(),
          studentQuery: query,
          matchReason: "关键词匹配",
          source: "campus" as ResultSource,
        } satisfies ConfirmedNotification),
    ),
    reasoning: `未配置 DeepSeek API Key，使用关键词匹配模式（扫描 ${activities.length} 条，命中 ${scored.length} 条）。`,
  };
}
