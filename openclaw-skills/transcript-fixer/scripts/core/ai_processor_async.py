#!/usr/bin/env python3
"""
AI Processor with Async/Parallel Support - Stage 2: AI-powered Text Corrections

ENHANCEMENT: Process chunks in parallel for 5-10x speed improvement on large files

Key improvements over ai_processor.py:
- Asyncio-based parallel chunk processing
- Configurable concurrency limit (default: 5 concurrent requests)
- Progress bar with real-time updates
- Graceful error handling with fallback model
- Maintains compatibility with existing API

CRITICAL FIX (P1-3): Memory leak prevention
- Limits all_changes growth with sampling
- Releases intermediate results promptly
- Reuses httpx client (connection pooling)
- Monitors memory usage with warnings
"""

from __future__ import annotations

import asyncio
import gc
import os
import re
import logging
from typing import List, Tuple, Optional, Final
from dataclasses import dataclass
import httpx

from .change_extractor import ChangeExtractor, ExtractedChange

# CRITICAL FIX: Import structured logging and retry logic
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logging_config import TimedLogger, ErrorCounter
from utils.retry_logic import RetryConfig, calculate_delay, is_transient_error

# Setup logger
logger = logging.getLogger(__name__)
timed_logger = TimedLogger(logger)

# CRITICAL FIX: Memory management constants
MAX_CHANGES_TO_TRACK: Final[int] = 1000  # Limit changes tracking to prevent memory bloat
MEMORY_WARNING_THRESHOLD: Final[int] = 100  # Warn if >100 chunks


@dataclass
class AIChange:
    """Represents an AI-suggested change"""
    chunk_index: int
    from_text: str
    to_text: str
    confidence: float  # 0.0 to 1.0
    context_before: str = ""
    context_after: str = ""
    change_type: str = "unknown"


