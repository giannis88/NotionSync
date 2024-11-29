# Contributing to Notion Sync

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

## Project Structure

```
notion/
├── config/          # Configuration files (.env, Modelfile)
├── docs/           # Documentation
├── frontend/       # Frontend TypeScript/React components
├── scripts/        # Batch scripts for automation
├── src/           # Python source code
├── tests/         # Test files
├── templates/      # Template files
├── data/          # Data files
└── logs/          # Log files
```

## Development Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and configure your environment variables

## Testing

Run tests with:
```bash
pytest
```

## Code Style

- Follow PEP 8 for Python code
- Use TypeScript for frontend components
- Include docstrings for all functions and classes
- Write meaningful commit messages

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

## Questions?

Feel free to open an issue for any questions or concerns.
