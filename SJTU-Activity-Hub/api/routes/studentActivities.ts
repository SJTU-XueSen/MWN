import { Router, type Request, type Response } from "express";
import type { StudentActivity, StudentActivityCreate } from "../../shared/studentActivities.js";
import { createHash } from "node:crypto";

const router = Router();

const store = new Map<string, StudentActivity>();

router.get("/", (_req: Request, res: Response) => {
  const items = Array.from(store.values()).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
  res.status(200).json({ success: true, items });
});

router.post("/", (req: Request, res: Response): void => {
  const body = req.body as StudentActivityCreate;

  if (!body.title?.trim()) {
    res.status(400).json({ success: false, error: "活动名称不能为空" });
    return;
  }
  if (!body.description?.trim()) {
    res.status(400).json({ success: false, error: "活动内容不能为空" });
    return;
  }

  const id = createHash("md5").update(body.title + Date.now()).digest("hex").slice(0, 12);
  const item: StudentActivity = {
    id,
    title: body.title.trim(),
    description: body.description.trim(),
    date: body.date || "",
    location: body.location?.trim() || "",
    organizer: body.organizer?.trim() || "",
    contact: body.contact?.trim() || "",
    createdAt: new Date().toISOString(),
  };

  store.set(id, item);
  res.status(201).json({ success: true, item });
});

router.delete("/:id", (req: Request, res: Response): void => {
  const { id } = req.params;

  if (!store.has(id)) {
    res.status(404).json({ success: false, error: "活动不存在" });
    return;
  }

  store.delete(id);
  res.status(200).json({ success: true });
});

export default router;
