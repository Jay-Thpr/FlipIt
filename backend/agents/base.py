from __future__ import annotations

from abc import ABC, abstractmethod

from fastapi import FastAPI
from pydantic import BaseModel, ValidationError

from backend.schemas import AgentTaskRequest, AgentTaskResponse, validate_agent_task_request


class BaseAgent(ABC):
    def __init__(self, *, slug: str, display_name: str, output_model: type[BaseModel]) -> None:
        self.slug = slug
        self.display_name = display_name
        self.output_model = output_model

    async def handle_task(self, request: AgentTaskRequest) -> AgentTaskResponse:
        try:
            request = validate_agent_task_request(self.slug, request)
        except (ValidationError, ValueError) as exc:
            return AgentTaskResponse(
                session_id=request.session_id,
                step=request.step,
                status="failed",
                error=f"Input validation failed for {self.slug}: {exc}",
            )

        try:
            output = await self.build_output(request)
            validated_output = self.output_model.model_validate(output).model_dump()
            return AgentTaskResponse(
                session_id=request.session_id,
                step=request.step,
                status="completed",
                output=validated_output,
            )
        except ValidationError as exc:
            return AgentTaskResponse(
                session_id=request.session_id,
                step=request.step,
                status="failed",
                error=f"Output validation failed for {self.slug}: {exc}",
            )
        except Exception as exc:
            return AgentTaskResponse(
                session_id=request.session_id,
                step=request.step,
                status="failed",
                error=f"{self.slug} execution failed: {exc}",
            )

    @abstractmethod
    async def build_output(self, request: AgentTaskRequest) -> dict:
        raise NotImplementedError


class StubAgent(BaseAgent):
    def __init__(self, *, slug: str, display_name: str, default_output: dict, output_model: type[BaseModel]) -> None:
        super().__init__(slug=slug, display_name=display_name, output_model=output_model)
        self.default_output = default_output

    async def build_output(self, request: AgentTaskRequest) -> dict:
        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"{self.display_name} completed {request.step}",
            **self.default_output,
        }


def build_agent_app(agent: StubAgent) -> FastAPI:
    app = FastAPI(title=agent.display_name)

    @app.get("/health")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "agent": agent.slug}

    @app.post("/task", response_model=AgentTaskResponse)
    async def task(request: AgentTaskRequest) -> AgentTaskResponse:
        return await agent.handle_task(request)

    @app.post("/chat")
    async def chat(request: dict) -> dict:
        return {
            "status": "not_implemented",
            "agent": agent.slug,
            "message": "Fetch.ai Chat Protocol scaffold placeholder",
            "request": request,
        }

    return app
