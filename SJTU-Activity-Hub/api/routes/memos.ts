import { Router, type Request, type Response } from "express";
import type { MemoCreateRequest, MemoItem } from "../../shared/memos.js";
import { createHash } from "node:crypto";

const router = Router();

const store = new Map<string, MemoItem>();

router.get("/", (_req: Request, res: Response) => {
  const items = Array.from(store.values()).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
  res.status(200).json({ success: true, items });
});

router.post("/", (req: Request, res: Response): void => {
  const { title, note, deadline } = req.body as MemoCreateRequest;

  if (!title?.trim()) {
    res.status(400).json({ success: false, error: "标题不能为空" });
    return;
  }

  const id = createHash("md5").update(title + Date.now()).digest("hex").slice(0, 12);
  const item: MemoItem = {
    id,
    title: title.trim(),
    note: note?.trim() || "",
    deadline: deadline || "",
    createdAt: new Date().toISOString(),
  };

  store.set(id, item);
  res.status(201).json({ success: true, item });
});

router.delete("/:id", (req: Request, res: Response): void => {
  const { id } = req.params;

  if (!store.has(id)) {
    res.status(404).json({ success: false, error: "备忘录不存在" });
    return;
  }

  store.delete(id);
  res.status(200).json({ success: true });
});

export default router;
