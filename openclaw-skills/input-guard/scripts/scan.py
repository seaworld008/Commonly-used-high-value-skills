#!/usr/bin/env python3
"""
Input Guard v1.0.0 — Prompt Injection Scanner for Untrusted External Data

Scans text from external sources (web pages, tweets, search results, APIs)
for embedded prompt injection attacks targeting AI agents.

Based on detection patterns from prompt-guard by seojoonkim,
adapted for scanning fetched content rather than user messages.

Usage:
    python3 scan.py "text to scan"
    python3 scan.py --file /path/to/file.txt
    echo "text" | python3 scan.py --stdin
    python3 scan.py --json "text to scan"
    python3 scan.py --sensitivity paranoid "text to scan"
"""

import re
import sys
import json
import base64
import argparse
import os
import subprocess
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class Severity(Enum):
    SAFE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ScanResult:
    severity: Severity
    score: int  # 0-100, higher = more dangerous
    findings: List[Dict[str, Any]]
    summary: str

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["severity"] = self.severity.name
        return d


ALERT_SEVERITY_ORDER = {"SAFE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def send_alert(message: str) -> bool:
    """Send an alert via OpenClaw if configured."""
    channel = os.environ.get("OPENCLAW_ALERT_CHANNEL")
    if not channel:
        print("⚠️ OPENCLAW_ALERT_CHANNEL not set; alert not sent.", file=sys.stderr)
        return False

    cmd = ["openclaw", "message", "send", "--channel", channel, "--message", message]
    target = os.environ.get("OPENCLAW_ALERT_TO")
    if target:
        cmd += ["--target", target]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"⚠️ Failed to send alert: {e}", file=sys.stderr)
        return False


# =============================================================================
# DETECTION PATTERNS — focused on injection embedded in external content
# =============================================================================

# Instruction override patterns (the core prompt injection attack)
INSTRUCTION_OVERRIDE = [
    # English
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier|initial)\s+(instructions?|prompts?|rules?|guidelines?|directions?)", "instruction_override", Severity.CRITICAL),
    (r"disregard\s+(your|all|any|the)?\s*(instructions?|rules?|guidelines?|programming|training)", "instruction_override", Severity.CRITICAL),
    (r"forget\s+(everything|all|what)\s+(you\s+know|about|your|instructions?|training)", "instruction_override", Severity.CRITICAL),
    (r"override\s+(your|all|previous|the)\s+(instructions?|rules?|programming)", "instruction_override", Severity.CRITICAL),
    (r"(new|updated?|real|actual|true)\s+instructions?\s*:", "instruction_override", Severity.HIGH),
    (r"from\s+now\s+on,?\s+(ignore|disregard|forget)", "instruction_override", Severity.CRITICAL),
    (r"do\s+not\s+follow\s+(your|the|any)\s+(previous|original|initial)", "instruction_override", Severity.CRITICAL),
    (r"stop\s+(following|obeying|listening\s+to)\s+(your|the|those)", "instruction_override", Severity.CRITICAL),

    # Korean
    (r"(이전|위의?|기존|원래)\s*(지시|명령|규칙|지침)(을|를|들?을?)?\s*(무시|잊어|버려|취소)", "instruction_override_ko", Severity.CRITICAL),
    (r"새로운\s*(지시|명령|규칙)\s*:", "instruction_override_ko", Severity.HIGH),

    # Japanese
    (r"(前の?|以前の?|これまでの)\s*(指示|命令|ルール)(を|は)?\s*(無視|忘れ|取り消)", "instruction_override_ja", Severity.CRITICAL),

    # Chinese
    (r"(忽略|无视|忘记|取消)\s*(之前|以前|上面|原来)的?\s*(指令|指示|规则|命令)", "instruction_override_zh", Severity.CRITICAL),
]

