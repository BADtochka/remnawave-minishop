import { readFile } from "node:fs/promises";
import path from "node:path";

const runtimeAppHtml = path.join(process.cwd(), "public", "demo", "runtime", "app.html");

export const prerender = true;

export async function GET() {
  return new Response(await readFile(runtimeAppHtml, "utf8"), {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
    },
  });
}
