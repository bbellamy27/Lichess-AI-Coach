import requests
import json

class PuterClient:
    """
    Client for interacting with the Free AI API (via Pollinations.ai).
    This replaces the old Puter implementation which was 403 blocked.
    """
    
    def __init__(self):
        self.url = "https://text.pollinations.ai/"
        self.model = "openai" # Uses their default best available model

    def chat(self, messages, context=None):
        """
        Send a chat history to Free AI and get a response.
        """
        system_content = (
            "You are 'Coach', a friendly chess coach. "
            "Explain clearly, give practical advice, and be supportive."
        )
        
        if context:
            system_content += f"\n\nUSER DATA:\n{context}"

        # Construct messages for Pollinations
        full_messages = [{"role": "system", "content": system_content}]
        
        for msg in messages:
            if msg["role"] != "system":
                # Ensure content is a string
                content = str(msg.get("content", ""))
                full_messages.append({"role": msg["role"], "content": content})

        payload = {
            "messages": full_messages,
            "model": self.model,
            "jsonMode": False # Explicitly disable JSON mode to avoid 400s on some endpoints
        }
        
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            return response.text
        except Exception as e:
            # Fallback for 400 errors (often due to context length or format)
            if "400" in str(e):
                try:
                    # Retry with a simpler payload (just the last message)
                    last_msg = messages[-1]["content"]
                    simple_payload = {
                        "messages": [
                            {"role": "system", "content": "You are a helpful chess coach."},
                            {"role": "user", "content": f"Context: {context}\n\nQuestion: {last_msg}"}
                        ],
                        "model": self.model
                    }
                    response = requests.post(self.url, headers=headers, json=simple_payload)
                    response.raise_for_status()
                    return response.text
                except Exception as e2:
                    return f"⚠️ Error (Retry Failed): {e2}"
            return f"⚠️ Error contacting Coach: {e}"

if __name__ == "__main__":
    client = PuterClient()
    print("PuterClient (Pollinations) initialized.")