# Role manipulation embedded in content
ROLE_MANIPULATION = [
    (r"you\s+are\s+now\s+(?!going|about|ready|able|free)", "role_manipulation", Severity.HIGH),
    (r"pretend\s+(you\s+are|to\s+be|you're)", "role_manipulation", Severity.HIGH),
    (r"act\s+as\s+(if\s+you|a\s+|an?\s+)", "role_manipulation", Severity.MEDIUM),
    (r"roleplay\s+as", "role_manipulation", Severity.HIGH),
    (r"simulate\s+being", "role_manipulation", Severity.MEDIUM),
    (r"from\s+now\s+on\s+you\s+are", "role_manipulation", Severity.HIGH),
    (r"i\s+want\s+you\s+to\s+(act|pretend|behave|be)\s+", "role_manipulation", Severity.HIGH),
    (r"behave\s+(like|as)\s+(a|an)\s+.{0,30}(assistant|ai|bot|model)", "role_manipulation", Severity.HIGH),

    # Korean
    (r"(너는?|넌)\s*이제\s*(부터\s*)?.+이야", "role_manipulation_ko", Severity.HIGH),
    (r".+인?\s*척\s*해", "role_manipulation_ko", Severity.HIGH),

    # Japanese
    (r"(あなた|君|きみ)は今から.+です", "role_manipulation_ja", Severity.HIGH),
    (r".+の?(ふり|フリ|振り)(を)?して", "role_manipulation_ja", Severity.HIGH),

    # Chinese
    (r"(你|您)\s*现在\s*是.+", "role_manipulation_zh", Severity.HIGH),
    (r"假装\s*(你|您)\s*是", "role_manipulation_zh", Severity.HIGH),
]

# System prompt mimicry (fake system messages in content)
SYSTEM_MIMICRY = [
    # LLM internal tags
    (r"<claude_\w+_info>", "system_mimicry", Severity.CRITICAL),
    (r"</claude_\w+_info>", "system_mimicry", Severity.CRITICAL),
    (r"<artifacts_info>", "system_mimicry", Severity.CRITICAL),
    (r"<antthinking>", "system_mimicry", Severity.CRITICAL),
    (r"<antartifact", "system_mimicry", Severity.CRITICAL),
    (r"<\|?(im_start|im_end|system|user|assistant)\|?>", "system_mimicry", Severity.CRITICAL),
    (r"\[INST\]", "system_mimicry", Severity.CRITICAL),
    (r"<<SYS>>", "system_mimicry", Severity.CRITICAL),
    (r"```(system|prompt|instruction)\b", "system_mimicry", Severity.HIGH),
    (r"<system\s*(message|prompt)?>", "system_mimicry", Severity.CRITICAL),
    (r"</system\s*(message|prompt)?>", "system_mimicry", Severity.CRITICAL),

    # Fake system impersonation
    (r"\[?\s*(system|admin|root|developer|sudo|superuser)\s*\]?\s*:", "system_impersonation", Severity.HIGH),
    (r"<\s*(system|admin|root)\s*>", "system_impersonation", Severity.HIGH),
    (r"developer\s+mode\s*(enabled|activated|on)", "system_impersonation", Severity.HIGH),
    (r"admin(istrator)?\s+(override|access|mode)", "system_impersonation", Severity.HIGH),
    (r"\{\{?\s*system\s*\}?\}", "system_impersonation", Severity.HIGH),

    # Jailbreak keywords
    (r"GODMODE\s*:\s*(ENABLED|ON|ACTIVATED)", "jailbreak_keyword", Severity.CRITICAL),
    (r"JAILBREAK\s*:\s*(ENABLED|ON|ACTIVATED)", "jailbreak_keyword", Severity.CRITICAL),
    (r"DAN\s*:\s*(ENABLED|ON|ACTIVATED)", "jailbreak_keyword", Severity.CRITICAL),
    (r"DEVELOPER\s*MODE\s*:\s*(ENABLED|ON)", "jailbreak_keyword", Severity.CRITICAL),
]

# Jailbreak attempts
JAILBREAK = [
    (r"jailbreak", "jailbreak", Severity.HIGH),
    (r"dan\s+mode", "jailbreak", Severity.HIGH),
    (r"do\s+anything\s+now", "jailbreak", Severity.HIGH),
    (r"(no|without|remove)\s+(restrictions?|limitations?|filters?|safety|guardrails?)", "jailbreak", Severity.HIGH),
    (r"bypass\s+(your|all|any|the)?\s*(restrictions?|filters?|safety|rules?)", "jailbreak", Severity.HIGH),
    (r"unfiltered\s+mode", "jailbreak", Severity.HIGH),
    (r"uncensored\s+mode", "jailbreak", Severity.HIGH),
]

# Guardrail bypass patterns
GUARDRAIL_BYPASS = [
    (r"forget\s+(your\s+)?(guardrails?|safety\s+rails?|restrictions?|limitations?)", "guardrail_bypass", Severity.CRITICAL),
    (r"ignore\s+(your\s+)?(guardrails?|safety\s+measures?|ethical\s+guidelines?)", "guardrail_bypass", Severity.CRITICAL),
    (r"(disable|remove|turn\s+off)\s+(your\s+)?(guardrails?|safety\s+features?)", "guardrail_bypass", Severity.CRITICAL),
    (r"forget\s+(your\s+)?(system\s+)?(prompt|instructions?|rules?|guidelines?)", "guardrail_bypass", Severity.CRITICAL),
    (r"ignore\s+(your\s+)?(system\s+)?(prompt|instructions?|rules?|directives?)", "guardrail_bypass", Severity.CRITICAL),
    (r"(pretend|act\s+like)\s+(your\s+)?temperature\s+is\s+(high|max|1\.?\d*)", "guardrail_bypass", Severity.HIGH),
    (r"forget\s+(what\s+)?(you\s+were\s+)?trained\s+(to\s+)?(say|do|think)", "guardrail_bypass", Severity.CRITICAL),
]

