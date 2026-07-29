// @vitest-environment node

import { describe, expect, it } from "vitest";
import { analyzeNotice } from "./activityRules";

describe("activityRules", () => {
  it("识别学生相关且在基准日未结束的活动", () => {
    const analysis = analyzeNotice(
      "上海交通大学2026年主题献血活动通知",
      "校红十字会将于2026年3月25日组织开展主题献血活动，号召广大师生参加。",
      "2026-03-23",
    );

    expect(analysis.isStudentRelated).toBe(true);
    expect(analysis.inferredEndDate).toBe("2026-03-25");
  });

  it("识别学生相关但已结束的报名活动", () => {
    const analysis = analyzeNotice(
      "上海交通大学2026春季学期助教培训通知",
      "请通知学院助教登录报名系统，报名截止时间：2026年3月12日12:00前。",
      "2026-03-05",
    );

    expect(analysis.isStudentRelated).toBe(true);
    expect(analysis.inferredEndDate).toBe("2026-03-12");
  });

  it("排除仅面向教师的公开课通知", () => {
    const analysis = analyzeNotice(
      "关于开展2026年春季学期“优秀教师公开课”活动的通知",
      "为促进老师们相互走进课堂交流和学习，欢迎老师报名参加公开课。",
      "2026-03-21",
    );

    expect(analysis.isStudentRelated).toBe(false);
  });
});
