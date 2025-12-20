"""
Unified LLM Client
Supports both OpenAI and Google Gemini APIs
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv


class LLMClient:
    """
    Unified interface for multiple LLM providers
    Supports: OpenAI (GPT), Google (Gemini)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize LLM client with configuration
        
        Args:
            config: Optional config dict with keys:
                - provider: "openai" or "google"
                - model: Model name
                - api_key: API key (optional, reads from env)
                - temperature: Generation temperature
        """
        self.config = config or {}
        
        # Load from .env file
        load_dotenv()
        
        # Get configuration
        self.provider = self.config.get('provider') or os.getenv('LLM_PROVIDER', 'google')
        self.model = self.config.get('model') or os.getenv('LLM_MODEL', 'gemma-3-27b-it')
        self.temperature = float(self.config.get('temperature') or os.getenv('LLM_TEMPERATURE', '0.7'))
        
        # Get API keys - support both GEMINI_API_KEY and GOOGLE_API_KEY
        if self.provider == 'openai':
            self.api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
        else:  # google
            self.api_key = (
                self.config.get('api_key') or 
                os.getenv('GEMINI_API_KEY') or 
                os.getenv('GOOGLE_API_KEY')
            )
        
        # Initialize client
        self.client = None
        if self.api_key:
            self._init_client()
        else:
            print(f"Warning: No API key found for {self.provider}. Using fallback mode.")
    
    def _init_client(self):
        """Initialize the appropriate LLM client"""
        try:
            if self.provider == 'openai':
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                
            elif self.provider == 'google':
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
                
        except ImportError as e:
            print(f"Error: Required package not installed for {self.provider}")
            if self.provider == 'google':
                print(f"Install with: pip install google-genai")
            else:
                print(f"Install with: pip install openai")
            self.client = None
        except Exception as e:
            print(f"Error initializing {self.provider} client: {e}")
            self.client = None
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate text using the configured LLM
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Override default temperature
        
        Returns:
            Generated text
        """
        if not self.client:
            # Fallback mode
            return self._generate_fallback(prompt)
        
        temp = temperature if temperature is not None else self.temperature
        
        try:
            if self.provider == 'openai':
                return self._generate_openai(prompt, system_prompt, max_tokens, temp)
            elif self.provider == 'google':
                return self._generate_google(prompt, system_prompt, max_tokens, temp)
            else:
                return self._generate_fallback(prompt)
                
        except Exception as e:
            print(f"Error generating with {self.provider}: {e}")
            return self._generate_fallback(prompt)
    
    def _generate_openai(
        self, 
        prompt: str, 
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Generate using OpenAI API"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content.strip()
    
    def _generate_google(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Generate using Google Gemini API"""
        # Combine system and user prompts
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Configure generation
        config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        # Generate content using the new SDK
        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt,
            config=config
        )
        
        return response.text.strip()
    
    def _generate_fallback(self, prompt: str) -> str:
        """Fallback generation when no API available"""
        # Simple template-based responses
        if "code" in prompt.lower() and "source" in prompt.lower():
            return "const factorial = n => n === 0 ? 1 : n * factorial(n - 1);\nfactorial(5);"
        elif "question" in prompt.lower():
            return """Consider the following Source program:

```javascript
const factorial = n => n === 0 ? 1 : n * factorial(n - 1);
factorial(5);
```

What is the value of the final expression?

A) 120
B) 119
C) 121
D) 24"""
        else:
            return "// Fallback: No API key available"
    
    def is_available(self) -> bool:
        """Check if LLM client is available"""
        return self.client is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about current configuration"""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "available": self.is_available()
        }


if __name__ == "__main__":
    # Test the LLM client
    print("Testing LLM Client...\n")
    
    client = LLMClient()
    info = client.get_info()
    
    print(f"Provider: {info['provider']}")
    print(f"Model: {info['model']}")
    print(f"Temperature: {info['temperature']}")
    print(f"Available: {info['available']}")
    
    if info['available']:
        print("\nTesting generation...")
        response = client.generate(
            "Say 'Hello from the LLM client!' and nothing else.",
            max_tokens=50
        )
        print(f"Response: {response}")
    else:
        print("\nNo API key configured. Set up .env file or environment variables.")