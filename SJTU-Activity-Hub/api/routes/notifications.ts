import { Router, type Request, type Response } from "express";
import type { ConfirmedNotification } from "../../shared/notifications.js";

const router = Router();

const store = new Map<string, ConfirmedNotification>();

router.get("/", (_req: Request, res: Response) => {
  const items = Array.from(store.values()).sort(
    (a, b) => new Date(b.confirmedAt).getTime() - new Date(a.confirmedAt).getTime(),
  );

  res.status(200).json({ success: true, items });
});

router.post("/", (req: Request, res: Response): void => {
  const notification = req.body as ConfirmedNotification;

  if (!notification?.id || !notification?.title) {
    res.status(400).json({ success: false, error: "通知数据不完整" });
    return;
  }

  store.set(notification.id, {
    ...notification,
    confirmedAt: notification.confirmedAt || new Date().toISOString(),
  });

  res.status(201).json({ success: true, item: store.get(notification.id) });
});

router.delete("/:id", (req: Request, res: Response): void => {
  const { id } = req.params;

  if (!store.has(id)) {
    res.status(404).json({ success: false, error: "通知不存在" });
    return;
  }

  store.delete(id);
  res.status(200).json({ success: true });
});

export default router;
