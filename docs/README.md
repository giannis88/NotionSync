# NotionSync - AI-Powered Notion Dashboard Synchronization

A robust Python-based tool for synchronizing and optimizing Notion dashboards using LLM processing.

## Features

- Automated Notion page synchronization
- LLM-powered content optimization using Ollama
- Template watcher service for real-time synchronization
- Automated backup system for templates
- Support for medical data preservation
- Multilingual support (German/English)
- Robust error handling and retry mechanisms
- Secure API token management

## Prerequisites

- Python 3.8+
- Notion API access
- Ollama (for LLM processing)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/giannis88/NotionSync.git
cd NotionSync
```

2. Create and activate a virtual environment:
```bash
python -m venv notion_sync_env
source notion_sync_env/bin/activate  # On Windows: notion_sync_env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your Notion API key and database ID
   - Configure other optional settings

## Usage

1. Install and start the template watcher service (Windows):
```bash
# Run as administrator
install_service.bat
```

2. Basic synchronization:
```bash
python auto_notion_sync.py
```

3. Using the batch file (Windows):
```bash
run_notion_sync.bat
```

4. With dashboard analysis:
```bash
run_dashboard_analysis.bat
```

5. Managing the template watcher service:
```bash
python install_template_service.py start   # Start the service
python install_template_service.py stop    # Stop the service
python install_template_service.py restart # Restart the service
python install_template_service.py remove  # Uninstall the service
```

## Configuration

The tool can be configured through environment variables in your `.env` file:

- `NOTION_API_KEY`: Your Notion API key
- `NOTION_DATABASE_ID`: Target database ID
- `OLLAMA_HOST`: Ollama API endpoint (default: http://localhost:11434)
- `MODEL_NAME`: LLM model to use (default: llama2)
- `LOG_LEVEL`: Logging verbosity (default: INFO)

## Project Structure

- `auto_notion_sync.py`: Main synchronization script
- `template_watcher.py`: Real-time template synchronization service
- `template_sync.py`: Template to Notion conversion logic
- `install_template_service.py`: Windows service installation script
- `claude_formatter.py`: Content formatting utilities
- `dashboard-processor.tsx`: Dashboard processing component
- `run_notion_sync.bat`: Windows batch file for easy execution
- `run_dashboard_analysis.bat`: Batch file for dashboard analysis

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Security

- Never commit your `.env` file
- Keep your Notion API key private
- Exported data is automatically excluded from git
