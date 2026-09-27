"""Replaceable company boundaries. No provider response can dispatch a tool."""
from __future__ import annotations

import copy
import json
import os
import re
import ssl
from datetime import date, datetime, timedelta, timezone
from typing import Protocol
from urllib.parse import urlsplit


class GatewayError(ValueError):
    """Safe, user-facing failure; never wrap a provider response body."""


class AssistantGateway(Protocol):
    def respond(self, messages: list[dict], purpose: str = "chat") -> str: ...


class QueryGateway(Protocol):
    def catalog(self) -> list[dict]: ...
    def validate(self, query_id: str, parameters: dict) -> None: ...
    def run(self, query_id: str, parameters: dict) -> dict: ...


class IdentityProvider(Protocol):
    def current(self) -> dict: ...


class DemoIdentity:
    def current(self) -> dict:
        return {"subject": "local-demo", "name": "本機示範使用者（非 AD）", "mode": "demo"}


class CompanyIdentity:
    def current(self) -> dict:
        raise GatewayError("公司 AD 與使用名單尚未配置，無法啟用正式身分。")


class OracleQueries:
    def catalog(self) -> list[dict]:
        return []

    def run(self, query_id: str, parameters: dict) -> dict:
        self.validate(query_id, parameters)

    def validate(self, query_id: str, parameters: dict) -> None:
        raise GatewayError("Oracle 尚未接線；Q01～Q03 正式查詢保持停用。")


PURPOSES = {
    "chat": "用繁體中文回答；不知道時說明未知。不要聲稱執行工具、查詢資料庫或建立排程。",
    "summarize": "根據提供內容整理重點，區分原文事實與推測，缺資料不要編造；不要自行計算 CSV 數值。",
    "rewrite": "只改寫提供文字，保留事實與數值，不新增承諾或資訊，輸出可供使用者預覽的候選文字。",
}


def validated_messages(messages: list[dict], limit: int = 50000) -> list[dict]:
    if not isinstance(messages, list) or not messages:
        raise GatewayError("請先輸入內容。")
    result = []
    for item in messages:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            raise GatewayError("對話格式不正確。")
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            raise GatewayError("對話內容不可空白。")
        result.append({"role": item["role"], "content": content})
    if sum(len(m["content"]) for m in result) > limit:
        raise GatewayError("內容超過已設定的文字上限，請縮小資料或開始新對話；未截斷送出。")
    return result


class DemoAssistant:
    def respond(self, messages: list[dict], purpose: str = "chat") -> str:
        if purpose not in PURPOSES:
            raise GatewayError("不支援的助理操作。")
        content = validated_messages(messages)[-1]["content"]
        prefix = "【本機示範回應，未呼叫 AI／公司服務】\n"
        if purpose == "summarize":
            return prefix + f"已提供 {len(content)} 個字元、{len(content.splitlines())} 行。\n這是程式計數，尚未產生語意摘要；接通公司 chatbot 後可整理重點。"
        if purpose == "rewrite":
            return prefix + "以下保留原文作為預覽示範，沒有假裝完成 AI 改寫：\n\n" + content
        return prefix + "已收到你的內容。可使用「查資料」體驗三項合成查詢，或使用整理／改寫預覽。接通公司 chatbot 後才會產生真正的助理回答。"


