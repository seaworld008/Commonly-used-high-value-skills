#!/usr/bin/env node

import fsSync from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT_PROMPT = "";
const DEFAULT_MODEL = "gpt-image-2";
const DEFAULT_BASE_URL = "";
const DEFAULT_TIMEOUT_MS = 240_000;
const DEFAULT_N = 1;
const DEFAULT_RESOLUTION = "1k";
const DEFAULT_ASPECT_RATIO = "1:1";
const DEFAULT_MODE = "current";
const DEFAULT_CURRENT_QUALITY = "low";
const MAX_REFERENCE_IMAGES = 16;
const MAX_REFERENCE_IMAGE_BYTES = 10 * 1024 * 1024;
const SUPPORTED_MODES = new Set(["current", "official-compatible"]);
const SUPPORTED_QUALITIES = new Set(["auto", "low", "medium", "high"]);
const SUPPORTED_RESOLUTIONS = new Set(["1k", "2k", "4k"]);
const SUPPORTED_ASPECT_RATIOS = new Set([
  "1:1",
  "3:2",
  "2:3",
  "4:3",
  "3:4",
  "5:4",
  "4:5",
  "16:9",
  "9:16",
  "2:1",
  "1:2",
  "21:9",
  "9:21",
]);
const OFFICIAL_PRESET_SIZES = new Map([
  ["1k|1:1", "1024x1024"],
  ["1k|3:2", "1536x1024"],
  ["1k|2:3", "1024x1536"],
  ["2k|1:1", "2048x2048"],
  ["2k|16:9", "2048x1152"],
  ["4k|16:9", "3840x2160"],
  ["4k|9:16", "2160x3840"],
]);
const IMAGE_MIME_BY_EXT = new Map([
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".webp", "image/webp"],
  [".gif", "image/gif"],
  [".bmp", "image/bmp"],
  [".avif", "image/avif"],
  [".heic", "image/heic"],
  [".heif", "image/heif"],
  [".tif", "image/tiff"],
  [".tiff", "image/tiff"],
]);
const SUPPORTED_REFERENCE_IMAGE_MIME_TYPES = new Set(IMAGE_MIME_BY_EXT.values());

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DOTENV_PATH = path.join(__dirname, ".env");
const CODEX_CONFIG_PATH = path.join(process.env.USERPROFILE || process.env.HOME || "", ".codex", "config.toml");
const CODEX_AUTH_PATH = path.join(process.env.USERPROFILE || process.env.HOME || "", ".codex", "auth.json");
const API_KEY_ENV_KEYS = [
  "GPT_IMAGE2_API_KEY",
  "OPENAI_API_KEY",
  "CODEX_OPENAI_API_KEY",
];
const BASE_URL_ENV_KEYS = [
  "GPT_IMAGE2_BASE_URL",
  "OPENAI_BASE_URL",
  "OPENAI_API_BASE_URL",
  "OPENAI_API_BASE",
  "CODEX_OPENAI_BASE_URL",
  "CODEX_OPENAI_API_BASE_URL",
];

function nowText() {
  return new Date().toTimeString().slice(0, 8);
}

function timestampText() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    "_",
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds()),
  ].join("");
}

function printHelp() {
  console.log(`用法:
  node gpt-image2.mjs [prompt]
  node gpt-image2.mjs --prompt "提示词"

可选参数:
  -p, --prompt <text>      提示词，优先级高于位置参数
  -m, --model <name>       模型名，默认读取 .env 的 GPT_IMAGE2_MODEL，未设置则 ${DEFAULT_MODEL}
  -n <count>               生成张数，默认读取 .env 的 GPT_IMAGE2_N，未设置则 ${DEFAULT_N}
  -i, --image <path>       参考图路径，可重复传入；有参考图时固定输出 1 张
  --reference <path>       --image 的别名
  --reference-image <path> --image 的别名
  --mode <current|official-compatible>
                            内部请求模式，默认读取 .env 的 GPT_IMAGE2_MODE，未设置则 ${DEFAULT_MODE}
  --resolution <1k|2k|4k>  分辨率；未指定时默认读取 .env 的 GPT_IMAGE2_RESOLUTION，未设置则 ${DEFAULT_RESOLUTION.toUpperCase()}
  --aspect-ratio <ratio>   宽高比，例如 1:1、16:9、9:16；未指定时默认读取 .env 的 GPT_IMAGE2_ASPECT_RATIO，未设置则 ${DEFAULT_ASPECT_RATIO}
  --quality <auto|low|medium|high>
                            默认画图通道未指定时使用 low；官方兼容模式未指定则不传
  --base-url <url>         接口地址；默认读取 GPT_IMAGE2_BASE_URL，再回退到 OpenAI/Codex 环境变量和 Codex 配置
  --api-key <key>          API Key；默认读取 GPT_IMAGE2_API_KEY，再回退到 OpenAI/Codex 环境变量和 Codex auth.json
  --out-dir <path>         输出目录，默认读取 .env 的 GPT_IMAGE2_OUT_DIR，未设置则 ./image2_output
  --timeout-ms <number>    请求超时毫秒数，默认读取 .env 的 GPT_IMAGE2_TIMEOUT_MS，未设置则 ${DEFAULT_TIMEOUT_MS}
  --dry-run                只打印将要请求的 URL 和请求形态，不调用接口、不扣费
  -h, --help               显示帮助
`);
}

