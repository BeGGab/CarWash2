/**
 * Записывает config.json в dist/ из переменной окружения BACKEND_URL.
 * Запускать после npm run build, перед serve (деплой без Docker).
 */
const fs = require("fs");
const path = require("path");

const dir = path.join(__dirname, "..", "dist");
const file = path.join(dir, "config.json");
const url = (process.env.BACKEND_URL || "").trim().replace(/\/$/, "");
const obj = { backendUrl: url || "" };

if (!fs.existsSync(dir)) {
  console.error("dist/ not found. Run npm run build first.");
  process.exit(1);
}
fs.writeFileSync(file, JSON.stringify(obj, null, 0), "utf8");
console.log("Written config.json with backendUrl:", obj.backendUrl || "(empty)");
