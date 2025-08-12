import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key
api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("Error: GEMINI_API_KEY not found in .env file or environment variables.")
else:
    try:
        print("Configuring Gemini...")
        # Configure the generative AI client
        genai.configure(api_key=api_key)

        print("Creating model...")
        # Create a model instance
        model = genai.GenerativeModel('gemini-2.5-flash')

        print("Sending test prompt...")
        # Send a test prompt
        response = model.generate_content("Tell me a short, one-sentence joke.")

        print("\n--- SUCCESS ---")
        print("Response from Gemini:", response.text)
        print("Your API key is working correctly!")

    except Exception as e:
        print("\n--- ERROR ---")
        print("An error occurred while testing the API key:")
        print(e)