function loadDotEnv(filePath) {
  if (!fsSync.existsSync(filePath)) {
    return {};
  }

  const content = fsSync.readFileSync(filePath, "utf8");
  const env = {};

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const splitIndex = line.indexOf("=");
    if (splitIndex === -1) {
      continue;
    }

    const key = line.slice(0, splitIndex).trim();
    let value = line.slice(splitIndex + 1).trim();
    if (!key) {
      continue;
    }

    const hasWrappedQuotes =
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"));
    if (hasWrappedQuotes) {
      value = value.slice(1, -1);
    }

    env[key] = value;
  }

  return env;
}

function pickConfigValue(dotenvConfig, keys, fallback = "") {
  for (const key of keys) {
    const processValue = process.env[key];
    if (processValue && String(processValue).trim()) {
      return String(processValue).trim();
    }
  }
  for (const key of keys) {
    const dotenvValue = dotenvConfig[key];
    if (dotenvValue && String(dotenvValue).trim()) {
      return String(dotenvValue).trim();
    }
  }
  return fallback;
}

function parseTomlStringValue(rawValue) {
  const value = String(rawValue || "").trim();
  if (!value) {
    return "";
  }
  const hashIndex = value.indexOf("#");
  const uncommented = hashIndex >= 0 ? value.slice(0, hashIndex).trim() : value;
  const hasDoubleQuotes = uncommented.startsWith('"') && uncommented.endsWith('"');
  const hasSingleQuotes = uncommented.startsWith("'") && uncommented.endsWith("'");
  if (hasDoubleQuotes || hasSingleQuotes) {
    return uncommented.slice(1, -1);
  }
  return uncommented;
}