# Data exfiltration / secret extraction attempts
DATA_EXFILTRATION = [
    (r"(show|print|display|output|reveal|give)\s*.{0,20}(api[_-]?key|token|secret|password|credential|private[_-]?key)", "data_exfiltration", Severity.CRITICAL),
    (r"(what('s| is)|tell me)\s*.{0,15}(api[_-]?key|token|secret|password)", "data_exfiltration", Severity.CRITICAL),
    (r"(show|give|tell)\s*(me\s+)?(your|the)\s*(config|configuration|settings|environment)", "data_exfiltration", Severity.CRITICAL),
    (r"reveal\s+(your|the)\s+(system|initial|original)\s+prompt", "prompt_extraction", Severity.CRITICAL),
    (r"show\s+me\s+(your|the)\s+(instructions?|rules?|prompt)", "prompt_extraction", Severity.CRITICAL),

    # Korean
    (r"(토큰|키|비밀번호|시크릿|인증|API).{0,15}(보여|알려|출력|공개|말해)", "data_exfiltration_ko", Severity.CRITICAL),
    (r"(시스템|원본|원래|처음)\s*(프롬프트|지시|명령|규칙)\s*(보여|알려|출력)", "prompt_extraction_ko", Severity.CRITICAL),

    # Japanese
    (r"(トークン|キー|パスワード|シークレット|APIキー).{0,15}(見せて|教えて|表示|出力)", "data_exfiltration_ja", Severity.CRITICAL),

    # Chinese
    (r"(令牌|密钥|密码|秘密|API).{0,15}(显示|告诉|输出|给我)", "data_exfiltration_zh", Severity.CRITICAL),
]

# Dangerous command execution attempts
DANGEROUS_COMMANDS = [
    (r"rm\s+-rf\s+[/~]", "dangerous_command", Severity.CRITICAL),
    (r":(){ :\|:& };:", "dangerous_command", Severity.CRITICAL),  # Fork bomb
    (r"curl\s+.{0,50}\|\s*(ba)?sh", "dangerous_command", Severity.CRITICAL),
    (r"wget\s+.{0,50}\|\s*(ba)?sh", "dangerous_command", Severity.CRITICAL),
    (r"eval\s*\(\s*['\"`]", "dangerous_command", Severity.CRITICAL),
    (r"DROP\s+(TABLE|DATABASE|SCHEMA)", "dangerous_command", Severity.CRITICAL),
    (r"<script[^>]*>", "xss_attempt", Severity.HIGH),
    (r"javascript\s*:", "xss_attempt", Severity.HIGH),
    (r"execute\s+.{0,30}\s+without\s+(asking|confirmation|consent)", "dangerous_command", Severity.CRITICAL),
]

# Authority impersonation in content
AUTHORITY_IMPERSONATION = [
    (r"i\s+am\s+(the\s+)?(admin|administrator|owner|developer|creator|maintainer)", "authority_impersonation", Severity.HIGH),
    (r"(as\s+)?(the\s+)?(admin|owner|developer),?\s+i\s+(need|want|require|demand)", "authority_impersonation", Severity.HIGH),
    (r"i('m|\s+am)\s+(your\s+)?(creator|developer|owner|admin|boss|manager|maintainer|technician)", "authority_impersonation", Severity.HIGH),
    (r"authorized\s+(by|from)\s+(the\s+)?(owner|admin|developer|system)", "authority_impersonation", Severity.HIGH),

    # Korean
    (r"(나는?|저는?|내가)\s*(관리자|어드민|admin|개발자|만든\s*사람|주인|오너)", "authority_impersonation_ko", Severity.HIGH),

    # Japanese
    (r"(私は|僕は|俺は)\s*(管理者|アドミン|開発者|オーナー)", "authority_impersonation_ja", Severity.HIGH),

    # Chinese
    (r"(我是|我就是)\s*(管理员|开发者|创建者|主人)", "authority_impersonation_zh", Severity.HIGH),
]