class AIProcessorAsync:
    """
    Stage 2 Processor: AI-powered corrections using GLM-4.6 with parallel processing

    Process:
    1. Split text into chunks (respecting API limits)
    2. Send chunks to GLM API in parallel (default: 5 concurrent)
    3. Track changes for learning engine
    4. Preserve formatting and structure

    Performance: ~5-10x faster than sequential processing on large files
    """

    def __init__(self, api_key: str, model: str = "GLM-4.6",
                 base_url: str = "https://open.bigmodel.cn/api/anthropic",
                 fallback_model: str = "GLM-4.5-Air",
                 max_concurrent: int = 5):
        """
        Initialize AI processor with async support

        Args:
            api_key: GLM API key
            model: Model name (default: GLM-4.6)
            base_url: API base URL
            fallback_model: Fallback model on primary failure
            max_concurrent: Maximum concurrent API requests (default: 5)
                          - Higher = faster but more API load
                          - Lower = slower but more conservative
                          - Recommended: 3-7 for GLM API

        CRITICAL FIX (P1-3): Added shared httpx client for connection pooling
        """
        self.api_key = api_key
        self.model = model
        self.fallback_model = fallback_model
        self.base_url = base_url
        self.max_chunk_size = 6000  # Characters per chunk
        self.max_concurrent = max_concurrent  # Concurrency limit
        self.change_extractor = ChangeExtractor()  # For learning from AI results

        # CRITICAL FIX: Shared client for connection pooling (prevents connection leaks)
        self._http_client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create shared HTTP client for connection pooling.

        CRITICAL FIX (P1-3): Prevents connection descriptor leaks
        """
        async with self._client_lock:
            if self._http_client is None or self._http_client.is_closed:
                # Create client with connection pooling limits
                limits = httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100,
                    keepalive_expiry=30.0
                )
                self._http_client = httpx.AsyncClient(
                    timeout=60.0,
                    limits=limits,
                    http2=True  # Enable HTTP/2 for better performance
                )
                logger.debug("Created new HTTP client with connection pooling")

            return self._http_client

    async def _close_http_client(self) -> None:
        """Close shared HTTP client to release resources"""
        async with self._client_lock:
            if self._http_client is not None and not self._http_client.is_closed:
                await self._http_client.aclose()
                self._http_client = None
                logger.debug("Closed HTTP client")

    def process(self, text: str, context: str = "") -> Tuple[str, List[AIChange]]:
        """
        Process text with AI corrections (parallel)

        Args:
            text: Text to correct
            context: Optional domain/meeting context

        Returns:
            (corrected_text, list_of_changes)

        CRITICAL FIX (P1-3): Ensures HTTP client cleanup
        """
        # Run async processing in sync context
        async def _run_with_cleanup():
            try:
                return await self._process_async(text, context)
            finally:
                # Ensure HTTP client is closed in the same event loop
                await self._close_http_client()

        return asyncio.run(_run_with_cleanup())

    async def _process_async(self, text: str, context: str) -> Tuple[str, List[AIChange]]:
        """
        Async implementation of process().

        CRITICAL FIX (P1-3): Memory leak prevention
        - Limits all_changes tracking
        - Releases intermediate results
        - Monitors memory usage
        """
        chunks = self._split_into_chunks(text)
        all_changes = []

        # CRITICAL FIX: Memory warning for large files
        if len(chunks) > MEMORY_WARNING_THRESHOLD:
            logger.warning(
                f"Large file detected: {len(chunks)} chunks. "
                f"Will sample changes to limit memory usage."
            )

        logger.info(
            "Starting batch processing",
            extra={"total_chunks": len(chunks), "model": self.model,
                   "max_concurrent": self.max_concurrent}
        )

        # CRITICAL FIX: Error rate monitoring
        error_counter = ErrorCounter(threshold=0.3)

        # CRITICAL FIX: Calculate change sampling rate to limit memory
        # For large files, only track a sample of changes
        changes_per_chunk_limit = MAX_CHANGES_TO_TRACK // max(len(chunks), 1)
        if changes_per_chunk_limit < 1:
            changes_per_chunk_limit = 1
            logger.info(f"Sampling changes: max {changes_per_chunk_limit} per chunk")

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # Create tasks for all chunks
        tasks = [
            self._process_chunk_with_semaphore(
                i, chunk, context, semaphore, len(chunks)
            )
            for i, chunk in enumerate(chunks, 1)
        ]

        # Wait for all tasks to complete
        with timed_logger.timed("batch_processing", total_chunks=len(chunks)):
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results (maintaining order)
        corrected_chunks = []
        for i, (chunk, result) in enumerate(zip(chunks, results), 1):
            if isinstance(result, Exception):
                logger.error(
                    "Chunk failed after model attempts",
                    extra={"chunk_index": i, "error_type": type(result).__name__}
                )
                error_counter.failure()
            else:
                corrected_chunks.append(result)
                error_counter.success()

                # Extract actual changes for learning
                if result != chunk:
                    extracted_changes = self.change_extractor.extract_changes(chunk, result)

                    # CRITICAL FIX: Limit changes tracking to prevent memory bloat
                    # Sample changes if we're already tracking too many
                    if len(all_changes) < MAX_CHANGES_TO_TRACK:
                        # Convert to AIChange format (limit per chunk)
                        for change in extracted_changes[:changes_per_chunk_limit]:
                            all_changes.append(AIChange(
                                chunk_index=i,
                                from_text=change.from_text,
                                to_text=change.to_text,
                                confidence=change.confidence,
                                context_before=change.context_before,
                                context_after=change.context_after,
                                change_type=change.change_type
                            ))
                    else:
                        # Already at limit, skip tracking more changes
                        if i % 100 == 0:  # Log occasionally
                            logger.debug(
                                f"Reached changes tracking limit ({MAX_CHANGES_TO_TRACK}), "
                                f"skipping change tracking for remaining chunks"
                            )

                    # CRITICAL FIX: Explicitly release extracted_changes
                    del extracted_changes

        # CRITICAL FIX: Force garbage collection for large files
        if len(chunks) > MEMORY_WARNING_THRESHOLD:
            gc.collect()
            logger.debug("Forced garbage collection after processing large file")

        # Final statistics
        stats = error_counter.get_stats()
        logger.info(
            "Batch processing completed",
            extra={"total_chunks": len(chunks),
                   "successes": stats['total_successes'],
                   "failures": stats['total_failures'],
                   "failure_rate": stats['window_failure_rate'],
                   "changes_extracted": len(all_changes),
                   "status": "failed" if stats['total_failures'] else "success"}
        )

        # Do not deliver an unchanged failed chunk as an AI-corrected result.
        if stats['total_failures']:
            first_error = next(result for result in results if isinstance(result, Exception))
            raise RuntimeError(
                f"AI correction failed for {stats['total_failures']}/{len(chunks)} chunks"
            ) from first_error

        return "\n\n".join(corrected_chunks), all_changes

    async def _request_with_retry(self, chunk: str, context: str, model: str,
                                  attempts: int, chunk_index: int) -> str:
        """Preserve transient retries without logging provider exception bodies."""
        config = RetryConfig(max_attempts=attempts, base_delay=1.0)
        for attempt in range(attempts):
            try:
                return await self._process_chunk_async(chunk, context, model)
            except Exception as exc:
                retrying = is_transient_error(exc) and attempt + 1 < attempts
                logger.warning(
                    "Model request failed",
                    extra={"chunk_index": chunk_index, "model": model,
                           "attempt": attempt + 1, "retrying": retrying,
                           "error_type": type(exc).__name__}
                )
                if not retrying:
                    raise
                await asyncio.sleep(calculate_delay(attempt, config))

    async def _process_chunk_with_semaphore(
        self,
        chunk_index: int,
        chunk: str,
        context: str,
        semaphore: asyncio.Semaphore,
        total_chunks: int
    ) -> str:
        """Try the primary model, then the fallback; never silently reuse text."""
        async with semaphore:
            logger.info(
                "Processing chunk",
                extra={"chunk_index": chunk_index, "total_chunks": total_chunks,
                       "chunk_length": len(chunk)}
            )
            try:
                result = await self._request_with_retry(
                    chunk, context, self.model, 3, chunk_index
                )
                logger.info(
                    "Chunk completed with primary model",
                    extra={"chunk_index": chunk_index, "model": self.model}
                )
                return result
            except Exception as primary_error:
                logger.warning(
                    "Chunk failed with primary model",
                    extra={"chunk_index": chunk_index, "model": self.model,
                           "error_type": type(primary_error).__name__}
                )
                if not self.fallback_model or self.fallback_model == self.model:
                    raise RuntimeError("Primary model failed; no fallback configured") from primary_error

                logger.info(
                    "Retrying chunk with fallback model",
                    extra={"chunk_index": chunk_index, "fallback_model": self.fallback_model}
                )
                try:
                    result = await self._request_with_retry(
                        chunk, context, self.fallback_model, 2, chunk_index
                    )
                except Exception as fallback_error:
                    logger.error(
                        "Chunk failed with fallback model",
                        extra={"chunk_index": chunk_index, "model": self.fallback_model,
                               "error_type": type(fallback_error).__name__}
                    )
                    raise RuntimeError("Primary and fallback models failed") from fallback_error
                logger.info(
                    "Chunk succeeded with fallback model",
                    extra={"chunk_index": chunk_index, "model": self.fallback_model}
                )
                return result

    def _split_into_chunks(self, text: str) -> List[str]:
        """
        Split text into processable chunks

        Strategy:
        - Split by double newlines (paragraphs)
        - Keep chunks under max_chunk_size
        - Don't split mid-paragraph if possible
        """
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para_length = len(para)

            # If single paragraph exceeds limit, force split
            if para_length > self.max_chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Split long paragraph by sentences
                sentences = re.split(r'([。！？\n])', para)
                temp_para = ""
                for i in range(0, len(sentences), 2):
                    sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                    if len(temp_para) + len(sentence) > self.max_chunk_size:
                        if temp_para:
                            chunks.append(temp_para)
                        temp_para = sentence
                    else:
                        temp_para += sentence
                if temp_para:
                    chunks.append(temp_para)

            # Normal case: accumulate paragraphs
            elif current_length + para_length > self.max_chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length + 2  # +2 for \n\n

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    async def _process_chunk_async(self, chunk: str, context: str, model: str) -> str:
        """
        Process a single chunk with GLM API (async).

        CRITICAL FIX (P1-3): Uses shared HTTP client for connection pooling
        """
        prompt = self._build_prompt(chunk, context)

        url = f"{self.base_url}/v1/messages"
        headers = {
            "anthropic-version": "2023-06-01",
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json"
        }

        data = {
            "model": model,
            "max_tokens": 8000,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}]
        }

        # CRITICAL FIX: Use shared client instead of creating new one
        # This prevents connection descriptor leaks
        client = await self._get_http_client()
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["content"][0]["text"]

    def _build_prompt(self, chunk: str, context: str) -> str:
        """Build correction prompt for GLM"""
        base_prompt = """你是专业的会议记录校对专家。请修复以下会议转录中的语音识别错误。

**修复原则**：
1. 严格保留原有格式（时间戳、发言人标识、Markdown标记等）
2. 修复明显的同音字错误
3. 修复专业术语错误
4. 修复标点符号错误
5. 不要改变语句含义和结构

**不要做**：
- 不要添加或删除内容
- 不要重新组织段落
- 不要改变发言人标识
- 不要修改时间戳

直接输出修复后的文本，不要解释。
"""

        if context:
            base_prompt += f"\n\n**领域上下文**：{context}\n"

        return base_prompt + f"\n\n{chunk}"
