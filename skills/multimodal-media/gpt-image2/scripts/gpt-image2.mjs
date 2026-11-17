#!/usr/bin/env node

import fsSync from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { inflateSync } from "node:zlib";

const DEFAULT_PROMPT = "";
const DEFAULT_MODEL = "gpt-image-2";
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
  --base-url <url>         接口地址，支持 GPT_IMAGE2_BASE_URL 及 OpenAI/Codex 兼容环境变量
  --api-key <key>          API Key，支持 GPT_IMAGE2_API_KEY 及 OpenAI/Codex 兼容环境变量
  --use-codex-auth         允许在宿主权限内读取本地 Codex 配置，仅补充参数、环境变量和 .env 缺少的地址或密钥
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
  const value = rawValue.trim();
  if (/^'[^']*'$/.test(value)) return value.slice(1, -1);
  if (value.startsWith('"')) {
    try {
      return JSON.parse(value);
    } catch {
      return "";
    }
  }
  return "";
}

function readCodexProviderBaseUrl(configPath) {
  if (!configPath || !fsSync.existsSync(configPath)) {
    return "";
  }

  const content = fsSync.readFileSync(configPath, "utf8");
  let activeProvider = "";
  let currentSection = "";

  // Ignore comments and multiline string contents, which may contain example tables.
  const token = /"""(?:\\[\s\S]|"(?!"")|[^"\\])*"{3,5}|'''[\s\S]*?'{3,5}|"(?:\\.|[^"\\\n])*"|'[^'\n]*'|#[^\n]*/g;
  const settings = content.replace(token, (match) => {
    if (match.startsWith("#")) return "";
    if (match.startsWith('"""') || match.startsWith("'''")) return '""';
    return match;
  });
  for (const rawLine of settings.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) {
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
    if (!currentSection && key === "model_provider") {
      activeProvider = parseTomlStringValue(line.slice(splitIndex + 1));
    } else if (activeProvider && key === "base_url") {
      const provider = currentSection.match(/^model_providers\s*\.\s*([\w-]+|"[^"\\]+"|'[^']+')$/);
      if (provider?.[1].replace(/^["']|["']$/g, "") === activeProvider) {
        return parseTomlStringValue(line.slice(splitIndex + 1));
      }
    }
  }

  return "";
}

function readCodexAuthApiKey(authPath) {
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
  let useCodexAuth = false;
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
    baseUrl: pickConfigValue(dotenvConfig, BASE_URL_ENV_KEYS),
    apiKey: pickConfigValue(dotenvConfig, API_KEY_ENV_KEYS),
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

    if (arg === "--use-codex-auth") {
      useCodexAuth = true;
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
  const home = useCodexAuth && (process.env.USERPROFILE || process.env.HOME);
  const codex = home && path.isAbsolute(home) ? path.join(home, ".codex") : null;
  if (codex && !parsedOptions.baseUrl) {
    parsedOptions.baseUrl = readCodexProviderBaseUrl(path.join(codex, "config.toml"));
  }
  if (parsedOptions.baseUrl) {
    parsedOptions.baseUrl = serviceRoot(parsedOptions.baseUrl);
    if (codex && !parsedOptions.apiKey) {
      parsedOptions.apiKey = readCodexAuthApiKey(path.join(codex, "auth.json"));
    }
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

function inferReferenceImageMimeType(raw) {
  return inferMimeTypeFromMagic(raw);
}

function requireImageStructure(condition) {
  if (!condition) throw new Error("图片结构不完整、编码错误或格式尚不支持校验");
}

const PNG_CRC_TABLE = Array.from({ length: 256 }, (_, value) => {
  for (let bit = 0; bit < 8; bit += 1) value = (value >>> 1) ^ ((value & 1) ? 0xedb88320 : 0);
  return value >>> 0;
});

function validatePNG(raw) {
  let offset = 8;
  let header;
  let palette = false;
  let dataEnded = false;
  const compressed = [];
  while (offset + 12 <= raw.length) {
    const length = raw.readUInt32BE(offset);
    const end = offset + 12 + length;
    requireImageStructure(end <= raw.length);
    const type = raw.toString("latin1", offset + 4, offset + 8);
    requireImageStructure(/^[A-Za-z]{4}$/.test(type) && type[2] === type[2].toUpperCase());
    let crc = 0xffffffff;
    for (let i = offset + 4; i < end - 4; i += 1) crc = PNG_CRC_TABLE[(crc ^ raw[i]) & 255] ^ (crc >>> 8);
    requireImageStructure(((crc ^ 0xffffffff) >>> 0) === raw.readUInt32BE(end - 4));
    const chunk = raw.subarray(offset + 8, end - 4);
    requireImageStructure(header || type === "IHDR");
    if (type === "IHDR") {
      requireImageStructure(!header && length === 13);
      header = chunk;
      const depths = { 0: [1, 2, 4, 8, 16], 2: [8, 16], 3: [1, 2, 4, 8], 4: [8, 16], 6: [8, 16] };
      requireImageStructure(chunk.readUInt32BE(0) > 0 && chunk.readUInt32BE(0) <= 0x7fffffff &&
        chunk.readUInt32BE(4) > 0 && chunk.readUInt32BE(4) <= 0x7fffffff &&
        depths[chunk[9]]?.includes(chunk[8]) && chunk[10] === 0 && chunk[11] === 0 && chunk[12] <= 1);
    } else if (type === "PLTE") {
      requireImageStructure(!palette && !compressed.length && length > 0 && length <= 768 && length % 3 === 0 &&
        ![0, 4].includes(header[9]) && (header[9] !== 3 || length / 3 <= 2 ** header[8]));
      palette = true;
    } else if (type === "IDAT") {
      requireImageStructure(!dataEnded && (header[9] !== 3 || palette));
      compressed.push(chunk);
    } else if (type === "IEND") {
      requireImageStructure(length === 0 && end === raw.length && compressed.length > 0);
      const width = header.readUInt32BE(0);
      const height = header.readUInt32BE(4);
      const bits = ({ 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 })[header[9]] * header[8];
      // Adam7 uses seven independently filtered passes; no pixel reconstruction is done.
      const passes = header[12] ? [[0, 0, 8, 8], [4, 0, 8, 8], [0, 4, 4, 8],
        [2, 0, 4, 4], [0, 2, 2, 4], [1, 0, 2, 2], [0, 1, 1, 2]] : [[0, 0, 1, 1]];
      const rows = passes.map(([x, y, dx, dy]) => {
        const w = Math.max(0, Math.ceil((width - x) / dx));
        const h = Math.max(0, Math.ceil((height - y) / dy));
        return [w ? 1 + Math.ceil(w * bits / 8) : 0, h];
      });
      const expected = rows.reduce((total, [stride, h]) => total + stride * h, 0);
      requireImageStructure(expected > 0 && expected <= 256 * 1024 * 1024);
      const packed = Buffer.concat(compressed);
      const inflated = inflateSync(packed, { maxOutputLength: expected, info: true });
      requireImageStructure(inflated.engine.bytesWritten === packed.length && inflated.buffer.length === expected);
      let rowOffset = 0;
      for (const [stride, h] of rows) {
        if (!stride) continue;
        for (let row = 0; row < h; row += 1, rowOffset += stride) requireImageStructure(inflated.buffer[rowOffset] <= 4);
      }
      return;
    } else {
      // Unknown critical chunks and animation need a decoder we do not bundle.
      requireImageStructure(type[0] === type[0].toLowerCase() && !["acTL", "fcTL", "fdAT"].includes(type));
    }
    if (compressed.length && type !== "IDAT") dataEnded = true;
    offset = end;
  }
  requireImageStructure(false);
}

function validateJPEG(raw) {
  let offset = 2;
  let frame;
  let scans = 0;
  const quantization = new Set();
  const huffman = new Set();
  const dcComponents = new Set();
  while (offset < raw.length) {
    requireImageStructure(raw[offset++] === 0xff);
    while (raw[offset] === 0xff) offset += 1;
    const marker = raw[offset++];
    if (marker === 0xd9) {
      requireImageStructure(frame && scans > 0 && dcComponents.size === frame.components.size && offset === raw.length);
      return;
    }
    requireImageStructure(offset + 2 <= raw.length);
    const length = raw.readUInt16BE(offset);
    requireImageStructure(length >= 2 && offset + length <= raw.length);
    const segment = raw.subarray(offset + 2, offset + length);
    offset += length;
    if ([0xc0, 0xc1, 0xc2].includes(marker)) {
      requireImageStructure(!frame && segment.length >= 6 && segment[0] === 8 &&
        segment.readUInt16BE(1) > 0 && segment.readUInt16BE(3) > 0 &&
        segment[5] >= 1 && segment[5] <= 4 && segment.length === 6 + 3 * segment[5]);
      const components = new Map();
      for (let i = 6; i < segment.length; i += 3) {
        requireImageStructure(!components.has(segment[i]) && (segment[i + 1] >> 4) >= 1 && (segment[i + 1] >> 4) <= 4 &&
          (segment[i + 1] & 15) >= 1 && (segment[i + 1] & 15) <= 4 && segment[i + 2] <= 3);
        components.set(segment[i], segment[i + 2]);
      }
      frame = { marker, components };
    } else if (marker === 0xdb || marker === 0xc4) {
      let pos = 0;
      while (pos < segment.length) {
        const selector = segment[pos++];
        requireImageStructure((selector & 15) <= 3 && (selector >> 4) <= 1);
        if (marker === 0xdb) {
          const bytes = 1 + (selector >> 4);
          requireImageStructure(pos + 64 * bytes <= segment.length);
          for (let i = 0; i < 64; i += 1, pos += bytes) requireImageStructure(segment.readUIntBE(pos, bytes) > 0);
          quantization.add(selector & 15);
        } else {
          requireImageStructure(pos + 16 <= segment.length);
          const symbols = segment.subarray(pos, pos + 16).reduce((sum, n) => sum + n, 0);
          requireImageStructure(symbols > 0 && symbols <= 256);
          let slots = 1;
          for (const count of segment.subarray(pos, pos + 16)) {
            slots = 2 * slots - count;
            requireImageStructure(slots >= 0);
          }
          pos += 16 + symbols;
          huffman.add(selector);
        }
        requireImageStructure(pos <= segment.length);
      }
      requireImageStructure(pos > 0);
    } else if (marker === 0xda) {
      requireImageStructure(frame && segment.length >= 6 && segment[0] > 0 &&
        segment[0] <= frame.components.size && segment.length === 4 + 2 * segment[0]);
      const selected = new Set();
      const spectral = segment.subarray(-3);
      requireImageStructure(spectral[0] <= spectral[1] && spectral[1] <= 63 &&
        (spectral[2] >> 4) <= 13 && (spectral[2] & 15) <= 13);
      if (frame.marker !== 0xc2) requireImageStructure(spectral[0] === 0 && spectral[1] === 63 && spectral[2] === 0);
      else requireImageStructure((spectral[0] !== 0 || spectral[1] === 0) &&
        (spectral[0] === 0 || segment[0] === 1) &&
        ((spectral[2] >> 4) === 0 || (spectral[2] >> 4) === (spectral[2] & 15) + 1));
      for (let i = 1; i < segment.length - 3; i += 2) {
        const id = segment[i];
        const tables = segment[i + 1];
        requireImageStructure(frame.components.has(id) && !selected.has(id) &&
          quantization.has(frame.components.get(id)) && (tables >> 4) <= 3 && (tables & 15) <= 3 &&
          (spectral[0] !== 0 || huffman.has(tables >> 4)) &&
          (spectral[1] === 0 || huffman.has(16 + (tables & 15))));
        selected.add(id);
        if (spectral[0] === 0 && (spectral[2] >> 4) === 0) dcComponents.add(id);
      }
      let entropyBytes = 0;
      while (offset < raw.length) {
        if (raw[offset] !== 0xff) { entropyBytes += 1; offset += 1; continue; }
        let next = offset + 1;
        while (raw[next] === 0xff) next += 1;
        if (raw[next] === 0x00 || (raw[next] >= 0xd0 && raw[next] <= 0xd7)) {
          if (raw[next] === 0x00) entropyBytes += 1;
          offset = next + 1;
        } else break;
      }
      requireImageStructure(entropyBytes > 0);
      scans += 1;
    } else if (marker === 0xdd) {
      requireImageStructure(segment.length === 2);
    } else {
      requireImageStructure((marker >= 0xe0 && marker <= 0xef) || marker === 0xfe);
    }
  }
  requireImageStructure(false);
}

function validateWebP(raw) {
  requireImageStructure(raw.length >= 20 && raw.readUInt32LE(4) + 8 === raw.length);
  let offset = 12;
  let canvas;
  let dimensions;
  let alpha = false;
  const seen = new Set();
  while (offset + 8 <= raw.length) {
    const type = raw.toString("latin1", offset, offset + 4);
    const length = raw.readUInt32LE(offset + 4);
    const end = offset + 8 + length;
    requireImageStructure(end + (length & 1) <= raw.length && (!(length & 1) || raw[end] === 0));
    const chunk = raw.subarray(offset + 8, end);
    requireImageStructure(!seen.has(type));
    seen.add(type);
    if (type === "VP8X") {
      requireImageStructure(offset === 12 && length === 10 && (chunk[0] & 0xc3) === 0 && chunk.readUIntLE(1, 3) === 0);
      canvas = [1 + chunk.readUIntLE(4, 3), 1 + chunk.readUIntLE(7, 3), chunk[0]];
    } else if (type === "VP8 " || type === "VP8L") {
      requireImageStructure(!dimensions);
      if (type === "VP8 ") {
        requireImageStructure(length > 10 && (chunk[0] & 1) === 0 && ((chunk[0] >> 1) & 7) <= 3 &&
          (chunk[0] & 16) !== 0 && chunk.subarray(3, 6).equals(Buffer.from([0x9d, 0x01, 0x2a])) &&
          (chunk.readUIntLE(0, 3) >> 5) > 0 && (chunk.readUIntLE(0, 3) >> 5) <= length - 10);
        dimensions = [chunk.readUInt16LE(6) & 0x3fff, chunk.readUInt16LE(8) & 0x3fff];
      } else {
        requireImageStructure(length > 5 && chunk[0] === 0x2f && (chunk[4] >> 5) === 0 && !alpha);
        const bits = chunk.readUInt32LE(1);
        dimensions = [1 + (bits & 0x3fff), 1 + ((bits >>> 14) & 0x3fff)];
      }
      requireImageStructure(dimensions.every((n) => n > 0) &&
        (!canvas || (canvas[0] === dimensions[0] && canvas[1] === dimensions[1])));
    } else if (type === "ALPH") {
      requireImageStructure(canvas && (canvas[2] & 16) !== 0 && !dimensions && length > 1 &&
        (chunk[0] & 0xc0) === 0 && (chunk[0] & 3) <= 1 && ((chunk[0] >> 4) & 3) <= 1 &&
        ((chunk[0] & 3) !== 0 || length === 1 + canvas[0] * canvas[1]));
      alpha = true;
    } else if (["ICCP", "EXIF", "XMP "].includes(type)) {
      const flag = { ICCP: 32, EXIF: 8, "XMP ": 4 }[type];
      requireImageStructure(canvas && (canvas[2] & flag) !== 0 && length > 0 &&
        (type === "ICCP" ? !dimensions && !alpha : dimensions));
    } else {
      requireImageStructure(type !== "ANIM" && type !== "ANMF");
    }
    offset = end + (length & 1);
  }
  requireImageStructure(offset === raw.length && dimensions && (!alpha || seen.has("VP8 ")));
  if (canvas) {
    for (const [type, flag] of [["ICCP", 32], ["EXIF", 8], ["XMP ", 4]]) {
      requireImageStructure(Boolean(canvas[2] & flag) === seen.has(type));
    }
    requireImageStructure(!(canvas[2] & 16) || alpha || seen.has("VP8L"));
  }
}

function validateGeneratedImage({ raw, mimeType }) {
  // Output validation is deliberately limited to static PNG, Huffman DCT JPEG,
  // and static WebP. Reference MIME detection remains independent. These checks
  // validate structure, not JPEG/WebP entropy decoding or pixel rendering.
  const validate = { "image/png": validatePNG, "image/jpeg": validateJPEG, "image/webp": validateWebP }[mimeType];
  requireImageStructure(validate && raw.length > 0 && raw.length <= MAX_REFERENCE_IMAGE_BYTES);
  try {
    validate(raw);
  } catch {
    requireImageStructure(false);
  }
}

export async function loadReferenceImages(imagePaths) {
  if (imagePaths.length > MAX_REFERENCE_IMAGES) {
    throw new Error(`参考图最多支持 ${MAX_REFERENCE_IMAGES} 张`);
  }

  const images = [];
  for (const imagePath of imagePaths) {
    let handle;
    try {
      handle = await fs.open(
        imagePath,
        fsSync.constants.O_RDONLY | (fsSync.constants.O_NOFOLLOW || 0),
      );
    } catch (error) {
      throw new Error(`参考图不存在或无法读取: ${imagePath} (${error.message})`);
    }

    try {
      const before = await handle.stat({ bigint: true });
      if (!before.isFile()) {
        throw new Error(`参考图不是文件: ${imagePath}`);
      }
      if (before.size <= 0n) {
        throw new Error(`参考图为空文件: ${imagePath}`);
      }
      if (before.size > BigInt(MAX_REFERENCE_IMAGE_BYTES)) {
        throw new Error(`参考图超过 10MB 限制: ${imagePath}`);
      }

      const raw = await handle.readFile();
      const after = await handle.stat({ bigint: true });
      if (
        raw.length !== Number(before.size) ||
        before.dev !== after.dev ||
        before.ino !== after.ino ||
        before.size !== after.size ||
        before.mtimeNs !== after.mtimeNs ||
        before.ctimeNs !== after.ctimeNs
      ) {
        throw new Error(`参考图在读取期间发生变化: ${imagePath}`);
      }

      const mimeType = inferReferenceImageMimeType(raw);
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
    } finally {
      await handle.close();
    }
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
    if (!header.toLowerCase().endsWith(";base64")) {
      throw new Error("图片 data URL 需要 Base64 载荷");
    }
    mimeType = normalizeImageMimeType(header.split(";", 1)[0]);
  }

  payload = payload.replace(/\s+/g, "").replace(/-/g, "+").replace(/_/g, "/");
  const raw = Buffer.from(payload, "base64");
  const encoded = raw.toString("base64");
  if (!raw.length || (payload !== encoded && payload !== encoded.replace(/=+$/, ""))) {
    throw new Error("无效的 Base64 图片载荷");
  }
  const detected = normalizeImageMimeType(inferMimeTypeFromMagic(raw));
  if (!detected || (mimeType && detected !== mimeType)) {
    throw new Error("图片内容与支持的格式不符");
  }
  return { raw, mimeType: detected };
}

function suffixFromMime(mimeType) {
  for (const [suffix, mime] of IMAGE_MIME_BY_EXT) {
    if (mime === mimeType) return suffix;
  }
  throw new Error("不支持的图片格式");
}

function serviceRoot(baseUrl) {
  let base;
  try {
    base = new URL(baseUrl);
  } catch {
    throw new Error("无效的接口地址，请提供 HTTP(S) 服务根地址");
  }
  if (!/^https?:\/\/[^/]/i.test(baseUrl) || /[\s\x00-\x1f\x7f\\?#]/.test(baseUrl) ||
      base.username || base.password || !base.hostname) {
    throw new Error("无效的接口地址，请提供 HTTP(S) 服务根地址");
  }
  return base.href.replace(/\/+$/, "");
}

async function fetchImageService(url, options) {
  try {
    return await fetch(url, options);
  } catch {
    throw new Error("图片请求未完成");
  }
}

async function parseJsonResponse(response) {
  if (!response.ok) {
    await response.body?.cancel().catch(() => {});
    throw new Error(`HTTP ${response.status}`);
  }
  try {
    return await response.json();
  } catch {
    throw new Error("接口返回了空响应或非 JSON 内容");
  }
}

async function requestJson(url, body, apiKey, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetchImageService(url, {
      method: "POST",
      redirect: "error",
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
    const response = await fetchImageService(url, {
      method: "POST",
      redirect: "error",
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

function normalizeImageMimeType(value) {
  const normalized = String(value || "").split(";", 1)[0].trim().toLowerCase();
  if (normalized === "image/jpg") {
    return "image/jpeg";
  }
  if (normalized === "image/heif") {
    return "image/heic";
  }
  return normalized;
}

async function readResponseBytesLimited(response, maxBytes, label) {
  if (!response.body || typeof response.body.getReader !== "function") {
    throw new Error(`${label} returned an unreadable body`);
  }

  const chunks = [];
  let total = 0;
  const reader = response.body.getReader();
  try {
    while (true) {
      const { done, value } = await reader.read().catch(() => {
        throw new Error("download interrupted");
      });
      if (done) break;
      const chunk = Buffer.from(value);
      total += chunk.length;
      if (total > maxBytes) {
        await reader.cancel().catch(() => {});
        throw new Error(`${label} exceeds the ${Math.floor(maxBytes / 1024 / 1024)}MB limit`);
      }
      chunks.push(chunk);
    }
  } finally {
    reader.releaseLock();
  }
  return Buffer.concat(chunks, total);
}

export async function downloadImageURL(url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetchImageService(url, {
      method: "GET",
      redirect: "error",
      signal: controller.signal,
    });
    if (!response.ok) {
      await response.body?.cancel().catch(() => {});
      throw new Error(`download HTTP ${response.status}`);
    }

    const contentType = normalizeImageMimeType(response.headers.get("content-type"));
    if (contentType && !SUPPORTED_REFERENCE_IMAGE_MIME_TYPES.has(contentType)) {
      throw new Error("download returned non-image content-type");
    }

    const contentLengthHeader = response.headers.get("content-length");
    if (contentLengthHeader) {
      if (!/^\d+$/.test(contentLengthHeader.trim())) {
        throw new Error("download returned invalid content-length");
      }
      const contentLength = Number(contentLengthHeader);
      if (!Number.isSafeInteger(contentLength) || contentLength <= 0) {
        throw new Error("download returned invalid content-length");
      }
      if (contentLength > MAX_REFERENCE_IMAGE_BYTES) {
        throw new Error("download exceeds the 10MB limit");
      }
    }

    const raw = await readResponseBytesLimited(
      response,
      MAX_REFERENCE_IMAGE_BYTES,
      "download",
    );
    if (raw.length === 0) {
      throw new Error("download returned an empty image");
    }
    if (contentLengthHeader && raw.length !== Number(contentLengthHeader)) {
      throw new Error("download content-length does not match received bytes");
    }
    const detectedMimeType = normalizeImageMimeType(inferMimeTypeFromMagic(raw));
    if (!SUPPORTED_REFERENCE_IMAGE_MIME_TYPES.has(detectedMimeType)) {
      throw new Error("downloaded image format is not supported or cannot be identified");
    }
    if (contentType && contentType !== detectedMimeType) {
      throw new Error(
        `download content-type ${contentType} does not match detected ${detectedMimeType}`,
      );
    }

    return {
      raw,
      mimeType: detectedMimeType,
    };
  } finally {
    clearTimeout(timer);
  }
}

async function publishGeneratedImage(filename, raw) {
  // mkdtemp creates a private (0700) directory on the destination filesystem.
  // Only our stage is writable: link publishes a complete inode and fails if
  // any object already occupies the final name, without following symlinks.
  let stageDir;
  let handle;
  try {
    stageDir = await fs.mkdtemp(path.join(path.dirname(filename), ".gpt-image2-"));
    const stagedFile = path.join(stageDir, "image");
    handle = await fs.open(stagedFile, "wx", 0o600);
    await fs.writeFile(handle, raw);
    if ((await handle.stat()).size !== raw.length) {
      throw new Error("图片暂存写入不完整");
    }
    await handle.sync();
    await handle.close();
    handle = undefined;
    await fs.link(stagedFile, filename);
  } finally {
    if (handle) {
      await handle.close().catch(() => {
        console.error("  无法关闭图片暂存文件");
      });
    }
    if (stageDir) {
      // Cleanup cannot turn an already published image into a failed receipt.
      // Never unlink the final name: it might belong to another invocation.
      await fs.rm(stageDir, { recursive: true, force: true }).catch(() => {
        console.error(`  无法清理图片暂存目录: ${stageDir}`);
      });
    }
  }
}

async function main() {
  const dotenvConfig = loadDotEnv(DOTENV_PATH);
  const options = parseArgs(process.argv.slice(2), dotenvConfig);
  if (!options.baseUrl) {
    throw new Error("缺少接口配置，请通过 --base-url、GPT_IMAGE2_BASE_URL、OPENAI_BASE_URL 或 CODEX_OPENAI_BASE_URL 提供地址");
  }
  if (!options.apiKey) {
    throw new Error("缺少接口配置，请通过 --api-key、GPT_IMAGE2_API_KEY、OPENAI_API_KEY 或 CODEX_OPENAI_API_KEY 提供密钥");
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
    requestUrl = `${options.baseUrl}/images/edits`;
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
    requestUrl = `${options.baseUrl}/images/generations`;
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

  const expected = hasReferenceImages ? 1 : options.n;
  const responseData = resp?.data;
  if (!Array.isArray(responseData) || !responseData.length) {
    throw new Error(`接口未返回图片，已保存 0 张，缺少 ${expected} 张`);
  }
  const data = hasReferenceImages ? responseData.slice(0, 1) : responseData;
  const ts = timestampText();
  let saved = 0;
  let failed = 0;
  for (const [index, img] of data.entries()) {
    try {
      let image;
      if (typeof img?.b64_json === "string" && img.b64_json) {
        image = decodeImageField(img.b64_json);
      } else if (typeof img?.url === "string" && img.url) {
        image = await downloadImageURL(img.url, options.timeoutMs);
      } else {
        throw new Error("缺少图片载荷");
      }
      validateGeneratedImage(image);
      await fs.mkdir(options.outDir, { recursive: true });
      const filename = path.join(options.outDir, `gpt-image2_${ts}_${index + 1}${suffixFromMime(image.mimeType)}`);
      await publishGeneratedImage(filename, image.raw);
      saved += 1;
      console.log(`  [${index}] saved ${filename} (${image.raw.length.toLocaleString()} bytes)`);
    } catch (error) {
      failed += 1;
      console.error(`  [${index}] ${error.message}`);
    }
  }
  const missing = Math.max(0, expected - saved);
  const summary = `已保存 ${saved} 张，预期 ${expected} 张，缺少 ${missing} 张`;
  if (saved !== expected || failed) throw new Error(`${summary}，失败条目 ${failed} 个`);
  console.log(summary);
}

const isMain = Boolean(process.argv[1]) &&
  fsSync.realpathSync(path.resolve(process.argv[1])) === fsSync.realpathSync(__filename);
if (isMain) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  });
}
