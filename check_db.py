import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from database_models import Interview, Result

def query_database():
    """Initializes the app and queries the database within the app context."""
    app = create_app()
    with app.app_context():
        print("--- Querying Database ---")
        
        # Fetch all interviews
        interviews = Interview.query.all()
        
        if not interviews:
            print("No interviews found in the database.")
        else:
            print(f"Found {len(interviews)} interview(s).\n")
            
            # Loop through each interview and print its details
            for interview in interviews:
                print(f"Interview ID: {interview.id}")
                print(f"  Candidate: {interview.candidate_name} ({interview.candidate_email})")
                print(f"  Topic: {interview.topic}")
                print(f"  Average Score: {interview.average_score:.2f}")
                print(f"  Timestamp: {interview.timestamp}")
                print("  Results:")
                
                # Print the results for each interview
                for result in interview.results:
                    print(f"    - Q: {result.question[:60]}...")
                    print(f"      A: {result.answer[:60]}...")
                    print(f"      Score: {result.score:.2f}")
                print("-------------------------")

if __name__ == "__main__":
    query_database()