class CompanyAssistant:
    """Stateless Chat Completions adapter. Company-specific changes belong here.

    `client` is an injected SDK client for offline tests. No session ID is shared.
    `header_env` maps custom header names to environment-variable names.
    `assistant_ref` plus `assistant_ref_field` adds exactly one company body field.
    """

    def __init__(self, config: dict, client=None, api_key=None):
        from openai import OpenAI
        import httpx

        self.config = copy.deepcopy(config.get("assistant", config))
        base = self.config.get("base_url", "")
        try:
            parsed = urlsplit(base)
            valid = (parsed.scheme == "https" and parsed.hostname and not parsed.username
                     and not parsed.password and not parsed.query and not parsed.fragment)
        except (TypeError, ValueError):
            valid = False
        if not valid or parsed.hostname.lower().rstrip(".") in {"api.openai.com", "openai.com"}:
            raise GatewayError("請設定公司的 HTTPS chatbot 端點；不使用公共預設端點或網址內帳密。")
        self.model = self.config.get("model")
        if not isinstance(self.model, str) or not self.model.strip():
            raise GatewayError("請填公司指定的模型／助理名稱。")
        timeout = self.config.get("timeout_seconds", 30)
        limit = self.config.get("max_context_chars", 50000)
        if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not 1 <= timeout <= 120:
            raise GatewayError("timeout_seconds 必須介於 1 與 120 秒。")
        if type(limit) is not int or not 1 <= limit <= 50000:
            raise GatewayError("max_context_chars 必須介於 1 與 50000。")
        self.limit = limit
        env = self.config.get("api_key_env", "UNIT_HELPER_API_KEY")
        key = api_key if api_key is not None else (os.environ.get(env, "") if isinstance(env, str) else "")
        if not key:
            raise GatewayError("未設定公司 API 金鑰環境變數。")
        headers = {}
        mapping = self.config.get("header_env", {})
        if not isinstance(mapping, dict):
            raise GatewayError("header_env 必須是標頭名稱與環境變數名稱的對照。")
        for name, env_name in mapping.items():
            if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9-]+", name)
                    or name.lower() in {"authorization", "host", "content-length", "content-type"}
                    or not isinstance(env_name, str)):
                raise GatewayError("自訂 HTTP 標頭設定不正確。")
            value = os.environ.get(env_name, "")
            if not value or "\r" in value or "\n" in value:
                raise GatewayError("自訂 HTTP 標頭的環境變數缺少或格式錯誤。")
            headers[name] = value
        self.extra_body = None
        ref = self.config.get("assistant_ref")
        if ref is not None:
            field = self.config.get("assistant_ref_field")
            if (not isinstance(field, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field)
                    or field in {"messages", "model", "stream", "tools", "tool_choice"}
                    or not isinstance(ref, str) or not ref.strip()):
                raise GatewayError("助理識別需指定公司文件中的 assistant_ref_field；不可覆蓋核心請求欄位。")
            self.extra_body = {field: ref}
        ca_bundle = self.config.get("ca_bundle")
        tls_context = True
        if ca_bundle is not None:
            if not isinstance(ca_bundle, str) or not ca_bundle.strip():
                raise GatewayError("ca_bundle 需為有效的公司 CA 憑證檔路徑。")
            try:
                tls_context = ssl.create_default_context(cafile=ca_bundle)
            except (OSError, ssl.SSLError):
                raise GatewayError("無法載入公司 CA 憑證檔；請確認路徑與 PEM 格式。TLS 驗證不會停用。") from None
        self.client = client or OpenAI(
            base_url=base, api_key=key, timeout=timeout, max_retries=0,
            default_headers=headers,
            http_client=httpx.Client(follow_redirects=False, timeout=timeout, verify=tls_context),
        )

    def respond(self, messages: list[dict], purpose: str = "chat") -> str:
        from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError
        if purpose not in PURPOSES:
            raise GatewayError("不支援的助理操作。")
        clean = validated_messages(messages, self.limit)
        try:
            kwargs = {"model": self.model, "messages": [{"role": "system", "content": PURPOSES[purpose]}] + clean,
                      "stream": False}
            if self.extra_body is not None:
                kwargs["extra_body"] = self.extra_body
            response = self.client.chat.completions.create(**kwargs)
            # Never execute tool calls or treat them as successful text.
            message = response.choices[0].message
            if getattr(message, "tool_calls", None) or getattr(message, "function_call", None):
                raise GatewayError("公司服務要求工具操作；此接線僅接受文字，沒有執行工具。")
            value = message.content
            if not isinstance(value, str) or not value.strip():
                raise GatewayError("公司服務回覆空白或非文字格式，請確認串接格式。")
            return value
        except APITimeoutError:
            raise GatewayError("公司服務逾時；沒有自動重試。遠端是否已完成需另行確認。") from None
        except APIStatusError as exc:
            label = "認證失敗" if exc.status_code in {401, 403} else f"HTTP {exc.status_code} 錯誤"
            raise GatewayError("公司服務" + label + "；請確認設定或聯絡維護者。") from None
        except APIConnectionError:
            raise GatewayError("無法連線公司服務；請檢查內網、憑證及端點。") from None
        except (APIError, AttributeError, IndexError, TypeError, KeyError):
            raise GatewayError("公司服務回傳格式不相容；請由公司 agent 調整串接模組。") from None

    def close(self):
        self.client.close()


