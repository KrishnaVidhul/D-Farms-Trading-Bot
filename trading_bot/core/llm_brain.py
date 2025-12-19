import os
import json
import logging
from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntelligentBrain")

class IntelligentBrain:
    def __init__(self):
        """Initialize Brain with API clients"""
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

        if not self.groq_key:
            logger.warning("GROQ_API_KEY is missing!")
        if not self.openai_key:
            logger.warning("OPENAI_API_KEY is missing!")

        # Initialize Clients
        try:
            self.groq_client = Groq(api_key=self.groq_key)
            self.openai_client = OpenAI(api_key=self.openai_key)
            logger.info("🧠 Intelligent Brain Initialized (Groq + OpenAI)")
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            raise e

        # Cost tracking
        self.audit_log = []

    def _audit_cost(self, model, tokens, source="OpenAI"):
        """Simple audit logger for cost control"""
        # Approx cost per 1k input tokens (as of late 2024 for 4o-mini) ~ $0.00015
        # This is a rough estimation
        cost_entry = {
            "source": source,
            "model": model,
            "tokens": tokens,
            "timestamp": "now" # In real app use datetime
        }
        self.audit_log.append(cost_entry)
        if source == "OpenAI":
             logger.info(f"💰 OpenAI Cost Audit: ~{tokens} tokens used ({model})")

    def fast_think(self, prompt, system_prompt="You are a helpful trading assistant."):
        """
        Uses Groq (Llama3-70b) for high-speed reasoning.
        Best for: News analysis, quick sentiment, formatting.
        """
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.5,
                max_tokens=1024,
            )
            response = chat_completion.choices[0].message.content
            return response
        except Exception as e:
            logger.error(f"⚡ fast_think (Groq) failed: {e}. Falling back to deep_think...")
            return self.deep_think(prompt, system_prompt + " (Fallback Context)")

    def deep_think(self, prompt, system_prompt="You are a senior financial risk manager."):
        """
        Uses OpenAI (gpt-4o-mini) for complex analytical tasks.
        Best for: Risk Audits, Strategy Changes, Coding.
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2048
            )
            
            # Audit Logic
            usage = response.usage
            total_tokens = usage.total_tokens
            self._audit_cost("gpt-4o-mini", total_tokens, source="OpenAI")
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"🧠 deep_think (OpenAI) failed: {e}")
            return "Error: Brain failure. Both systems unresponsive."

    def analyze_sentiment(self, text):
        """
        Uses Groq to return structured JSON sentiment analysis.
        Returns: {'sentiment': 'POSITIVE', 'score': 0.95, 'reasoning': '...'}
        """
        system_prompt = (
            "You are a financial sentiment analyzer. "
            "Analyze the text and return a JSON object with: "
            "{'sentiment': 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL', "
            "'score': float (0.0 to 1.0), 'reasoning': 'brief explanation'}. "
            "Output ONLY JSON."
        )
        
        try:
            # Using Groq with JSON mode if available, or just strict prompting
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.1, # Low temp for consistent JSON
                response_format={"type": "json_object"}
            )
            raw_json = chat_completion.choices[0].message.content
            return json.loads(raw_json)
            
        except Exception as e:
            logger.error(f"Sentiment Analysis Error: {e}. Attempting Fallback.")
            # Simple Fallback to neutral if parsing fails
            return {'sentiment': 'NEUTRAL', 'score': 0.5, 'reasoning': f"Error: {e}"}

# Simple Test
if __name__ == "__main__":
    brain = IntelligentBrain()
    print("--- Testing Fast Think ---")
    print(brain.fast_think("What adds complexity to a trading algorithm?"))
    print("\n--- Testing Sentiment ---")
    print(brain.analyze_sentiment("Apple reports record breaking profits but warns of supply chain issues."))
