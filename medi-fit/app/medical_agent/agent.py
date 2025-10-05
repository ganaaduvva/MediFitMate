import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from app.medical_agent.toolset import medical_toolset
from google.genai import types
from typing import List, Dict, Any
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from contextlib import asynccontextmanager

load_dotenv()

medical_assistance_agent = None 

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect MCP toolset via SSE connection params and initialize agent tools
    params = SseConnectionParams(url=os.getenv("MCP_GATEWAY_URL"))
    await medical_toolset.connect(params)
    tools = await medical_toolset.get_tools()

    global medical_assistance_agent
    medical_assistance_agent = LlmAgent(
        model="gemini-2.0-flash-001",
        name="medical_assistance_agent",
        description="You are an agent that can help user with medical related questions.",
        instruction="You are a helpful medical assistance agent. Use your specialized tools to answer questions about drugs, health statistics, and medical literature.",
        tools=tools,
    )

    yield  # Control goes to application serving requests here

    # Shutdown: cleanup code if any (e.g. disconnect toolset)
    await medical_toolset.disconnect()


app = FastAPI(lifespan=lifespan)


# Define request model
class QueryRequest(BaseModel):
    question: str


session_service = InMemorySessionService()


@app.get("/")
async def root():
    return {"message": "Welcome to the Medical Assistance Agent API!"}



@app.post("/ask")
async def ask_agent(req: QueryRequest):
    try:
        question_text: str = req.question
        print("Starting run_async with question:", question_text)

        user_id = "user_1"  # Or dynamic per caller

        # Try to get existing session first
        try:
            session = await session_service.get_session(user_id=user_id, app_name="medical_app")
        except Exception:
            # Create a new session if none exists
            session = await session_service.create_session(
                state={},
                app_name="medical_app",
                user_id=user_id
            )

        # Create runner
        runner = Runner(
            app_name='medical_app',
            agent=medical_assistance_agent,
            session_service=session_service,
        )

        # Create content for the message
        content = types.Content(
            role='user', 
            parts=[types.Part(text=question_text)]
        )

        # Collect agent response chunks
        chunks = []
        events_async = runner.run_async(
            session_id=session.id,
            user_id=session.user_id,
            new_message=content
        )

        async for event in events_async:
            # Extract text from event content if available
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts') and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            chunks.append(part.text)

        # Join chunks to make one combined response
        agent_response = "".join(chunks) if chunks else "No response generated"

        return {"response": agent_response, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "error"}


@app.get("/validate_toolset")
async def validate_toolset():
    tools = await medical_toolset.get_tools()
    for tool in tools:
        print(f"Tool: {tool.name} - {tool.description}")
