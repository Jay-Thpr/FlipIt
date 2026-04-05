from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel
from pydantic import ValidationError

from backend.config import get_agent_timeout_seconds

OutputModelT = TypeVar("OutputModelT", bound=BaseModel)


class BrowserUseRuntimeUnavailable(RuntimeError):
    pass


class BrowserUseTaskExecutionError(RuntimeError):
    pass


def classify_browser_use_failure(exc: Exception, *, operation: str | None = None) -> str:
    if isinstance(exc, BrowserUseRuntimeUnavailable):
        return "runtime_unavailable"
    if isinstance(exc, (BrowserUseTaskExecutionError, ValidationError, ValueError)):
        return "result_invalid"

    message = str(exc).lower()
    if "profile" in message:
        return "profile_missing"
    if "revision" in message:
        return "revision_failed"
    if "submit" in message or "publish" in message:
        return "submit_failed"
    if "abort" in message or "discard" in message or "close" in message:
        return "abort_failed"
    if operation == "prepare_listing_for_review":
        return "review_checkpoint_failed"
    if operation == "apply_listing_revision":
        return "revision_failed"
    if operation == "submit_prepared_listing":
        return "submit_failed"
    if operation == "abort_prepared_listing":
        return "abort_failed"
    return "browser_error"


def build_browser_use_metadata(
    *,
    mode: str,
    attempted_live_run: bool,
    profile_name: str | None = None,
    profile_available: bool | None = None,
    error_category: str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    return {
        "mode": mode,
        "attempted_live_run": attempted_live_run,
        "profile_name": profile_name,
        "profile_available": profile_available,
        "error_category": error_category,
        "detail": detail,
    }


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def should_force_browser_fallback() -> bool:
    return env_flag("BROWSER_USE_FORCE_FALLBACK", default=False)


def get_browser_use_model() -> str:
    return os.getenv("BROWSER_USE_GEMINI_MODEL", "gemini-2.0-flash")


def get_browser_profile_root() -> Path:
    return Path(os.getenv("BROWSER_USE_PROFILE_ROOT", "profiles"))


def get_browser_profile_path(profile_name: str) -> str:
    return str((get_browser_profile_root() / profile_name).resolve())


def get_browser_profile_kwargs(
    *,
    allowed_domains: list[str] | None = None,
    user_data_dir: str | None = None,
    keep_alive: bool = False,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "headless": False,
        "stealth": True,
    }
    if allowed_domains:
        kwargs["allowed_domains"] = allowed_domains
    if user_data_dir:
        kwargs["user_data_dir"] = user_data_dir
    if keep_alive:
        kwargs["keep_alive"] = True
    return kwargs


def get_browser_use_max_steps(default: int = 15) -> int:
    return int(os.getenv("BROWSER_USE_MAX_STEPS", str(default)))


def import_browser_use_dependencies() -> tuple[Any, Any, Any, Any]:
    from browser_use import Agent, BrowserSession
    from browser_use.browser import BrowserProfile
    from langchain_google_genai import ChatGoogleGenerativeAI

    return Agent, BrowserSession, BrowserProfile, ChatGoogleGenerativeAI


def browser_use_runtime_ready() -> bool:
    if should_force_browser_fallback():
        return False
    if not os.getenv("GOOGLE_API_KEY"):
        return False
    try:
        import_browser_use_dependencies()
    except Exception:
        return False
    return True


def summarize_browser_use_error(exc: Exception) -> str:
    if isinstance(exc, BrowserUseRuntimeUnavailable):
        return str(exc)
    message = str(exc).strip()
    if not message:
        return exc.__class__.__name__
    return message[:200]


async def run_structured_browser_task(
    *,
    task: str,
    output_model: type[OutputModelT],
    operation_name: str | None = None,
    allowed_domains: list[str] | None = None,
    user_data_dir: str | None = None,
    keep_alive: bool = False,
    max_steps: int | None = None,
    max_failures: int = 3,
) -> dict[str, Any]:
    if should_force_browser_fallback():
        raise BrowserUseRuntimeUnavailable("Browser Use fallback forced by environment")
    if not os.getenv("GOOGLE_API_KEY"):
        raise BrowserUseRuntimeUnavailable("GOOGLE_API_KEY is not configured")

    try:
        Agent, BrowserSession, BrowserProfile, ChatGoogleGenerativeAI = import_browser_use_dependencies()
    except Exception as exc:
        raise BrowserUseRuntimeUnavailable("Browser Use dependencies are not installed") from exc

    llm = ChatGoogleGenerativeAI(model=get_browser_use_model())
    browser_profile = BrowserProfile(
        **get_browser_profile_kwargs(
            allowed_domains=allowed_domains,
            user_data_dir=user_data_dir,
            keep_alive=keep_alive,
        )
    )
    session = BrowserSession(browser_profile=browser_profile)

    try:
        agent = Agent(
            task=task,
            llm=llm,
            browser_session=session,
            output_model_schema=output_model,
            max_steps=max_steps or get_browser_use_max_steps(),
            max_failures=max_failures,
        )
        history = await agent.run()
        result = history.final_result(output_model)
        if result is None:
            operation_label = operation_name or "browser task"
            raise BrowserUseTaskExecutionError(f"Browser Use returned no structured result for {operation_label}")
        if isinstance(result, BaseModel):
            return result.model_dump()
        return output_model.model_validate(result).model_dump()
    finally:
        stop = getattr(session, "stop", None)
        if stop is not None:
            await stop()


def get_browser_task_timeout_seconds() -> float:
    return max(30.0, get_agent_timeout_seconds())
