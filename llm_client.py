import os
import json

class LLMClient:
    """
    Client for interacting with the Google Gemini API.
    
    This class handles the generation of personalized coaching reports based on
    the user's chess statistics and opening performance.
    """
    
    def __init__(self):
        """
        Initialize the LLMClient.
        
        Retrieves the API key from environment variables and configures the Gemini model.
        """
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("Warning: GOOGLE_API_KEY not found in environment variables.")
            self.model = None
        else:
            import google.generativeai as genai  # imported lazily: only needed when Gemini is selected
            genai.configure(api_key=self.api_key)
            # Use 'gemini-2.0-flash' as it is available and fast
            self.model_name = 'gemini-2.0-flash'
            self.model = genai.GenerativeModel(self.model_name)

    def chat(self, messages, context=None):
        """
        Send a chat history to Gemini and get a response.
        
        Args:
            messages (list): List of message dicts [{'role': 'user', 'content': '...'}, ...]
            context (str): Optional context string about the user.
            
        Returns:
            str: The assistant's response.
        """
        if not self.model:
            return "Error: Google API Key not configured."
            
        try:
            # Convert OpenAI-style messages to Gemini history
            history = []
            last_user_message = ""
            
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                if msg["role"] == "system":
                    # Prepend system prompt to the first user message or handle separately
                    continue
                
                if role == "user":
                    last_user_message = msg["content"]
                    # Inject context into the latest user message if provided
                    if context and msg == messages[-1]:
                        last_user_message = f"[Context: {context}]\n\n{last_user_message}"
                else:
                    history.append({"role": "user", "parts": [last_user_message]}) # Gemini expects user before model
                    history.append({"role": "model", "parts": [msg["content"]]})
            
            # Start chat session
            chat = self.model.start_chat(history=history)
            
            # Send the last message
            response = chat.send_message(last_user_message)
            return response.text
            
        except Exception as e:
            return f"Error with Gemini Chat: {str(e)}"
