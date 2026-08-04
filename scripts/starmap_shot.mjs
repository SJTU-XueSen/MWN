// 星图视觉验证：headless Chrome 登录 → 打开 /starmap → 截图
// 用法: node scripts/starmap_shot.mjs [输出路径]
import { spawn } from "node:child_process";
const WebSocket = globalThis.WebSocket; // Node 22+ 内置

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9333;
const OUT = process.argv[2] || "starmap_shot.jpg";

const chrome = spawn(CHROME, [
  "--headless=new",
  `--remote-debugging-port=${PORT}`,
  "--disable-gpu", "--no-sandbox",
  "--window-size=1600,900",
  "--user-data-dir=C:\\Users\\wqx_0\\AppData\\Local\\Temp\\chrome-starmap",
  "about:blank",
], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getWs() {
  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const tabs = await r.json();
      const tab = tabs.find((t) => t.type === "page");
      if (tab) return tab.webSocketDebuggerUrl;
    } catch {}
    await sleep(250);
  }
  throw new Error("chrome devtools not reachable");
}

let msgId = 0;
const pending = new Map();
function cdp(ws, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++msgId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function main() {
  const ws = new WebSocket(await getWs());
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  ws.addEventListener("message", (ev) => {
    const m = JSON.parse(ev.data.toString());
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id); pending.delete(m.id);
      m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result);
    }
  });

  await cdp(ws, "Page.enable");
  await cdp(ws, "Runtime.enable");
  await cdp(ws, "Emulation.setDeviceMetricsOverride", { width: 1600, height: 900, deviceScaleFactor: 1, mobile: false });

  // 登录拿 session cookie
  await cdp(ws, "Page.navigate", { url: "http://127.0.0.1:5000/login" });
  await sleep(1500);
  const login = await cdp(ws, "Runtime.evaluate", {
    expression: `fetch('/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:'txdsyl_',password:'090915'})}).then(r=>r.json())`,
    awaitPromise: true, returnByValue: true,
  });
  console.log("login:", JSON.stringify(login.result?.value || login.result?.description || login.result).slice(0, 120));

  // 打开星图
  await cdp(ws, "Page.navigate", { url: "http://127.0.0.1:5000/starmap" });
  await sleep(5000); // 等 API + 力导向布局

  const shot = await cdp(ws, "Page.captureScreenshot", { format: "jpeg", quality: 80 });
  const { writeFileSync } = await import("node:fs");
  writeFileSync(OUT, Buffer.from(shot.data, "base64"));
  console.log("saved:", OUT);

  // 页面文本验证（stats 文案 + 图例）
  const text = await cdp(ws, "Runtime.evaluate", {
    expression: `document.body.innerText.replace(/\\n+/g, ' | ').slice(0, 600)`,
    returnByValue: true,
  });
  console.log("page-text:", (text.result?.value || "").slice(0, 500));

  // 控制台错误收集
  const consoleErr = await cdp(ws, "Runtime.evaluate", {
    expression: `(() => { const errs = window.__errs || []; return errs.slice(-10); })()`,
    returnByValue: true,
  });
  console.log("console-errs:", JSON.stringify(consoleErr.result?.value || []));

  ws.close();
  chrome.kill();
  process.exit(0);
}

main().catch((e) => { console.error("FAIL:", e.message); chrome.kill(); process.exit(1); });
