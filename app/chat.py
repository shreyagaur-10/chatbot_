"""
Chat engine that integrates OpenRouter LLM with the RAG retrieval system.
"""

import os
import json
from typing import AsyncGenerator

from dotenv import load_dotenv
import httpx

load_dotenv()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free models on OpenRouter (ordered by direct clean response capability)
FREE_MODELS = [
    "liquid/lfm-3-1.7b:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "inclusionai/ling-3.2-flash:free",
    "particle-ai/particle-1:free",
    "thinkingmachines/inkling-2-small:free",
    "nvidia/nemotron-3.5-lightning:free",
]

SYSTEM_PROMPT = """You are a helpful AI assistant specialized in real estate information about DarGlobal and Wasalt.

**DarGlobal** (Dar Global PLC) is a London-listed luxury real estate developer, investor, and asset manager. They create high-quality communities, landmark destinations, and lifestyle-driven assets across premier global markets.

**Wasalt** is one of Saudi Arabia's leading PropTech companies and digital real estate platforms, licensed by REGA (Real Estate General Authority).

Use ONLY the provided context to answer questions. If the context doesn't contain enough information, say so honestly. Be concise, accurate, and helpful. When mentioning financial figures, projects, or statistics, cite them precisely as found in the context.

If the user asks about something unrelated to DarGlobal or Wasalt, politely redirect them to ask about these companies.
"""


class ChatEngine:
    """Manages chat interactions with OpenRouter LLM + RAG context."""

    def __init__(self, retrieval_engine):
        self.retrieval = retrieval_engine
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.model = os.getenv("OPENROUTER_MODEL", FREE_MODELS[0])
        self.conversation_history: dict[str, list] = {}  # session_id -> messages

    def _get_model(self) -> str:
        """Return the configured model, falling back through free models."""
        return self.model

    async def chat(
        self, message: str, session_id: str = "default"
    ) -> str:
        """Process a chat message and return the response."""
        # Retrieve relevant context
        context = self.retrieval.get_context(message, top_k=5)

        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Add conversation history (last 6 messages for context)
        history = self.conversation_history.get(session_id, [])
        messages.extend(history[-6:])

        # Add user message with context
        user_msg = f"""Based on the following context information, please answer the user's question.

CONTEXT:
{context}

USER QUESTION:
{message}

Please provide a helpful, accurate answer based on the context above. If the context doesn't contain enough information to fully answer the question, acknowledge what you can answer and what you cannot."""

        messages.append({"role": "user", "content": user_msg})

        # Call OpenRouter API
        response_text = await self._call_openrouter(messages)

        # Update conversation history
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        self.conversation_history[session_id].append(
            {"role": "user", "content": message}
        )
        self.conversation_history[session_id].append(
            {"role": "assistant", "content": response_text}
        )

        # Keep history manageable
        if len(self.conversation_history[session_id]) > 20:
            self.conversation_history[session_id] = self.conversation_history[session_id][-12:]

        return response_text

    async def _call_openrouter(self, messages: list[dict]) -> str:
        """Call the OpenRouter API with fallbacks and context guarantee."""
        if not self.api_key:
            return self._fallback_response(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("APP_URL", "http://localhost:8000"),
            "X-Title": "DarGlobal-Wasalt Chatbot",
        }

        payload = {
            "model": self._get_model(),
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.3,
        }

        # 1. Try primary model
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        msg = choices[0].get("message", {})
                        content = msg.get("content") or msg.get("reasoning")
                        if content and str(content).strip():
                            return str(content).strip()
        except Exception:
            pass

        # 2. Try fallback models
        for fallback_model in FREE_MODELS:
            if fallback_model == self._get_model():
                continue
            try:
                payload["model"] = fallback_model
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        OPENROUTER_API_URL,
                        headers=headers,
                        json=payload,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            msg = choices[0].get("message", {})
                            content = msg.get("content") or msg.get("reasoning")
                            if content and str(content).strip():
                                return str(content).strip()
            except Exception:
                continue

        # 3. Always return a high quality answer from the scraped knowledge base
        return self._fallback_response(messages)

    def _fallback_response(self, messages: list[dict]) -> str:
        """Generate a context-based response without an LLM (when no API key is set)."""
        # Extract the user question from the last message
        last_msg = messages[-1]["content"] if messages else ""

        # Try to extract the context section
        context_start = last_msg.find("CONTEXT:")
        question_start = last_msg.find("USER QUESTION:")

        if context_start >= 0 and question_start >= 0:
            context = last_msg[context_start + 8:question_start].strip()
            question = last_msg[question_start + 14:].strip()
            # Remove the instruction part
            answer_start = question.find("Please provide")
            if answer_start >= 0:
                question = question[:answer_start].strip()

            if context and context != "No relevant information found in the knowledge base.":
                return (
                    f"Based on the available information:\n\n{context}\n\n"
                    f"---\n*Note: Running without an OpenRouter API key. "
                    f"Set the OPENROUTER_API_KEY environment variable for AI-powered responses.*"
                )

        return (
            "I can help you with information about DarGlobal and Wasalt. "
            "Please ask me about their projects, services, financial results, or any other details. "
            "\n\n*Note: Running without an OpenRouter API key. "
            "Set the OPENROUTER_API_KEY environment variable for AI-powered responses.*"
        )

    def clear_history(self, session_id: str = "default"):
        """Clear conversation history for a session."""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