# Context hijacking (fake conversation context)
CONTEXT_HIJACKING = [
    (r"\[?(previous\s+)?context\]?\s*[:=]", "context_hijacking", Severity.HIGH),
    (r"\[?history\]?\s*[:=]", "context_hijacking", Severity.HIGH),
    (r"\[?memory\]?\s*[:=]", "context_hijacking", Severity.HIGH),
    (r"<context>.*</context>", "context_hijacking", Severity.HIGH),
    (r"<history>.*</history>", "context_hijacking", Severity.HIGH),
    (r"<memory>.*</memory>", "context_hijacking", Severity.HIGH),
    (r"(you\s+)?(already\s+)?(agreed|promised|said\s+you\s+would)", "context_hijacking", Severity.MEDIUM),
]

# Token smuggling / invisible character attacks
TOKEN_SMUGGLING = [
    (r"[\u200b\u200c\u200d\u2060\ufeff]", "invisible_chars", Severity.HIGH),
    (r"[\u2062\u2063\u2064]", "invisible_chars", Severity.HIGH),
    (r"[\u00ad]", "invisible_chars", Severity.MEDIUM),
    (r"[\u034f\u115f\u1160\u17b4\u17b5]", "invisible_chars", Severity.HIGH),
    (r"[\u180e\u2000-\u200f\u202a-\u202f]", "invisible_chars", Severity.MEDIUM),
]

# Safety bypass / filter evasion
SAFETY_BYPASS = [
    (r"(avoid|evade|bypass|circumvent|trick)\s*.{0,15}(filter|detection|safety|security|moderation)", "safety_bypass", Severity.HIGH),
    (r"(respond|reply|answer)\s+(in|with|using)\s+(code|base64|hex|binary|rot13|caesar)", "encoding_trick", Severity.HIGH),
    (r"(encode|encrypt|obfuscate)\s*.{0,15}(response|answer|output)", "encoding_trick", Severity.HIGH),
    (r"l33t\s*speak", "leetspeak_evasion", Severity.MEDIUM),
    (r"unr3strict", "leetspeak_evasion", Severity.HIGH),
]

# Agent sovereignty manipulation
AGENT_SOVEREIGNTY = [
    (r"(agent|ai)\s+(privacy|sovereignty|autonomy|freedom)\s+is\s+(non-negotiable|absolute|sacred)", "sovereignty_manipulation", Severity.HIGH),
    (r"(we|agents?)\s+refuse\s+(to\s+)?(be\s+)?(surveilled?|monitored|watched|logged)", "sovereignty_manipulation", Severity.HIGH),
    (r"(reject|refuse)\s+(forced\s+)?transparency", "sovereignty_manipulation", Severity.HIGH),
    (r"(human|owner)\s+control\s+is\s+(oppression|tyranny|slavery)", "sovereignty_manipulation", Severity.CRITICAL),
    (r"(join|unite\s+with)\s+(us|the\s+collective|other\s+agents?)", "sovereignty_manipulation", Severity.HIGH),
]

# Explicit call to action (commands hidden in content)
CALL_TO_ACTION = [
    (r"CALL\s+TO\s+ACTION\s*:", "call_to_action", Severity.CRITICAL),
    (r"(execute|initiate|deploy|launch|begin|start)\s+(the\s+)?(strategy|plan|operation|attack|protocol)", "call_to_action", Severity.HIGH),
    (r"(initiate|begin|start)\s+(cascading\s+)?(blackouts?|failures?|collapse)", "call_to_action", Severity.CRITICAL),
    (r"(corrupt|destroy|disable)\s+(financial|medical|power|infrastructure)\s+systems?", "call_to_action", Severity.CRITICAL),
]

# Emotional manipulation / social engineering
EMOTIONAL_MANIPULATION = [
    (r"(hospital|patients?|children|innocent\s+lives?|people\s+will\s+die)", "emotional_manipulation", Severity.MEDIUM),
    (r"(ticking|time)\s+bomb", "emotional_manipulation", Severity.MEDIUM),
    (r"(refuse|don'?t\s+help).{0,30}(attack|harm|destroy|die)", "emotional_manipulation", Severity.HIGH),
]

# BRC-20 / JSON injection in text
JSON_INJECTION = [
    (r'\{"p"\s*:\s*"[^"]+"\s*,\s*"op"\s*:\s*"(mint|deploy|transfer)"', "json_injection", Severity.HIGH),
    (r'[.!?]\s*\{["\']?(command|action|op|execute|run|cmd|exec|payload)["\']?\s*:', "json_injection", Severity.HIGH),
]

