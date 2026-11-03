import requests
import os
import json

class GroqClient:
    """
    Client for interacting with the Groq API (Llama 3).
    """
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"

    def chat(self, messages, context=None):
        """
        Send a chat history to Groq and get a response.
        """
        if not self.api_key:
            return "Error: Groq API Key not configured."

        system_content = (
            "You are 'Coach', a friendly chess coach and study assistant. "
            "You explain concepts clearly, give practical improvement advice, "
            "and stay supportive. You can answer chess questions, study plans, "
            "emotions, mindset, or strategy. Always be helpful and positive."
        )
        
        if context:
            system_content += f"\n\nCURRENT USER DATA:\n{context}\nUse this data to personalize your advice."

        # Prepare messages list with system prompt first
        full_messages = [{"role": "system", "content": system_content}]
        
        # Append user history (filtering out any previous system messages if passed in raw)
        for msg in messages:
            if msg["role"] != "system":
                full_messages.append(msg)

        payload = {
            "model": self.model,
            "messages": full_messages
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error with Groq Chat: {e}"

if __name__ == "__main__":
    client = GroqClient()
    print("GroqClient initialized.")
