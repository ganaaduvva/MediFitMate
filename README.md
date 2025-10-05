# MediFitMate

MediFitMate 🧑‍🤝‍🧑 is a WhatsApp health & fitness companion bot designed to support users in managing their workouts, meals, hydration, yoga sessions, and medication. With AI-powered insights, MediFitMate helps users maintain a healthier lifestyle through personalized guidance and real-time assistance.

---

## Features

- **Prescription Assistance:** Read and explain prescriptions to help users understand their medications.
- **Meal Understanding:** Guide users on meal compositions and nutritional content.
- **Personalized Meal Suggestions:** Offer meal recommendations tailored to users' health requirements.
- **Multi-language Support:** Communicate effectively with users in multiple languages for wider accessibility.

---

## Architecture Overview

MediFitMate integrates several powerful components and technologies to deliver seamless user experience:

- **Dockerized MCP Gateway:** Acts as a gateway connecting the bot to multiple AI services with a flexible and customizable orchestration layer using a custom catalog.
- **Medical MCP Server:** Implements specialized medical tools accessible via the MCP Gateway.
- **Cerebras Inference Model:** Used for executing large language models efficiently, powered by the Cerebras platform.
- **Llama Models:** Employed in the agent to provide thoughtful, context-aware conversational AI.
- **Google AI Developer Kit (Google ADK):** Provides the agent framework, session management, tool definition, and sophisticated runner capabilities.
- **Twilio API:** Manages WhatsApp messaging for interacting with users, sending and receiving messages, and integrating the health assistant seamlessly into the WhatsApp platform.

---

## Docker MCP Gateway Usage

The MCP Gateway enables MediFitMate to interact seamlessly with multiple AI models and tools. It is deployed as a Docker container configured with a custom `catalog.yaml` file describing the available MCP servers and tools.

Key points:

- **Custom Catalog:** The catalog specifies your medical MCP server (`medical-mcp`), its tools (e.g., drug info, health statistics, and literature search), and their endpoints.
- **Flexible Transport:** Uses Server-Sent Events (SSE) for event-driven communication between the gateway and MCP servers.
- **Docker Compose Integration:** The MCP Gateway container depends on the `medical-mcp` service and shares a user-defined bridge network, allowing smooth inter-container communication.

Example snippet from the Custom Catalog:

```
version: 2
name: custom-mcp
displayName: Custom MCP Catalog
registry:
  medical:
    enabled: true
    description: An MCP server providing medical information from FDA, WHO, PubMed, and RxNorm.
    title: Medical MCP Server
    type: server
    image: hackathon-test-medical-mcp:latest
    ref: ""
    readme: https://github.com/JamesANZ/medical-mcp/blob/main/README.md
    toolsUrl: /root/.docker/mcp/tools/medical-mcp.json
    source: https://github.com/JamesANZ/medical-mcp/tree/main
    upstream: https://github.com/JamesANZ/medical-mcp
    dateAdded: "2025-09-24T00:00:00Z"
    transport: sse
    sseEndpoint: http://medical-mcp:8000/sse
    tools:
      - name: "search-drugs"
      - name: "get-drug-details"
      - name: "get-health-statistics"
      - name: "get-article-details"
      - name: "search-drug-nomenclature"
      - name: "search-google-scholar"
      - name: "search-clinical-guidelines"
      - name: "check-drug-interactions"
      - name: "search-medical-databases"
      - name: "search-medical-journals"
    env:
      - name: NODE_ENV
        value: "development"
      - name: MCP_TIMEOUT
        value: "30000"
      - name: MCP_USER_AGENT
        value: "medical-mcp/1.0.0"
    command:
      - npm 
      - run
      - start:http
    prompts: 0
    resources: {}
    metadata:
      category: healthcare
      tags: 
        - medical
        - healthcare
        - pubmed
        - fda
      license: ISC
      owner: JamesANZ

```

Example snippet from the Docker Compose:

```
mcp-gateway:
  image: docker/mcp-gateway:latest
  container_name: mcp-gateway
  ports:
    - "9000:9000"
  networks:
    - hackathon-network
  depends_on:
    medical-mcp:
      condition: service_healthy
  command:
    - --servers=medical
    - --catalog=/mcp/catalog.yaml
    - --transport=sse
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
    - ./catalog.yaml:/mcp/catalog.yaml
    - ./tools:/mcp/tools:ro

```


---

## Cerebras Inference and Llama Models

- **Cerebras Model:** The backend uses Cerebras' `CerebrasLiteLlm` to run highly optimized inference on large language models. This accelerates response time and enables the handling of complex medical and fitness queries.
  
- **Llama Models:** The conversational agent is based on Llama models (e.g., `gemini-2.0-flash-001` or similar) to deliver natural, context-aware dialogue, enhancing user interactions.

These models are loaded and utilized through an async lifespan context to optimize resource consumption and startup performance.

---

## Google AI Developer Kit (Google ADK) Usage

MediFitMate leverages Google ADK's advanced agent framework for building interactive bots with:

- **LlmAgent:** The central conversational agent managing dialogue, tool invocation, and response generation.
- **MCPToolset:** Provides abstraction to interact with the Medical MCP server’s multiple medical tools seamlessly.
- **Session Management:** Using `InMemorySessionService` to maintain user sessions and conversation states.
- **Runner and Message Handling:** Coordinates asynchronous execution of agent tasks, streaming responses back to the client.

All components combine to provide robust, modular, and scalable AI-powered assistance.

---

## Twilio WhatsApp Integration

- **Twilio API** is used to bridge WhatsApp messages between users and the MediFitMate backend.
- MediFitMate receives incoming WhatsApp messages through Twilio webhooks.
- Outgoing messages, including AI-generated responses, are sent back to users via Twilio's WhatsApp messaging API.
- This integration enables real-time, reliable communication on a platform popular among the target audience.

Ensure you have configured your Twilio account SID, authentication token, and WhatsApp messaging number securely for proper operation.

---

## FastAPI Backend with Modern Lifespan Event Handling

The backend is built with FastAPI, using the modern recommended `lifespan` async context manager for startup and shutdown handling, including:

- Connecting and initializing MCP toolset during startup.
- Gracefully cleaning up resources and connections on shutdown.

This ensures efficient resource management and clean lifecycle handling.

---

## Getting Started

1. **Clone the repository** and ensure Docker and Docker Compose are installed.
2. **Configure environment variables** like `MCP_GATEWAY_URL`, `CEREBRAS_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and model references in an `.env` file.
3. **Run** the entire stack using `docker-compose up --build`.
4. **Interact** with MediFitMate via WhatsApp using your configured Twilio WhatsApp phone number.

---

MediFitMate bridges AI technology and health management, empowering users with personalized support for fitness, nutrition, and medication adherence all from their WhatsApp chat window.

---

*This README highlights the core architecture and technologies of the MediFitMate hackathon project, emphasizing the integration of Docker MCP Gateway, Cerebras inference, Llama models, Google ADK framework, and Twilio WhatsApp messaging.*
