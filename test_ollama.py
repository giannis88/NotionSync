import requests
import logging
import sys

def test_ollama_connection(model_name="qwen2.5-coder-extra-ctx:7b"):
    """Tests the connection to Ollama and checks if the model is available"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Test basic connection
        response = requests.get("http://localhost:11434/api/version")
        if response.status_code != 200:
            logging.error("Failed to connect to Ollama server")
            return False
            
        logging.info("Successfully connected to Ollama server")
        
        # Check if model is available
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": "Test prompt",
                "stream": False
            }
        )
        
        if response.status_code == 404:
            logging.error(f"Model {model_name} not found. Please install it first.")
            logging.info(f"Run: ollama pull {model_name}")
            return False
        elif response.status_code != 200:
            logging.error(f"Error testing model: {response.status_code}")
            return False
            
        logging.info(f"Successfully tested model {model_name}")
        return True
        
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to Ollama server. Is it running?")
        return False
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    if not test_ollama_connection():
        sys.exit(1) 