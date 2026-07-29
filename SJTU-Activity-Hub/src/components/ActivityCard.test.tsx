import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ActivityCard from "./ActivityCard";

describe("ActivityCard", () => {
  it("渲染活动信息并触发选择事件", () => {
    const onSelect = vi.fn();

    render(
      <ActivityCard
        selected={false}
        onSelect={onSelect}
        activity={{
          id: "demo-1",
          title: "上海交通大学2026年主题献血活动通知",
          url: "https://www.sjtu.edu.cn/tg/20260323/220663.html",
          publishDate: "2026-03-23",
          matchedKeywords: ["师生", "献血", "活动"],
          extractedDates: ["2026-03-25"],
          inferredEndDate: "2026-03-25",
          summary: "校红十字会将于2026年3月25日组织开展主题献血活动。",
          status: "ongoing",
          relevanceReason: "命中关键词：师生、献血、活动",
          decisionReason: "根据正文中的时间信息，推断活动结束日为 2026-03-25",
        }}
      />,
    );

    expect(screen.getByText("上海交通大学2026年主题献血活动通知")).toBeTruthy();
    expect(screen.getByText("推断结束日")).toBeTruthy();

    screen.getByRole("button").click();
    expect(onSelect).toHaveBeenCalledWith("demo-1");
  });
});
