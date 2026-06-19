from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import db_dependency
from app.services.llm_agent import run_agent

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: list = []


@router.post("")
def chat(req: ChatRequest, conn=Depends(db_dependency)):
    try:
        reply, history, tool_trace = run_agent(
            conn=conn,
            message=req.message,
            history=req.history,
        )

        return {
            "reply": reply,
            "history": history,
            "tool_trace": tool_trace,
        }

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Sprandy couldn't reach Ollama: {str(e)}"
        )