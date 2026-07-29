import { Router, type Request, type Response } from "express";
import { getActivities } from "../services/sjtuCrawler.js";
import { searchByAi } from "../services/aiMatcher.js";

const router = Router();

router.post("/", async (req: Request, res: Response): Promise<void> => {
  const { query } = req.body as { query?: string };

  if (!query || typeof query !== "string" || !query.trim()) {
    res.status(400).json({ success: false, error: "请输入搜索关键词" });
    return;
  }

  try {
    const activitiesResult = await getActivities();
    const result = await searchByAi(query.trim(), activitiesResult.items);

    res.status(200).json({
      success: true,
      ...result,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "未知错误";
    res.status(500).json({ success: false, error: "AI 搜索失败", message });
  }
});

export default router;
