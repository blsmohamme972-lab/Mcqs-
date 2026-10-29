"""Publisher HTTP transport: bounded reads and credential-safe diagnostics."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "kafu-drain/1.0"
MAX_RESPONSE = 64 * 1024 * 1024
_SECRET_NAME = re.compile(r"TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY", re.I)
_TOKEN = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|cfut_[A-Za-z0-9_-]{20,}|\b\d{6,12}:[A-Za-z0-9_-]{25,})")


def sanitize_text(value: object, extra_secrets=()) -> str:
    """Redact before truncating. Never return request headers or signed queries."""
    text = str(value)
    secrets = [v for k, v in os.environ.items() if _SECRET_NAME.search(k) and len(v.strip()) >= 4]
    secrets.extend(str(v) for v in extra_secrets if v and len(str(v).strip()) >= 4)
    for secret in sorted(set(secrets), key=len, reverse=True):
        for variant in {secret, secret.strip(), urllib.parse.quote(secret, safe="")}:
            if variant:
                text = text.replace(variant, "<redacted>")
    text = _TOKEN.sub("<redacted>", text)
    text = re.sub(r"(?i)(Bearer|Basic)\s+[^\s\"'<>]+", r"\1 <redacted>", text)
    text = re.sub(r"(?i)((?:token|secret|password|api_key|signature|sig)[\"']?\s*[:=]\s*[\"']?)[^\s,\"'<>}]+", r"\1<redacted>", text)
    text = re.sub(r"(/(?:file/)?bot)[^/\s]+/", r"\1<redacted>/", text)
    def clean_url(match):
        try:
            parsed = urllib.parse.urlsplit(match.group(0))
            return urllib.parse.urlunsplit((parsed.scheme, parsed.hostname or "", parsed.path, "", ""))
        except ValueError:
            return "<redacted-url>"
    text = re.sub(r"https?://[^\s\"'<>]+", clean_url, text)
    return text


def _safe_path(url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlsplit(url)
    return parsed.hostname or "", sanitize_text(parsed.path or "/")


class HttpStepError(RuntimeError):
    def __init__(self, step: str, method: str, url: str, status: str | int, body: str = "") -> None:
        self.status = status
        self.step = step
        self.method = method
        self.host, self.path = _safe_path(url)
        self.body = sanitize_text(body)[:200]
        summary = f"step={step} method={method} host={self.host} path={self.path} status={status}"
        if self.body:
            summary += f" body={self.body!r}"
        super().__init__(summary)


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        before, after = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if after.scheme != "https" or after.username or after.password:
            raise urllib.error.URLError("unsafe redirect refused")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and (before.scheme, before.netloc) != (after.scheme, after.netloc):
            for name in list(dict(redirected.header_items())):
                if name.lower() in {"authorization", "cookie", "proxy-authorization", "x-telegram-bot-api-secret-token"}:
                    redirected.remove_header(name)
        return redirected


def _open(req, timeout):
    return urllib.request.build_opener(_SafeRedirect()).open(req, timeout=timeout)


def request_bytes(url: str, *, step: str, method: str = "GET", data: bytes | None = None,
                  headers: dict[str, str] | None = None, timeout: int = 30,
                  max_bytes: int = MAX_RESPONSE) -> bytes:
    method = method.upper()
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise HttpStepError(step, method, url, "invalid_url", "HTTPS URL without userinfo required")
    merged = {k: v for k, v in (headers or {}).items() if k.lower() != "user-agent"}
    merged["User-Agent"] = USER_AGENT
    req = urllib.request.Request(url, data=data, headers=merged, method=method)
    host, path = _safe_path(url)
    sensitive = [v for k, v in merged.items() if k.lower() in {"authorization", "cookie", "x-telegram-bot-api-secret-token"}]
    sensitive += [v.split(" ", 1)[-1] for v in sensitive]
    try:
        with _open(req, timeout=timeout) as response:
            status = response.status
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise HttpStepError(step, method, url, "too_large", "response exceeds configured byte limit")
            if not 200 <= status < 300:
                raise urllib.error.HTTPError(url, status, "non-2xx", response.headers, None)
            print(f"[http] step={step} method={method} host={host} path={path} status={status}", flush=True)
            return raw
    except urllib.error.HTTPError as exc:
        # Read enough to redact a reflected long credential before selecting 200 chars.
        limit = min(65536, 1024 + max((len(v.encode()) for v in sensitive), default=0))
        raw = exc.read(limit) if exc.fp is not None else b""
        body = sanitize_text(raw.decode("utf-8", errors="replace"), sensitive)[:200]
        safe_headers = exc.headers or {}
        server = sanitize_text(safe_headers.get("server", ""), sensitive)[:80]
        ray = sanitize_text(safe_headers.get("cf-ray", ""), sensitive)[:80]
        print(f"[http] step={step} method={method} host={host} path={path} status={exc.code} server={server!r} cf-ray={ray!r} body={body!r}", flush=True)
        raise HttpStepError(step, method, url, exc.code, body) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        detail = sanitize_text(getattr(exc, "reason", exc), sensitive)[:200]
        print(f"[http] step={step} method={method} host={host} path={path} status=network_error body={detail!r}", flush=True)
        raise HttpStepError(step, method, url, "network_error", detail) from None


def request_json(url: str, *, step: str, method: str = "GET", payload: Any | None = None,
                 data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    merged = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode()
        merged.setdefault("Content-Type", "application/json")
    raw = request_bytes(url, step=step, method=method, data=data, headers=merged, timeout=timeout)
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError):
        raise HttpStepError(step, method.upper(), url, "invalid_json", "response was not valid JSON") from None


def download(url: str, target: Path, *, step: str, headers: dict[str, str] | None = None,
             timeout: int = 90, max_bytes: int | None = None) -> int:
    raw = request_bytes(url, step=step, headers=headers, timeout=timeout,
                        max_bytes=MAX_RESPONSE if max_bytes is None else max_bytes)
    target.write_bytes(raw)
    return len(raw)
