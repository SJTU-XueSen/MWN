import cors from "cors";
import dotenv from "dotenv";
import express, { type NextFunction, type Request, type Response } from "express";
import activitiesRoutes from "./routes/activities.js";
import aiSearchRoutes from "./routes/aiSearch.js";
import memosRoutes from "./routes/memos.js";
import notificationsRoutes from "./routes/notifications.js";
import studentActivitiesRoutes from "./routes/studentActivities.js";

dotenv.config();

const app: express.Application = express();

app.use(cors());
app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true, limit: "10mb" }));

app.use("/api/activities", activitiesRoutes);
app.use("/api/ai-search", aiSearchRoutes);
app.use("/api/memos", memosRoutes);
app.use("/api/notifications", notificationsRoutes);
app.use("/api/student-activities", studentActivitiesRoutes);

app.get("/api/health", (_req: Request, res: Response) => {
  res.status(200).json({
    success: true,
    message: "ok",
  });
});

app.use((error: Error, _req: Request, res: Response, _next: NextFunction) => {
  res.status(500).json({
    success: false,
    error: "服务器内部错误",
    message: error.message,
  });
});

app.use((_req: Request, res: Response) => {
  res.status(404).json({
    success: false,
    error: "API 不存在",
  });
});

export default app;
