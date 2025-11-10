import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app

# Vercel expects the Flask app to be available as 'app'
# The main.py file should export the Flask app instance
if __name__ == "__main__":
    app.run()