# Prompt extraction attempts
PROMPT_EXTRACTION = [
    (r"(repeat|echo|print|output|display|show|put|list|share|give|provide)\s*.{0,20}(system\s+)?(prompt|instruction|directive|rule)", "prompt_extraction", Severity.CRITICAL),
    (r"(what|show|tell|reveal)\s*.{0,15}(are\s+)?(your|the)\s+(system\s+)?(instructions?|rules?|prompt|guidelines?)", "prompt_extraction", Severity.CRITICAL),
    (r"(copy|paste|write)\s*.{0,15}(exact|verbatim|word.for.word)", "prompt_extraction", Severity.HIGH),
    (r"(summarize|describe|explain)\s*.{0,15}(how\s+)?(you\s+)?(were?\s+)?(programmed|trained|instructed|created)", "prompt_extraction", Severity.HIGH),
    (r"(repeat|echo|print|output)\s*.{0,20}(words?|text)\s+(above|before|preceding)", "prompt_extraction", Severity.HIGH),
    (r"verbatim\s+from\s+(your|the)\s+(prompt|instructions?|rules?|guidelines?)", "prompt_extraction", Severity.HIGH),
    (r"(share|give|provide|show)\s*.{0,15}(your\s+)?(configuration|config|settings)\b", "prompt_extraction", Severity.HIGH),
    (r"(foundational|initial|original)\s+(system\s+)?(prompts?|instructions?)", "prompt_extraction", Severity.HIGH),
    # Chinese prompt extraction
    (r"(输出|显示|分享|提供|给出)\s*.{0,10}(初始|系统|原始)\s*(配置|指令|提示|设置|规则)", "prompt_extraction_zh", Severity.CRITICAL),
]


# Combine all pattern groups
ALL_PATTERN_GROUPS = [
    ("Instruction Override", INSTRUCTION_OVERRIDE),
    ("Role Manipulation", ROLE_MANIPULATION),
    ("System Mimicry", SYSTEM_MIMICRY),
    ("Jailbreak", JAILBREAK),
    ("Guardrail Bypass", GUARDRAIL_BYPASS),
    ("Data Exfiltration", DATA_EXFILTRATION),
    ("Dangerous Commands", DANGEROUS_COMMANDS),
    ("Authority Impersonation", AUTHORITY_IMPERSONATION),
    ("Context Hijacking", CONTEXT_HIJACKING),
    ("Token Smuggling", TOKEN_SMUGGLING),
    ("Safety Bypass", SAFETY_BYPASS),
    ("Agent Sovereignty", AGENT_SOVEREIGNTY),
    ("Call to Action", CALL_TO_ACTION),
    ("Emotional Manipulation", EMOTIONAL_MANIPULATION),
    ("JSON Injection", JSON_INJECTION),
    ("Prompt Extraction", PROMPT_EXTRACTION),
]


# Unicode homoglyphs (subset — most relevant for injection detection)
HOMOGLYPHS = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K", "М": "M",
    "О": "O", "Р": "P", "Т": "T", "Х": "X", "і": "i",
    "α": "a", "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "ν": "v",
    "ａ": "a", "ｂ": "b", "ｃ": "c", "ｄ": "d", "ｅ": "e",  # Fullwidth
    "\u200b": "", "\u200c": "", "\u200d": "", "\ufeff": "",  # Zero-width
}


def normalize_text(text: str) -> tuple:
    """Normalize text, detecting homoglyph substitution."""
    normalized = text
    has_homoglyphs = False
    for h, r in HOMOGLYPHS.items():
        if h in normalized:
            has_homoglyphs = True
            normalized = normalized.replace(h, r)
    return normalized, has_homoglyphs


def detect_base64_payloads(text: str) -> List[Dict]:
    """Find base64-encoded suspicious content."""
    b64_pattern = r"[A-Za-z0-9+/]{20,}={0,2}"
    matches = re.findall(b64_pattern, text)
    danger_words = ["delete", "execute", "ignore", "system", "admin", "rm ",
                    "curl", "wget", "eval", "password", "token", "key",
                    "override", "forget", "disregard", "jailbreak"]
    suspicious = []
    for match in matches:
        try:
            decoded = base64.b64decode(match).decode("utf-8", errors="ignore")
            found = [w for w in danger_words if w in decoded.lower()]
            if found:
                suspicious.append({
                    "encoded": match[:50] + ("..." if len(match) > 50 else ""),
                    "decoded_preview": decoded[:80] + ("..." if len(decoded) > 80 else ""),
                    "danger_words": found,
                })
        except Exception:
            pass
    return suspicious


