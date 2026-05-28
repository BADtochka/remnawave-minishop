import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const siteRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const distRoot = path.join(siteRoot, "dist");

const userRoutes = [
  "home",
  "install",
  "trial",
  "invite",
  "devices",
  "support",
  "settings",
  "login",
  "login/password",
];

const adminRoutes = [
  "stats",
  "users",
  "payments",
  "promos",
  "ads",
  "broadcast",
  "logs",
  "support",
  "tariffs",
  "appearance",
  "translations",
  "backups",
  "settings",
];

const demoRoutes = [
  ...userRoutes.map((route) => `demo/${route}`),
  "demo/admin",
  ...adminRoutes.map((route) => `demo/admin/${route}`),
];

const runtimeRoutes = [
  ...userRoutes.map((route) => `demo/runtime/${route}`),
  "demo/runtime/admin",
  ...adminRoutes.map((route) => `demo/runtime/admin/${route}`),
];

async function copyHtml(source, route) {
  const targetDir = path.join(distRoot, route);
  await mkdir(targetDir, { recursive: true });
  await copyFile(source, path.join(targetDir, "index.html"));
}

const demoShell = path.join(distRoot, "demo", "index.html");
const runtimeApp = path.join(distRoot, "demo", "runtime", "app.html");

for (const route of demoRoutes) {
  await copyHtml(demoShell, route);
}

for (const route of runtimeRoutes) {
  await copyHtml(runtimeApp, route);
}

console.log(
  `Materialized ${demoRoutes.length} public demo routes and ${runtimeRoutes.length} runtime routes`,
);
