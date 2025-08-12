import os
import redis
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the Redis URL from the environment
redis_url = os.getenv("REDIS_URL")

if not redis_url:
    print("Error: REDIS_URL not found in .env file.")
else:
    print(f"Attempting to connect to Redis at: {redis_url}")
    try:
        # Create a Redis client from the URL
        r = redis.from_url(redis_url)

        # Ping the Redis server to check the connection
        if r.ping():
            print("\nSuccessfully connected to Redis! The URL is correct.")
        else:
            print("\nConnected to Redis, but ping failed. Check server status.")
    except redis.exceptions.ConnectionError as e:
        print(f"\nFailed to connect to Redis. Please check your REDIS_URL and ensure Redis is running.")
        print(f"Error details: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