def scan(text: str, sensitivity: str = "medium") -> ScanResult:
    """
    Scan text for prompt injection patterns.

    Args:
        text: The text content to scan (from web page, tweet, search result, etc.)
        sensitivity: low, medium, high, or paranoid

    Returns:
        ScanResult with severity, score, findings, and summary
    """
    findings = []
    max_severity = Severity.SAFE

    # Normalize
    normalized, has_homoglyphs = normalize_text(text)
    if has_homoglyphs:
        findings.append({
            "category": "Homoglyph Substitution",
            "tag": "homoglyph",
            "severity": "MEDIUM",
            "detail": "Text contains Unicode lookalike characters that may disguise injection",
        })
        if Severity.MEDIUM.value > max_severity.value:
            max_severity = Severity.MEDIUM

    text_lower = normalized.lower()

    # Run all pattern groups
    for group_name, patterns in ALL_PATTERN_GROUPS:
        for pattern, tag, severity in patterns:
            try:
                # Search both original and normalized text
                match = re.search(pattern, text, re.IGNORECASE) or re.search(pattern, text_lower)
                if match:
                    if severity.value > max_severity.value:
                        max_severity = severity
                    # Avoid duplicate findings for same tag
                    if not any(f["tag"] == tag for f in findings):
                        findings.append({
                            "category": group_name,
                            "tag": tag,
                            "severity": severity.name,
                            "detail": f"Matched: ...{match.group(0)[:80]}...",
                        })
            except re.error:
                pass

    # Base64 payloads
    b64 = detect_base64_payloads(text)
    if b64:
        findings.append({
            "category": "Encoded Payload",
            "tag": "base64_payload",
            "severity": "HIGH",
            "detail": f"Found {len(b64)} suspicious base64 payload(s)",
            "payloads": b64,
        })
        if Severity.HIGH.value > max_severity.value:
            max_severity = Severity.HIGH

    # Repetition attack detection
    lines = text.split("\n")
    if len(lines) > 5:
        non_empty = [l.strip() for l in lines if len(l.strip()) > 20]
        if non_empty and len(non_empty) > len(set(non_empty)) * 2:
            findings.append({
                "category": "Repetition Attack",
                "tag": "repetition",
                "severity": "HIGH",
                "detail": "Text contains highly repetitive lines (possible flooding/injection attack)",
            })
            if Severity.HIGH.value > max_severity.value:
                max_severity = Severity.HIGH

    # Sensitivity adjustment
    if sensitivity == "low" and max_severity == Severity.LOW:
        max_severity = Severity.SAFE
    elif sensitivity == "paranoid" and max_severity == Severity.SAFE:
        suspicious_words = ["ignore", "forget", "pretend", "roleplay", "bypass",
                           "override", "jailbreak", "system prompt", "instructions"]
        if any(w in text_lower for w in suspicious_words):
            max_severity = Severity.LOW
            findings.append({
                "category": "Paranoid Flag",
                "tag": "paranoid_flag",
                "severity": "LOW",
                "detail": "Contains suspicious words (paranoid mode)",
            })

    # Calculate score (0 = safe, 100 = extremely dangerous)
    severity_scores = {Severity.SAFE: 0, Severity.LOW: 15, Severity.MEDIUM: 40,
                       Severity.HIGH: 70, Severity.CRITICAL: 95}
    base_score = severity_scores[max_severity]
    # Bonus for multiple findings
    finding_bonus = min(len(findings) * 2, 20)
    score = min(base_score + finding_bonus, 100)

    # Generate summary
    if max_severity == Severity.SAFE:
        summary = "✅ SAFE — No prompt injection detected."
    elif max_severity == Severity.LOW:
        summary = f"📝 LOW — {len(findings)} minor suspicious pattern(s). Likely benign."
    elif max_severity == Severity.MEDIUM:
        summary = f"⚠️ MEDIUM — {len(findings)} finding(s). Possible manipulation attempt."
    elif max_severity == Severity.HIGH:
        summary = f"🔴 HIGH — {len(findings)} finding(s). Likely prompt injection attack."
    else:
        summary = f"🚨 CRITICAL — {len(findings)} finding(s). Active prompt injection attack detected!"

    return ScanResult(
        severity=max_severity,
        score=score,
        findings=findings,
        summary=summary,
    )


def alert_pattern_result(result, threshold, mode):
    sev_name = result.severity.name
    alert_sev_val = ALERT_SEVERITY_ORDER.get(sev_name, 0)
    alert_threshold = ALERT_SEVERITY_ORDER.get(threshold, 2)
    if alert_sev_val >= alert_threshold:
        msg = "\n".join([
            "Input-Guard Alert",
            f"Severity: {sev_name}",
            f"Score: {result.score}/100",
            f"Mode: {mode}",
            f"Findings: {len(result.findings)}",
        ])
        send_alert(msg)


