import requests
import logging
import sys
from pathlib import Path
import json
import re
import os

def analyze_ollama_logs():
    """Analysiert die Ollama-Logs für Optimierungen"""
    ollama_dir = Path(os.getenv('LOCALAPPDATA')) / 'Ollama'
    log_paths = [
        ollama_dir / 'ollama.log',           # Direkt im Ollama-Verzeichnis
        ollama_dir / 'logs' / 'ollama.log',  # Im logs Unterverzeichnis
        ollama_dir / 'ollama' / 'logs' / 'ollama.log'  # Alternative Struktur
    ]
    
    log_file = None
    for path in log_paths:
        if path.exists():
            log_file = path
            break
            
    if not log_file:
        logging.error(f"Ollama log file not found in {ollama_dir}")
        return None
        
    try:
        logs = log_file.read_text(encoding='utf-8')
        logging.info(f"Found Ollama logs at: {log_file}")
        
        # Extrahiere wichtige Metriken
        metrics = {
            'gpu_usage': re.findall(r'memory.available="\[(\d+\.\d+) GiB\]"', logs),
            'memory_required': re.findall(r'memory.required.full="(\d+\.\d+) GiB"', logs),
            'layers_gpu': re.findall(r'layers.offload=(\d+)', logs),
            'batch_size': re.findall(r'--batch-size (\d+)', logs),
            'gpu_info': re.findall(r'Device \d+: (.*), compute capability', logs)
        }
        
        # Analysiere die letzten Werte
        if metrics['gpu_usage']:
            gpu_available = float(metrics['gpu_usage'][-1])
            logging.info(f"GPU Memory Available: {gpu_available} GiB")
            
        if metrics['memory_required']:
            mem_required = float(metrics['memory_required'][-1])
            logging.info(f"Memory Required: {mem_required} GiB")
            
        if metrics['layers_gpu']:
            gpu_layers = int(metrics['layers_gpu'][-1])
            logging.info(f"GPU Layers: {gpu_layers}")
            
        if metrics['batch_size']:
            batch = int(metrics['batch_size'][-1])
            logging.info(f"Batch Size: {batch}")
            
        if metrics['gpu_info']:
            logging.info(f"GPU: {metrics['gpu_info'][-1]}")
            
        # Optimiere Modelfile basierend auf Metriken
        modelfile = Path('Modelfile')
        if modelfile.exists():
            content = modelfile.read_text()
            
            # Passe Parameter basierend auf Logs an
            if gpu_available < mem_required:
                content = re.sub(r'num_ctx \d+', f'num_ctx {min(2048, int(gpu_available * 1024))}', content)
                
            if gpu_layers > 0:
                content = re.sub(r'num_gpu_layers \d+', f'num_gpu_layers {gpu_layers}', content)
                
            modelfile.write_text(content)
            logging.info("Updated Modelfile with optimized parameters")
            
        return metrics
        
    except Exception as e:
        logging.error(f"Error analyzing Ollama logs: {str(e)}")
        return None

def test_ollama_connection(model_name="dashboard-llama"):
    """Tests the connection to Ollama and checks if the model is available"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Analysiere Logs für Optimierungen
        metrics = analyze_ollama_logs()
        if metrics:
            logging.info("Successfully analyzed Ollama metrics")
        
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
            logging.error(f"Model {model_name} not found. Creating custom model...")
            try:
                with open('Modelfile', 'r', encoding='utf-8') as f:
                    modelfile = f.read()
                
                create_response = requests.post(
                    "http://localhost:11434/api/create",
                    json={
                        "name": model_name,
                        "modelfile": modelfile
                    }
                )
                
                if create_response.status_code != 200:
                    logging.error("Failed to create custom model")
                    return False
                    
                logging.info(f"Successfully created custom model: {model_name}")
                return True
                
            except Exception as e:
                logging.error(f"Error creating custom model: {str(e)}")
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