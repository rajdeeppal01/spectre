import logging
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from src.guardrails import AIGuardrail

# Configure structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ai_pipeline_app")

app = FastAPI(
    title="Secure AI Pipeline API",
    version="1.0.0",
    description="Production-ready FastAPI service with OWASP LLM guardrails and automated security checks."
)

guardrail = AIGuardrail()

class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="User prompt to evaluate and process")
    user_id: str = Field(default="anonymous", description="Identifier of the requesting user")

class PromptResponse(BaseModel):
    status: str
    message: str
    processed_response: str

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for Kubernetes / Docker container health probes."""
    return {"status": "healthy", "service": "secure-ai-pipeline"}

@app.post("/api/v1/generate", response_model=PromptResponse, status_code=status.HTTP_200_OK)
async def generate_response(payload: PromptRequest):
    """
    Evaluates prompt through AI Guardrails and simulates secure LLM generation.
    """
    logger.info(f"Received prompt generation request from user: {payload.user_id}")

    # 1. Validate prompt through AIGuardrail
    is_safe, reason = guardrail.validate_prompt(payload.prompt)
    if not is_safe:
        logger.warning(f"Guardrail violation blocked request. Reason: {reason}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "SecurityViolation",
                "message": reason,
                "code": "LLM_GUARDRAIL_BLOCKED"
            }
        )

    # 2. Simulate secure LLM downstream generation (in production, invoke OpenAI / Anthropic / local model)
    simulated_raw_output = f"Processed securely: {payload.prompt[::-1]}" # Mock processing
    sanitized_output = guardrail.sanitize_output(simulated_raw_output)

    logger.info("Prompt successfully processed and sanitized.")
    return PromptResponse(
        status="success",
        message="Prompt evaluated and processed securely.",
        processed_response=sanitized_output
    )
