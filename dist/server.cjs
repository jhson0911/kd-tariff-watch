var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// server.ts
var import_express = __toESM(require("express"), 1);
var import_path = __toESM(require("path"), 1);
var import_promises = require("node:fs/promises");
var import_vite = require("vite");
var import_genai = require("@google/genai");
var import_dotenv = __toESM(require("dotenv"), 1);
import_dotenv.default.config();
var dataDirectory = import_path.default.join(process.cwd(), "data");
var officialDataFile = import_path.default.join(dataDirectory, "official-data.json");
var userStateFile = import_path.default.join(dataDirectory, "app-state.json");
async function readJson(filePath) {
  return JSON.parse(await (0, import_promises.readFile)(filePath, "utf8"));
}
async function readUserState() {
  try {
    return await readJson(userStateFile);
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}
function isValidUserState(value) {
  if (!value || typeof value !== "object") return false;
  const state = value;
  return ["htsItems", "shipments", "runs", "reviews"].every((key) => Array.isArray(state[key]));
}
async function startServer() {
  const app = (0, import_express.default)();
  const PORT = Number(process.env.PORT || 3e3);
  app.use(import_express.default.json({ limit: "10mb" }));
  const apiKey = process.env.GEMINI_API_KEY || "";
  const ai = apiKey ? new import_genai.GoogleGenAI({ apiKey }) : null;
  app.get("/api/health", async (_req, res) => {
    try {
      const officialData = await readJson(officialDataFile);
      res.json({
        status: "ok",
        aiConfigured: !!ai,
        officialDataLoaded: true,
        htsChangeCount: officialData.dataset?.changeCount ?? 0,
        timestamp: (/* @__PURE__ */ new Date()).toISOString()
      });
    } catch (error) {
      res.status(503).json({
        status: "data_unavailable",
        aiConfigured: !!ai,
        officialDataLoaded: false,
        error: error?.message || String(error)
      });
    }
  });
  app.get("/api/data/bootstrap", async (_req, res) => {
    try {
      const [officialData, userState] = await Promise.all([
        readJson(officialDataFile),
        readUserState()
      ]);
      res.json({ ...officialData, aiConfigured: !!ai, userState });
    } catch (error) {
      res.status(500).json({ error: "\uACF5\uC2DD \uC790\uB8CC\uB97C \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.", details: error?.message || String(error) });
    }
  });
  app.put("/api/data/state", async (req, res) => {
    if (!isValidUserState(req.body)) {
      return res.status(400).json({ error: "\uC800\uC7A5\uD560 \uC791\uC5C5 \uB370\uC774\uD130 \uD615\uC2DD\uC774 \uC62C\uBC14\uB974\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4." });
    }
    const state = {
      htsItems: req.body.htsItems,
      shipments: req.body.shipments,
      runs: req.body.runs,
      reviews: req.body.reviews,
      savedAt: (/* @__PURE__ */ new Date()).toISOString()
    };
    await (0, import_promises.writeFile)(userStateFile, JSON.stringify(state, null, 2), "utf8");
    res.json({ saved: true, savedAt: state.savedAt });
  });
  app.post("/api/genai/copilot", async (req, res) => {
    try {
      const prompt = typeof req.body?.prompt === "string" ? req.body.prompt.trim() : "";
      const context = req.body?.context;
      if (!prompt) return res.status(400).json({ error: "\uC9C8\uBB38\uC744 \uC785\uB825\uD574 \uC8FC\uC138\uC694." });
      if (prompt.length > 2e3) return res.status(400).json({ error: "\uC9C8\uBB38\uC740 2,000\uC790 \uC774\uB0B4\uB85C \uC785\uB825\uD574 \uC8FC\uC138\uC694." });
      if (!ai) {
        return res.status(503).json({
          error: "AI \uB3C4\uC6B0\uBBF8 \uC5F0\uACB0 \uC815\uBCF4\uAC00 \uC124\uC815\uB418\uC9C0 \uC54A\uC558\uC2B5\uB2C8\uB2E4. GEMINI_API_KEY\uB97C \uC124\uC815\uD55C \uB4A4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC8FC\uC138\uC694."
        });
      }
      const officialData = await readJson(officialDataFile);
      const sourceSummary = officialData.sources.map((source) => `${source.nameKo}: ${source.url}`).join("\n");
      const systemInstruction = `
\uB2F9\uC2E0\uC740 \uBBF8\uAD6D \uC218\uCD9C\uD488\uBAA9\uC758 \uAD00\uC138 \uBCC0\uACBD \uC0AC\uC804\uD655\uC778\uC744 \uB3D5\uB294 AI \uB3C4\uC6B0\uBBF8\uC785\uB2C8\uB2E4.
\uC77C\uBC18 \uC0AC\uC6A9\uC790\uAC00 \uC774\uD574\uD560 \uC218 \uC788\uB294 \uD55C\uAD6D\uC5B4\uB85C \uB2F5\uD558\uACE0, \uAF2D \uD544\uC694\uD55C \uC804\uBB38\uC6A9\uC5B4\uB9CC \uD55C\uAD6D\uC5B4 \uC124\uBA85 \uB4A4\uC5D0 \uAD04\uD638\uB85C \uD45C\uAE30\uD558\uC138\uC694.
\uD654\uBA74 \uB370\uC774\uD130\uB9CC\uC73C\uB85C \uBC95\uC801 \uACB0\uB860\uC744 \uD655\uC815\uD558\uC9C0 \uB9D0\uACE0, \uD655\uC778\uD55C \uC0AC\uC2E4\xB7\uCD94\uAC00 \uD655\uC778\uC0AC\uD56D\xB7\uAD8C\uC7A5 \uC870\uCE58\uB97C \uAD6C\uBD84\uD558\uC138\uC694.
\uADFC\uAC70\uAC00 \uC5C6\uB294 \uD488\uBAA9\uBC88\uD638, \uC138\uC728, \uD310\uB840\uB97C \uB9CC\uB4E4\uC5B4\uB0B4\uC9C0 \uB9C8\uC138\uC694.

\uD604\uC7AC \uD654\uBA74 \uC815\uBCF4: ${JSON.stringify(context || {})}
\uC5F0\uACB0\uB41C \uACF5\uC2DD \uC790\uB8CC:
${sourceSummary}
`;
      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: [{ role: "user", parts: [{ text: `${systemInstruction}

\uC9C8\uBB38: ${prompt}` }] }]
      });
      res.json({
        reply: response.text || "\uB2F5\uBCC0\uC744 \uC0DD\uC131\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.",
        sources: officialData.sources.map((source) => `${source.nameKo} \u2014 ${source.url}`)
      });
    } catch (error) {
      console.error("AI assistant error:", error);
      res.status(500).json({
        error: "AI \uB3C4\uC6B0\uBBF8 \uC694\uCCAD\uC744 \uCC98\uB9AC\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.",
        details: error?.message || String(error)
      });
    }
  });
  if (process.env.NODE_ENV !== "production") {
    const vite = await (0, import_vite.createServer)({ server: { middlewareMode: true }, appType: "spa" });
    app.use(vite.middlewares);
  } else {
    const distPath = import_path.default.join(process.cwd(), "dist");
    app.use(import_express.default.static(distPath));
    app.get("*", (_req, res) => res.sendFile(import_path.default.join(distPath, "index.html")));
  }
  app.listen(PORT, "0.0.0.0", () => {
    console.log(`US export tariff pre-check server running on http://0.0.0.0:${PORT}`);
  });
}
startServer();
//# sourceMappingURL=server.cjs.map