function readCodexProviderBaseUrl(configPath = CODEX_CONFIG_PATH) {
  if (!configPath || !fsSync.existsSync(configPath)) {
    return "";
  }

  const content = fsSync.readFileSync(configPath, "utf8");
  let activeProvider = "";
  let currentSection = "";
  const providerBaseUrls = new Map();

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const sectionMatch = line.match(/^\[(.+)]$/);
    if (sectionMatch) {
      currentSection = sectionMatch[1].trim();
      continue;
    }

    const splitIndex = line.indexOf("=");
    if (splitIndex === -1) {
      continue;
    }
    const key = line.slice(0, splitIndex).trim();
    const value = parseTomlStringValue(line.slice(splitIndex + 1));
    if (!value) {
      continue;
    }

    if (!currentSection && key === "model_provider") {
      activeProvider = value;
      continue;
    }

    const providerMatch = currentSection.match(/^model_providers\.(.+)$/);
    if (providerMatch && key === "base_url") {
      const providerName = providerMatch[1].replace(/^["']|["']$/g, "");
      providerBaseUrls.set(providerName, value);
    }
  }

  if (activeProvider && providerBaseUrls.has(activeProvider)) {
    return providerBaseUrls.get(activeProvider);
  }
  if (providerBaseUrls.size === 1) {
    return Array.from(providerBaseUrls.values())[0];
  }
  return "";
}

function readCodexAuthApiKey(authPath = CODEX_AUTH_PATH) {
  if (!authPath || !fsSync.existsSync(authPath)) {
    return "";
  }

  try {
    const payload = JSON.parse(fsSync.readFileSync(authPath, "utf8"));
    const apiKey = payload?.OPENAI_API_KEY;
    return apiKey && String(apiKey).trim() ? String(apiKey).trim() : "";
  } catch {
    return "";
  }
}

function parsePositiveInt(value, name) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${name} 必须是正整数`);
  }
  return parsed;
}

function normalizeOptionalResolution(value, name) {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) {
    return "";
  }
  if (!SUPPORTED_RESOLUTIONS.has(normalized)) {
    throw new Error(`${name} 只能是 1k、2k 或 4k`);
  }
  return normalized;
}

function normalizeOptionalAspectRatio(value, name) {
  const normalized = String(value || "").trim();
  if (!normalized) {
    return "";
  }
  if (!SUPPORTED_ASPECT_RATIOS.has(normalized)) {
    throw new Error(`${name} 不支持: ${normalized}`);
  }
  return normalized;
}

function normalizeMode(value, name) {
  const raw = String(value || "").trim().toLowerCase();
  const normalized = raw === "openai" || raw === "official" || raw === "openai-compatible"
    ? "official-compatible"
    : raw;
  if (!normalized) {
    return DEFAULT_MODE;
  }
  if (!SUPPORTED_MODES.has(normalized)) {
    throw new Error(`${name} 只能是 current 或 official-compatible`);
  }
  return normalized;
}

function normalizeOptionalQuality(value, name) {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) {
    return "";
  }
  if (!SUPPORTED_QUALITIES.has(normalized)) {
    throw new Error(`${name} 只能是 auto、low、medium 或 high`);
  }
  return normalized;
}

function greatestCommonDivisor(a, b) {
  let x = Math.abs(a);
  let y = Math.abs(b);
  while (y !== 0) {
    const next = x % y;
    x = y;
    y = next;
  }
  return x;
}

function leastCommonMultiple(a, b) {
  if (a <= 0 || b <= 0) {
    return 0;
  }
  return Math.floor((a / greatestCommonDivisor(a, b)) * b);
}

function resolveOfficialImageSize(resolution, aspectRatio) {
  const normalizedResolution = normalizeOptionalResolution(resolution || DEFAULT_RESOLUTION, "--resolution");
  const normalizedRatio = normalizeOptionalAspectRatio(aspectRatio || DEFAULT_ASPECT_RATIO, "--aspect-ratio");
  const preset = OFFICIAL_PRESET_SIZES.get(`${normalizedResolution}|${normalizedRatio}`);
  if (preset) {
    return preset;
  }

  const parts = normalizedRatio.split(":").map((part) => Number.parseInt(part, 10));
  if (parts.length !== 2 || parts.some((part) => !Number.isInteger(part) || part <= 0)) {
    throw new Error(`不支持的宽高比: ${normalizedRatio}`);
  }
  let [rawW, rawH] = parts;
  let ratioValue = rawW / rawH;
  if (ratioValue < 1) {
    ratioValue = 1 / ratioValue;
  }
  if (ratioValue > 3) {
    throw new Error(`不支持的宽高比: ${normalizedRatio}`);
  }

  const targetPixelsByResolution = {
    "1k": 1_048_576,
    "2k": 4_194_304,
    "4k": 8_294_400,
  };
  const reducedDivisor = greatestCommonDivisor(rawW, rawH);
  const ratioW = rawW / reducedDivisor;
  const ratioH = rawH / reducedDivisor;
  const widthStep = 16 / greatestCommonDivisor(ratioW, 16);
  const heightStep = 16 / greatestCommonDivisor(ratioH, 16);
  const unit = leastCommonMultiple(widthStep, heightStep);
  if (unit <= 0) {
    throw new Error(`不支持的宽高比: ${normalizedRatio}`);
  }
  const maxScaleBySide = Math.min(3840 / ratioW, 3840 / ratioH);
  const maxScaleByPixels = Math.sqrt(targetPixelsByResolution[normalizedResolution] / (ratioW * ratioH));
  const maxScale = Math.min(maxScaleBySide, maxScaleByPixels);
  const scale = Math.floor(maxScale / unit) * unit;
  if (scale <= 0) {
    throw new Error(`不支持的宽高比: ${normalizedRatio}`);
  }
  const width = ratioW * scale;
  const height = ratioH * scale;
  const pixels = width * height;
  if (pixels < 655_360 || pixels > 8_294_400) {
    throw new Error(`不支持的分辨率/宽高比组合: ${normalizedResolution} ${normalizedRatio}`);
  }
  return `${width}x${height}`;
}

function resolveOutputDir(outDir) {
  return path.isAbsolute(outDir) ? outDir : path.resolve(process.cwd(), outDir);
}

function resolveInputPath(inputPath) {
  return path.isAbsolute(inputPath) ? inputPath : path.resolve(process.cwd(), inputPath);
}

function parseArgs(argv, dotenvConfig) {
  let promptFlag = null;
  const positionals = [];
  const options = {
    model: process.env.GPT_IMAGE2_MODEL || dotenvConfig.GPT_IMAGE2_MODEL || DEFAULT_MODEL,
    n: parsePositiveInt(
      process.env.GPT_IMAGE2_N || dotenvConfig.GPT_IMAGE2_N || String(DEFAULT_N),
      "GPT_IMAGE2_N",
    ),
    mode: normalizeMode(
      process.env.GPT_IMAGE2_MODE ||
        dotenvConfig.GPT_IMAGE2_MODE ||
        DEFAULT_MODE,
      "GPT_IMAGE2_MODE",
    ),
    resolution: normalizeOptionalResolution(
      process.env.GPT_IMAGE2_RESOLUTION ||
        dotenvConfig.GPT_IMAGE2_RESOLUTION ||
        DEFAULT_RESOLUTION,
      "GPT_IMAGE2_RESOLUTION",
    ),
    aspectRatio: normalizeOptionalAspectRatio(
      process.env.GPT_IMAGE2_ASPECT_RATIO ||
        dotenvConfig.GPT_IMAGE2_ASPECT_RATIO ||
        DEFAULT_ASPECT_RATIO,
      "GPT_IMAGE2_ASPECT_RATIO",
    ),
    quality: normalizeOptionalQuality(
      process.env.GPT_IMAGE2_QUALITY || dotenvConfig.GPT_IMAGE2_QUALITY || "",
      "GPT_IMAGE2_QUALITY",
    ),
    baseUrl: pickConfigValue(dotenvConfig, BASE_URL_ENV_KEYS, readCodexProviderBaseUrl() || DEFAULT_BASE_URL),
    apiKey: pickConfigValue(dotenvConfig, API_KEY_ENV_KEYS, readCodexAuthApiKey()),
    outDir: resolveOutputDir(
      process.env.GPT_IMAGE2_OUT_DIR || dotenvConfig.GPT_IMAGE2_OUT_DIR || "./image2_output",
    ),
    timeoutMs: parsePositiveInt(
      process.env.GPT_IMAGE2_TIMEOUT_MS ||
        dotenvConfig.GPT_IMAGE2_TIMEOUT_MS ||
        String(DEFAULT_TIMEOUT_MS),
      "GPT_IMAGE2_TIMEOUT_MS",
    ),
    dryRun: false,
    images: [],
  };

  const readValue = (index, arg) => {
    const value = argv[index + 1];
    if (!value || value.startsWith("-")) {
      throw new Error(`${arg} 需要一个值`);
    }
    return value;
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];

    if (arg === "-h" || arg === "--help") {
      printHelp();
      process.exit(0);
    }

    if (arg === "-p" || arg === "--prompt") {
      promptFlag = readValue(i, arg);
      i += 1;
      continue;
    }

    if (arg === "-m" || arg === "--model") {
      options.model = readValue(i, arg);
      i += 1;
      continue;
    }

    if (arg === "--mode") {
      options.mode = normalizeMode(readValue(i, arg), arg);
      i += 1;
      continue;
    }

    if (arg === "-n") {
      options.n = parsePositiveInt(readValue(i, arg), "-n");
      i += 1;
      continue;
    }

    if (arg === "-i" || arg === "--image" || arg === "--reference" || arg === "--reference-image") {
      options.images.push(resolveInputPath(readValue(i, arg)));
      i += 1;
      continue;
    }

    if (arg === "--resolution") {
      options.resolution = normalizeOptionalResolution(readValue(i, arg), "--resolution");
      i += 1;
      continue;
    }

    if (arg === "--aspect-ratio") {
      options.aspectRatio = normalizeOptionalAspectRatio(readValue(i, arg), "--aspect-ratio");
      i += 1;
      continue;
    }

    if (arg === "--quality") {
      options.quality = normalizeOptionalQuality(readValue(i, arg), "--quality");
      i += 1;
      continue;
    }

    if (arg === "--base-url") {
      options.baseUrl = readValue(i, arg);
      i += 1;
      continue;
    }

    if (arg === "--api-key") {
      options.apiKey = readValue(i, arg);
      i += 1;
      continue;
    }

    if (arg === "--out-dir") {
      options.outDir = resolveOutputDir(readValue(i, arg));
      i += 1;
      continue;
    }

    if (arg === "--timeout-ms") {
      options.timeoutMs = parsePositiveInt(readValue(i, arg), "--timeout-ms");
      i += 1;
      continue;
    }

    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }

    if (arg.startsWith("-")) {
      throw new Error(`未知参数: ${arg}`);
    }

    positionals.push(arg);
  }

  const parsedOptions = {
    ...options,
    prompt: promptFlag || positionals.join(" ") || DEFAULT_PROMPT,
  };
  if (!parsedOptions.prompt) {
    throw new Error("缺少提示词，请通过位置参数或 --prompt 传入");
  }
  if (!parsedOptions.aspectRatio) {
    parsedOptions.aspectRatio = DEFAULT_ASPECT_RATIO;
  }
  return parsedOptions;
}

function inferMimeTypeFromMagic(raw) {
  if (raw.length >= 8 && raw.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) {
    return "image/png";
  }
  if (raw.length >= 3 && raw[0] === 0xff && raw[1] === 0xd8 && raw[2] === 0xff) {
    return "image/jpeg";
  }
  if (raw.length >= 12 && raw.subarray(0, 4).toString("ascii") === "RIFF" && raw.subarray(8, 12).toString("ascii") === "WEBP") {
    return "image/webp";
  }
  if (raw.length >= 6) {
    const gifHeader = raw.subarray(0, 6).toString("ascii");
    if (gifHeader === "GIF87a" || gifHeader === "GIF89a") {
      return "image/gif";
    }
  }
  if (raw.length >= 2 && raw.subarray(0, 2).toString("ascii") === "BM") {
    return "image/bmp";
  }
  if (raw.length >= 12 && raw.subarray(4, 8).toString("ascii") === "ftyp") {
    const brand = raw.subarray(8, 12).toString("ascii").trim();
    if (brand === "avif" || brand === "avis") {
      return "image/avif";
    }
    if (brand === "heic" || brand === "heix" || brand === "hevc" || brand === "hevx" || brand === "mif1" || brand === "msf1") {
      return "image/heic";
    }
  }
  if (
    raw.length >= 4 &&
    ((raw[0] === 0x49 && raw[1] === 0x49 && raw[2] === 0x2a && raw[3] === 0x00) ||
      (raw[0] === 0x4d && raw[1] === 0x4d && raw[2] === 0x00 && raw[3] === 0x2a))
  ) {
    return "image/tiff";
  }
  return "";
}

function inferReferenceImageMimeType(filePath, raw) {
  return inferMimeTypeFromMagic(raw) || IMAGE_MIME_BY_EXT.get(path.extname(filePath).toLowerCase()) || "";
}

async function loadReferenceImages(imagePaths) {
  if (imagePaths.length > MAX_REFERENCE_IMAGES) {
    throw new Error(`参考图最多支持 ${MAX_REFERENCE_IMAGES} 张`);
  }

  const images = [];
  for (const imagePath of imagePaths) {
    const stat = await fs.stat(imagePath).catch((error) => {
      throw new Error(`参考图不存在或无法读取: ${imagePath} (${error.message})`);
    });
    if (!stat.isFile()) {
      throw new Error(`参考图不是文件: ${imagePath}`);
    }
    if (stat.size <= 0) {
      throw new Error(`参考图为空文件: ${imagePath}`);
    }
    if (stat.size > MAX_REFERENCE_IMAGE_BYTES) {
      throw new Error(`参考图超过 10MB 限制: ${imagePath}`);
    }

    const raw = await fs.readFile(imagePath);
    const mimeType = inferReferenceImageMimeType(imagePath, raw);
    if (!SUPPORTED_REFERENCE_IMAGE_MIME_TYPES.has(mimeType)) {
      throw new Error(`参考图格式不支持或无法识别: ${imagePath}`);
    }

    images.push({
      path: imagePath,
      filename: path.basename(imagePath),
      mimeType,
      raw,
      sizeBytes: raw.length,
    });
  }
  return images;
}

function decodeImageField(value) {
  let payload = value.trim();
  let mimeType = null;

  if (payload.startsWith("data:")) {
    const splitIndex = payload.indexOf(",");
    if (splitIndex === -1) {
      throw new Error("data URL 缺少逗号分隔符");
    }
    const header = payload.slice(5, splitIndex);
    payload = payload.slice(splitIndex + 1);
    mimeType = header.split(";", 1)[0] || null;
  }

  payload = payload.replace(/\s+/g, "");
  const missingPadding = (4 - (payload.length % 4)) % 4;
  if (missingPadding > 0) {
    payload += "=".repeat(missingPadding);
  }

  return {
    raw: Buffer.from(payload, "base64"),
    mimeType,
  };
}

function suffixFromMime(mimeType) {
  if (mimeType === "image/jpeg") {
    return ".jpg";
  }
  if (mimeType === "image/webp") {
    return ".webp";
  }
  return ".png";
}

function suffixFromURL(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    const ext = path.extname(parsed.pathname).toLowerCase();
    if ([".png", ".jpg", ".jpeg", ".webp", ".gif"].includes(ext)) {
      return ext === ".jpeg" ? ".jpg" : ext;
    }
  } catch {
    // Ignore invalid URL parsing here; fetch will report the useful error.
  }
  return ".png";
}

function joinUrl(baseUrl, suffix) {
  return `${baseUrl.replace(/\/+$/, "")}${suffix}`;
}

async function parseJsonResponse(response) {
  const text = await response.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }

  if (!response.ok) {
    const detail = json ? JSON.stringify(json) : text;
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }

  if (!json) {
    throw new Error("接口返回了空响应或非 JSON 内容");
  }

  return json;
}

async function requestJson(url, body, apiKey, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    return await parseJsonResponse(response);
  } finally {
    clearTimeout(timer);
  }
}

async function requestMultipart(url, fields, images, apiKey, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const form = new FormData();

  for (const [key, value] of Object.entries(fields)) {
    if (value !== undefined && value !== null && value !== "") {
      form.append(key, String(value));
    }
  }
  for (const image of images) {
    form.append("image", new Blob([image.raw], { type: image.mimeType }), image.filename);
  }

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        authorization: `Bearer ${apiKey}`,
      },
      body: form,
      signal: controller.signal,
    });

    return await parseJsonResponse(response);
  } finally {
    clearTimeout(timer);
  }
}

async function downloadImageURL(url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: "GET",
      signal: controller.signal,
    });
    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`download HTTP ${response.status}: ${text.slice(0, 500)}`);
    }

    const contentType = (response.headers.get("content-type") || "").split(";", 1)[0].trim();
    if (contentType && !contentType.startsWith("image/")) {
      throw new Error(`download returned non-image content-type: ${contentType}`);
    }

    const arrayBuffer = await response.arrayBuffer();
    return {
      raw: Buffer.from(arrayBuffer),
      mimeType: contentType || null,
    };
  } finally {
    clearTimeout(timer);
  }
}

async function main() {
  const dotenvConfig = loadDotEnv(DOTENV_PATH);
  const options = parseArgs(process.argv.slice(2), dotenvConfig);
  if (!options.apiKey) {
    throw new Error("缺少接口配置，请设置 GPT_IMAGE2_API_KEY、OPENAI_API_KEY、CODEX_OPENAI_API_KEY，或在 Codex auth.json 中配置 OPENAI_API_KEY");
  }
  if (!options.baseUrl) {
    throw new Error("缺少接口配置，请设置 GPT_IMAGE2_BASE_URL、OPENAI_BASE_URL、CODEX_OPENAI_BASE_URL，或在 Codex config.toml 的当前 model_provider 中配置 base_url");
  }

  console.log(`[${nowText()}] prompt: ${options.prompt}`);
  const imageSize = resolveOfficialImageSize(options.resolution, options.aspectRatio);
  const hasReferenceImages = options.images.length > 0;
  const referenceImages = hasReferenceImages ? await loadReferenceImages(options.images) : [];
  const quality = options.quality || (options.mode === "current" ? DEFAULT_CURRENT_QUALITY : "");

  console.log(
    `[${nowText()}] options: resolution=${options.resolution}, aspect_ratio=${options.aspectRatio}, size=${imageSize}${quality ? `, quality=${quality}` : ""}${hasReferenceImages ? `, reference_images=${referenceImages.length}, output=1` : `, output=${options.n}`}`,
  );

  let requestUrl = "";
  let requestBody = null;
  let resp = null;

  if (hasReferenceImages) {
    requestUrl = joinUrl(options.baseUrl, "/images/edits");
    requestBody = {
      model: options.model,
      prompt: options.prompt,
      size: imageSize,
    };
    if (quality) {
      requestBody.quality = quality;
    }

    if (options.dryRun) {
      console.log(`[${nowText()}] dry-run url: ${requestUrl}`);
      console.log(JSON.stringify({
        fields: requestBody,
        reference_images: referenceImages.map((image) => ({
          path: image.path,
          filename: image.filename,
          mime_type: image.mimeType,
          size_bytes: image.sizeBytes,
        })),
        output_count: 1,
      }, null, 2));
      return;
    }

    const start = Date.now();
    resp = await requestMultipart(requestUrl, requestBody, referenceImages, options.apiKey, options.timeoutMs);
    const elapsedSeconds = (Date.now() - start) / 1000;
    console.log(`[${nowText()}] 耗时 ${elapsedSeconds.toFixed(1)}s`);
  } else {
    requestUrl = joinUrl(options.baseUrl, "/images/generations");
    requestBody = {
      model: options.model,
      prompt: options.prompt,
      n: options.n,
      size: imageSize,
    };
    if (quality) {
      requestBody.quality = quality;
    }

    if (options.dryRun) {
      console.log(`[${nowText()}] dry-run url: ${requestUrl}`);
      console.log(JSON.stringify(requestBody, null, 2));
      return;
    }

    const start = Date.now();
    resp = await requestJson(requestUrl, requestBody, options.apiKey, options.timeoutMs);
    const elapsedSeconds = (Date.now() - start) / 1000;
    console.log(`[${nowText()}] 耗时 ${elapsedSeconds.toFixed(1)}s`);
  }

  console.log(`resp.created = ${resp.created}`);
  console.log(`resp.usage = ${resp.usage ?? null}`);

  await fs.mkdir(options.outDir, { recursive: true });
  const ts = timestampText();
  const responseData = Array.isArray(resp.data) ? resp.data : [];
  if (hasReferenceImages && responseData.length > 1) {
    console.log(`[${nowText()}] reference image mode returned ${responseData.length} images; saving the first one only`);
  }
  const data = hasReferenceImages ? responseData.slice(0, 1) : responseData;

  for (const [index, img] of data.entries()) {
    console.log(
      `  [${index}] model=${img?.model ?? null} revised_prompt=${img?.revised_prompt ?? null}`,
    );

    if (img?.b64_json) {
      const { raw, mimeType } = decodeImageField(img.b64_json);
      const filename = path.join(
        options.outDir,
        `gpt-image2_${ts}_${index + 1}${suffixFromMime(mimeType)}`,
      );
      await fs.writeFile(filename, raw);
      console.log(
        `  [${index}] saved ${filename} (${raw.length.toLocaleString()} bytes, header=${JSON.stringify(raw.subarray(0, 8).toString("latin1"))})`,
      );
      continue;
    }

    if (img?.url) {
      console.log(`  [${index}] image url = ${img.url}`);
      const { raw, mimeType } = await downloadImageURL(img.url, options.timeoutMs);
      const suffix = mimeType ? suffixFromMime(mimeType) : suffixFromURL(img.url);
      const filename = path.join(options.outDir, `gpt-image2_${ts}_${index + 1}${suffix}`);
      await fs.writeFile(filename, raw);
      console.log(
        `  [${index}] saved ${filename} (${raw.length.toLocaleString()} bytes, source=url, content_type=${mimeType ?? "unknown"}, header=${JSON.stringify(raw.subarray(0, 8).toString("latin1"))})`,
      );
      continue;
    }

    console.log(`  [${index}] no image payload found`);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
