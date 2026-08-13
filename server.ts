import express from "express";
import path from "path";
import { readFile, writeFile } from "node:fs/promises";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const dataDirectory = path.join(process.cwd(), "data");
const officialDataFile = path.join(dataDirectory, "official-data.json");
const userStateFile = path.join(dataDirectory, "app-state.json");

async function readJson<T>(filePath: string): Promise<T> {
  return JSON.parse(await readFile(filePath, "utf8")) as T;
}

async function readUserState() {
  try {
    return await readJson<Record<string, unknown>>(userStateFile);
  } catch (error: any) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

function isValidUserState(value: unknown): value is Record<string, unknown> {
  if (!value || typeof value !== "object") return false;
  const state = value as Record<string, unknown>;
  return ["htsItems", "shipments", "runs", "reviews"].every((key) => Array.isArray(state[key]));
}

async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT || 3000);

  app.use(express.json({ limit: "10mb" }));

  const apiKey = process.env.GEMINI_API_KEY || "";
  const ai = apiKey ? new GoogleGenAI({ apiKey }) : null;

  app.get("/api/health", async (_req, res) => {
    try {
      const officialData = await readJson<any>(officialDataFile);
      res.json({
        status: "ok",
        aiConfigured: !!ai,
        officialDataLoaded: true,
        htsChangeCount: officialData.dataset?.changeCount ?? 0,
        timestamp: new Date().toISOString(),
      });
    } catch (error: any) {
      res.status(503).json({
        status: "data_unavailable",
        aiConfigured: !!ai,
        officialDataLoaded: false,
        error: error?.message || String(error),
      });
    }
  });

  app.get("/api/data/bootstrap", async (_req, res) => {
    try {
      const [officialData, userState] = await Promise.all([
        readJson<Record<string, unknown>>(officialDataFile),
        readUserState(),
      ]);
      res.json({ ...officialData, aiConfigured: !!ai, userState });
    } catch (error: any) {
      res.status(500).json({ error: "공식 자료를 불러오지 못했습니다.", details: error?.message || String(error) });
    }
  });

  app.put("/api/data/state", async (req, res) => {
    if (!isValidUserState(req.body)) {
      return res.status(400).json({ error: "저장할 작업 데이터 형식이 올바르지 않습니다." });
    }

    const state = {
      htsItems: req.body.htsItems,
      shipments: req.body.shipments,
      runs: req.body.runs,
      reviews: req.body.reviews,
      savedAt: new Date().toISOString(),
    };
    await writeFile(userStateFile, JSON.stringify(state, null, 2), "utf8");
    res.json({ saved: true, savedAt: state.savedAt });
  });

  app.post("/api/genai/copilot", async (req, res) => {
    try {
      const prompt = typeof req.body?.prompt === "string" ? req.body.prompt.trim() : "";
      const context = req.body?.context;

      if (!prompt) return res.status(400).json({ error: "질문을 입력해 주세요." });
      if (prompt.length > 2000) return res.status(400).json({ error: "질문은 2,000자 이내로 입력해 주세요." });
      if (!ai) {
        return res.status(503).json({
          error: "AI 도우미 연결 정보가 설정되지 않았습니다. GEMINI_API_KEY를 설정한 뒤 다시 시도해 주세요.",
        });
      }

      const officialData = await readJson<any>(officialDataFile);
      const sourceSummary = officialData.sources
        .map((source: any) => `${source.nameKo}: ${source.url}`)
        .join("\n");

      const systemInstruction = `
당신은 미국 수출품목의 관세 변경 사전확인을 돕는 AI 도우미입니다.
일반 사용자가 이해할 수 있는 한국어로 답하고, 꼭 필요한 전문용어만 한국어 설명 뒤에 괄호로 표기하세요.
화면 데이터만으로 법적 결론을 확정하지 말고, 확인한 사실·추가 확인사항·권장 조치를 구분하세요.
근거가 없는 품목번호, 세율, 판례를 만들어내지 마세요.

현재 화면 정보: ${JSON.stringify(context || {})}
연결된 공식 자료:
${sourceSummary}
`;

      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: [{ role: "user", parts: [{ text: `${systemInstruction}\n\n질문: ${prompt}` }] }],
      });

      res.json({
        reply: response.text || "답변을 생성하지 못했습니다.",
        sources: officialData.sources.map((source: any) => `${source.nameKo} — ${source.url}`),
      });
    } catch (error: any) {
      console.error("AI assistant error:", error);
      res.status(500).json({
        error: "AI 도우미 요청을 처리하지 못했습니다.",
        details: error?.message || String(error),
      });
    }
  });

  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({ server: { middlewareMode: true }, appType: "spa" });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => res.sendFile(path.join(distPath, "index.html")));
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`US export tariff pre-check server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
