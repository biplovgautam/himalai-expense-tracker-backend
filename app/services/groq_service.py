import aiohttp
import json
import os
import certifi
import ssl
from typing import Dict, Any, Optional
from datetime import datetime

async def ask_groq(
    system_prompt: str, 
    user_prompt: str, 
    temperature: float = 0.2,
    max_tokens: int = 1000,
    model: str = None
) -> str:
    """
    Simple function to call Groq API with system and user prompts.
    
    Args:
        system_prompt: Instructions for the AI
        user_prompt: The user's query or content
        temperature: Controls randomness (0.0-1.0)
        max_tokens: Maximum number of tokens to generate
        model: Override the default model from settings
        
    Returns:
        The text response from Groq AI
    """
    api_key = os.getenv("GROQ_API_KEY")
    api_endpoint = os.getenv("GROQ_API_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions")
    
    # Updated default model from mixtral-8x7b-32768 to llama3-70b-8192
    ai_model = model or os.getenv("GROQ_MODEL", "llama3-70b-8192")
    
    # Add fallback models if the primary fails
    fallback_models = ["llama2-70b-4096", "claude-3-opus-20240229"]
    
    # Add this debugging before the API call
    if api_key:
        print(f"Using API key: {api_key[:5]}...")
    else:
        print("WARNING: No API key found!")
    
    # Create SSL context with certifi certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    try:
        # Use the SSL context in the ClientSession
        conn = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=conn) as session:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "model": ai_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            print(f"Calling Groq API with model: {ai_model}")
            async with session.post(api_endpoint, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Groq API Error ({response.status}): {error_text}")
                    # Return more detailed error information
                    return f"Error calling Groq API ({response.status}): {error_text[:500]}"
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]
                
    except Exception as e:
        print(f"Error in ask_groq: {str(e)}")
        return f"Error: {str(e)}"


# Add a class wrapper for backward compatibility
class GroqService:
    """
    Class wrapper around the ask_groq function for backward compatibility.
    """
    def __init__(self, output_dir=None):
        """Initialize the service with optional output directory"""
        from pathlib import Path
        self.output_dir = Path(output_dir) if output_dir else Path("./outputs")
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    async def process_chat(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process a chat message using Groq API"""
        system_prompt = user_input.get("system_prompt", "You are a helpful assistant.")
        user_prompt = user_input.get("message", "")
        
        response = await ask_groq(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=user_input.get("temperature", 0.2),
            max_tokens=user_input.get("max_tokens", 1000)
        )
        
        result = {
            "message": response,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save result if needed
        if hasattr(self, '_save_result'):
            self._save_result(result)
            
        return result
    
    def _save_result(self, data: dict) -> None:
        """Save chat results to file"""
        from uuid import uuid4
        
        result = {
            "id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            **data
        }
        
        file_path = self.output_dir / f"{result['id']}.json"
        with open(file_path, "w") as f:
            json.dump(result, f, indent=2)

#