def _column(name, label, type="text", copy_as_text=False):
    return {"name": name, "label": label, "type": type, "copy_as_text": copy_as_text}


class DemoQueries:
    def catalog(self) -> list[dict]:
        parameters = {
            "from_date": {"label": "起日（含）", "type": "date", "default": (date.today()-timedelta(days=1)).isoformat()},
            "to_date": {"label": "迄日（不含）", "type": "date", "default": date.today().isoformat()},
            "category": {"label": "類別", "type": "single_choice", "options": ["all", "A", "B"], "default": "all"},
        }
        return [
            {"id": "DEMO01", "name": "示範庫存明細", "description": "合成庫存異動資料，非公司庫存。", "example": "查昨天的 A 類庫存", "parameters": copy.deepcopy(parameters), "date_range": {"start":"from_date", "end":"to_date"},
             "columns": [_column("record_date", "日期"), _column("item_id", "料號", copy_as_text=True), _column("category", "類別"), _column("quantity", "數量", "integer")]},
            {"id": "DEMO02", "name": "示範訂單明細", "description": "合成訂單及精確金額字串，非公司訂單。", "example": "查昨天的全部訂單", "parameters": copy.deepcopy(parameters), "date_range": {"start":"from_date", "end":"to_date"},
             "columns": [_column("record_date", "日期"), _column("order_id", "訂單編號", copy_as_text=True), _column("category", "類別"), _column("amount", "金額", "decimal", True)]},
            {"id": "DEMO03", "name": "示範數量合計", "description": "以同一批示範庫存異動計算總量，可測門檻通知。", "example": "查昨天 A 類數量合計", "parameters": copy.deepcopy(parameters), "date_range": {"start":"from_date", "end":"to_date"},
             "columns": [_column("quantity", "合計數量", "integer")]},
        ]

    def validate(self, query_id: str, parameters: dict) -> None:
        catalog = {q["id"]: q for q in self.catalog()}
        if query_id not in catalog:
            raise GatewayError("查詢不存在或尚未接線；只允許 DEMO01～DEMO03。")
        if not isinstance(parameters, dict) or set(parameters) != {"from_date", "to_date", "category"}:
            raise GatewayError("查詢需且僅需 from_date、to_date、category。")
        try:
            if any(not isinstance(parameters[k], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", parameters[k]) for k in ("from_date", "to_date")):
                raise ValueError()
            start, end = date.fromisoformat(parameters["from_date"]), date.fromisoformat(parameters["to_date"])
        except (ValueError, TypeError):
            raise GatewayError("日期格式需為有效 YYYY-MM-DD。") from None
        if (not 1 <= (end - start).days <= 90 or not isinstance(parameters["category"], str)
                or parameters["category"] not in {"all", "A", "B"}):
            raise GatewayError("日期需為 1～90 天且迄日不含；類別只能為 all、A 或 B。")

    def run(self, query_id: str, parameters: dict) -> dict:
        self.validate(query_id, parameters)
        catalog = {q["id"]: q for q in self.catalog()}
        start, end = date.fromisoformat(parameters["from_date"]), date.fromisoformat(parameters["to_date"])
        rows, total = [], 0
        for day in range((end - start).days):
            current = start + timedelta(days=day)
            for i in range(150):
                category = "A" if i % 2 == 0 else "B"
                if parameters["category"] not in {"all", category}:
                    continue
                quantity = (current.toordinal() + i) % 40 + 1
                total += quantity
                if query_id == "DEMO01":
                    rows.append([current.isoformat(), f"{i + 1:06d}", category, quantity])
                elif query_id == "DEMO02":
                    rows.append([current.isoformat(), f"{current:%Y%m%d}{i + 1:010d}", category, f"{quantity * 13}.{i % 100:02d}"])
        if query_id == "DEMO03":
            rows = [[total]]
        truncated = len(rows) > 1000
        rows = rows[:1000]
        result = {"query_ref": {"id": query_id, "version": 1}, "parameters": copy.deepcopy(parameters),
                  "columns": catalog[query_id]["columns"], "rows": rows, "row_count": len(rows),
                  "truncated": truncated, "source_label": "本機合成示範資料（非 Oracle／公司資料）",
                  "fetched_at_utc": datetime.now(timezone.utc).isoformat()}
        if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > 2 * 1024 * 1024:
            raise GatewayError("結果超過 2 MiB，請縮小條件。")
        return result
