import os
from dotenv import load_dotenv
from google import genai

# 1. Load the .env file explicitly
load_dotenv()

# 2. Initialize the client
# The SDK usually looks for GOOGLE_API_KEY by default. 
# Since you named it GEMINI_API_KEY, we must pass it explicitly.
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# 3. Generate content
# FIXED: Removed the extra single quotes inside the double quotes.
response = client.models.generate_content(
    model="gemma-3-27b-it", 
    contents="Explain how AI works in a few words"
)

print(response.text)