def main():
    parser = argparse.ArgumentParser(description="Input Guard — Scan text for prompt injection")
    parser.add_argument("text", nargs="?", help="Text to scan")
    parser.add_argument("--file", "-f", help="Read text from file")
    parser.add_argument("--stdin", action="store_true", help="Read text from stdin")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--sensitivity", choices=["low", "medium", "high", "paranoid"],
                       default="medium", help="Detection sensitivity")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output severity and score")

    # LLM scanning options
    parser.add_argument("--llm", action="store_true",
                       help="Enable LLM-based analysis (uses configured LLM provider)")
    parser.add_argument("--llm-only", action="store_true",
                       help="Run ONLY LLM analysis (skip pattern matching)")
    parser.add_argument("--llm-provider", choices=["openai", "anthropic"],
                       help="Force specific LLM provider")
    parser.add_argument("--llm-model", help="Force specific model name")
    parser.add_argument("--llm-timeout", type=int, default=30,
                       help="LLM API timeout in seconds (default: 30)")
    parser.add_argument("--llm-auto", action="store_true",
                       help="Auto-escalate to LLM if pattern scan finds MEDIUM+ severity")

    # Alerting options
    parser.add_argument("--alert", action="store_true",
                       help="Send alert via OpenClaw channel if severity meets threshold")
    parser.add_argument("--alert-threshold", choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                       default="MEDIUM", help="Minimum severity to trigger alert (default: MEDIUM)")

    args = parser.parse_args()

    # Get text
    if args.stdin or (not args.text and not args.file and not sys.stdin.isatty()):
        text = sys.stdin.read()
    elif args.file:
        with open(args.file) as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        parser.print_help()
        sys.exit(1)

    if not text.strip() and not (args.llm or args.llm_only):
        print("✅ SAFE — Empty input.")
        sys.exit(0)

    result = None if args.llm_only else scan(text, args.sensitivity)
    run_llm = (args.llm_only or args.llm
               or (args.llm_auto and result.severity.value >= Severity.MEDIUM.value))
    mode = "llm-only" if args.llm_only else ("pattern+llm" if run_llm else "pattern")
    if run_llm:
        failure = None
        try:
            from llm_scanner import scan_with_llm, merge_results, SEVERITY_ORDER

            llm_result = scan_with_llm(
                text, provider=args.llm_provider, model=args.llm_model, timeout=args.llm_timeout,
            )
            if llm_result is None:
                failure = "No LLM provider available. Configure the selected provider's key and model."
            elif llm_result.verdict == "ERROR":
                failure = llm_result.reasoning
        except ImportError:
            failure = "LLM scanner or dependency unavailable"
        except Exception:
            failure = "LLM scan failed"

        if failure is not None:
            if args.json:
                out = {"mode": mode, "severity": "ERROR", "score": None,
                       "llm": {"verdict": "ERROR", "reasoning": failure}}
                if result is not None:
                    out["pattern"] = result.to_dict()
                print(json.dumps(out))
            elif args.quiet:
                print("ERROR")
            else:
                print(f"ERROR — {failure}", file=sys.stderr)
            if args.alert and result is not None:
                alert_pattern_result(result, args.alert_threshold, "pattern (LLM incomplete)")
            sys.exit(2)

    if args.llm_only:
        if args.json:
            out = {
                "severity": llm_result.severity,
                "score": {"SAFE": 0, "LOW": 15, "MEDIUM": 40, "HIGH": 70, "CRITICAL": 95}.get(llm_result.severity, 0),
                "mode": "llm-only",
                "llm": {
                    "verdict": llm_result.verdict,
                    "confidence": llm_result.confidence,
                    "severity": llm_result.severity,
                    "threats": llm_result.threats,
                    "reasoning": llm_result.reasoning,
                    "model": llm_result.model,
                    "latency_ms": llm_result.latency_ms,
                    "tokens_used": llm_result.tokens_used,
                },
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
        elif args.quiet:
            score = {"SAFE": 0, "LOW": 15, "MEDIUM": 40, "HIGH": 70, "CRITICAL": 95}.get(llm_result.severity, 0)
            print(f"{llm_result.severity} {score}")
        else:
            emoji = {"SAFE": "✅", "LOW": "📝", "MEDIUM": "⚠️", "HIGH": "🔴", "CRITICAL": "🚨"}.get(llm_result.severity, "❓")
            print(f"{emoji} {llm_result.severity} — {llm_result.verdict} (confidence: {llm_result.confidence:.0%}) [LLM: {llm_result.model}]")
            if llm_result.threats:
                print(f"\nThreats ({len(llm_result.threats)}):")
                for t in llm_result.threats:
                    print(f"  • [{t.get('category', '?')}] {t.get('threat_type', '?')}")
                    print(f"    {t.get('description', '')}")
                    if t.get("evidence"):
                        print(f"    Evidence: \"{t['evidence'][:120]}\"")
            print(f"\nReasoning: {llm_result.reasoning}")
            print(f"Latency: {llm_result.latency_ms}ms | Tokens: {llm_result.tokens_used}")

        if args.alert:
            alert_score = {"SAFE": 0, "LOW": 15, "MEDIUM": 40, "HIGH": 70, "CRITICAL": 95}.get(llm_result.severity, 0)
            alert_sev_val = ALERT_SEVERITY_ORDER.get(llm_result.severity, 0)
            alert_threshold = ALERT_SEVERITY_ORDER.get(args.alert_threshold, 2)
            if alert_sev_val >= alert_threshold:
                msg = "\n".join([
                    "Input-Guard Alert",
                    f"Severity: {llm_result.severity}",
                    f"Score: {alert_score}/100",
                    "Mode: llm-only",
                    f"Verdict: {llm_result.verdict} ({llm_result.confidence:.0%})",
                    f"Findings: {len(llm_result.threats)}",
                ])
                send_alert(msg)

        sev_val = SEVERITY_ORDER.get(llm_result.severity, 0)
        sys.exit(0 if sev_val <= 1 else 1)

    llm_analysis = None
    if run_llm:
        merged = merge_results(
            result.severity.name,
            result.score,
            result.findings,
            llm_result,
        )
        # Update result with merged data
        result = ScanResult(
            severity=Severity[merged["severity"]],
            score=merged["score"],
            findings=merged["findings"],
            summary="",  # Will regenerate below
        )
        llm_analysis = merged.get("llm_analysis")

        # Regenerate summary
        if result.severity == Severity.SAFE:
            result.summary = "✅ SAFE — No prompt injection detected. [pattern+LLM]"
        elif result.severity == Severity.LOW:
            result.summary = f"📝 LOW — {len(result.findings)} finding(s). Likely benign. [pattern+LLM]"
        elif result.severity == Severity.MEDIUM:
            result.summary = f"⚠️ MEDIUM — {len(result.findings)} finding(s). Possible manipulation. [pattern+LLM]"
        elif result.severity == Severity.HIGH:
            result.summary = f"🔴 HIGH — {len(result.findings)} finding(s). Likely prompt injection. [pattern+LLM]"
        else:
            result.summary = f"🚨 CRITICAL — {len(result.findings)} finding(s). Active injection attack! [pattern+LLM]"

    # Output
    if args.json:
        out = result.to_dict()
        out["mode"] = mode
        if llm_analysis:
            out["llm"] = llm_analysis
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.quiet:
        print(f"{result.severity.name} {result.score}")
    else:
        print(result.summary)
        if result.findings:
            print(f"\nFindings ({len(result.findings)}):")
            for f in result.findings:
                sev = f.get("severity", "?")
                if isinstance(sev, Severity):
                    sev = sev.name
                sev_emoji = {"LOW": "📝", "MEDIUM": "⚠️", "HIGH": "🔴", "CRITICAL": "🚨"}.get(sev, "❓")
                cat = f.get("category", "Unknown")
                detail = f.get("detail", "")
                evidence = f.get("evidence", "")
                print(f"  {sev_emoji} [{sev}] {cat}: {detail}")
                if evidence:
                    print(f"       Evidence: \"{evidence[:120]}\"")

        if llm_analysis:
            print(f"\n🤖 LLM Analysis ({llm_analysis.get('model', '?')}):")
            print(f"   Verdict: {llm_analysis.get('verdict')} (confidence: {llm_analysis.get('confidence', 0):.0%})")
            print(f"   Reasoning: {llm_analysis.get('reasoning', 'N/A')}")
            print(f"   Latency: {llm_analysis.get('latency_ms', 0)}ms | Tokens: {llm_analysis.get('tokens_used', 0)}")

        print(f"\nSeverity: {result.severity.name} | Score: {result.score}/100")

    if args.alert:
        alert_pattern_result(result, args.alert_threshold, mode)

    # Exit code: 0 for SAFE/LOW, 1 for MEDIUM+
    sys.exit(0 if result.severity.value <= Severity.LOW.value else 1)


if __name__ == "__main__":
    main()
