import { Router, type Request, type Response } from "express";
import { getActivities } from "../services/sjtuCrawler.js";

const router = Router();

router.get("/", async (_req: Request, res: Response) => {
  try {
    const payload = await getActivities();
    res.status(200).json(payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "未知错误";

    res.status(500).json({
      success: false,
      error: "活动抓取失败",
      message,
    });
  }
});

export default router;
