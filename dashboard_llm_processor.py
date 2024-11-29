import os
import json
import logging
import requests
import time
import psutil
import GPUtil
import numpy as np
import yaml
import datetime
import traceback
import asyncio
import aiohttp
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Semaphore
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client
from typing import List, Dict, Optional

# Load environment variables with explicit path
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Configure GPU optimizations
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ['GGML_CUDA_NO_PINNED'] = '1'
os.environ['GGML_CUDA_FORCE_MMQ'] = '1'
os.environ['OLLAMA_HOST'] = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
os.environ['OLLAMA_FLASH_ATTENTION'] = 'true'
os.environ['GGML_USE_FLASH_ATTN'] = '1'
os.environ['GGML_ATTENTION_MASK'] = '1'
os.environ['GGML_MEM_EFFICIENT'] = '1'
os.environ['GGML_TENSOR_SPLIT'] = '1'

# Configure memory optimizations
os.environ['GGML_MAX_BATCH_SIZE'] = '512'
os.environ['GGML_MAX_TOKENS'] = '2048'
os.environ['GGML_ROPE_SCALING'] = 'linear'
os.environ['GGML_ROPE_FREQ_BASE'] = '10000.0'
os.environ['GGML_ROPE_FREQ_SCALE'] = '1.0'

class DashboardLLMProcessor:
    def __init__(self, notion_token: Optional[str] = None):
        """Initialize the dashboard processor."""
        self.notion_token = notion_token or os.getenv("NOTION_TOKEN")
        if not self.notion_token:
            raise ValueError("Notion token is required. Set NOTION_TOKEN environment variable or pass token to constructor.")
        
        self.notion = Client(auth=self.notion_token)
        # Set Health Hub page ID as default
        self.dashboard_page_id = os.getenv("NOTION_DASHBOARD_PAGE_ID", "14ce4a7d76a4814988b3d244ddfbc751")
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Ollama model configuration
        self.model_config = {
            'model': os.getenv('MODEL_NAME', 'notionsync-gpu'),
            'mirostat': 1,
            'mirostat_eta': 0.1,
            'mirostat_tau': 5.0,
            'num_ctx': 2048,
            'num_gpu': 32,
            'num_thread': 8,
            'repeat_last_n': 64,
            'repeat_penalty': 1.1,
            'temperature': 0.7,
            'tfs_z': 1.0,
            'top_k': 40,
            'top_p': 0.9,
            'flash_attn': True,
            'use_flash_attn_2': True,
            'attention_mask': True,
            'rope_freq_base': 10000.0,
            'rope_freq_scale': 1.0,
            'stop': ['</s>']
        }
        
        # Verify Ollama server is running
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code != 200:
                raise ConnectionError("Ollama server is not responding correctly")
            models = response.json().get("models", [])
            model_name = os.getenv("MODEL_NAME", "notionsync-gpu")
            if not any(model.get("name", "").startswith(model_name) for model in models):
                logging.warning(f"{model_name} model not found in Ollama. Please ensure the model is properly loaded.")
        except Exception as e:
            logging.error(f"Error connecting to Ollama server: {str(e)}")
            logging.error("Please ensure Ollama is running and the custom model is installed")
            raise

    def _load_stats(self):
        """Load performance statistics"""
        stats_file = Path("data/cache/llm_stats.json")
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    saved_stats = json.load(f)
                    self.perf_stats.update(saved_stats)
            except Exception as e:
                logging.error(f"Error loading stats: {e}")

    def _save_stats(self):
        """Save performance statistics"""
        stats_file = Path("data/cache/llm_stats.json")
        try:
            with open(stats_file, 'w') as f:
                json.dump(self.perf_stats, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving stats: {e}")

    def _configure_gpu(self):
        """Configure Ollama for GTX 1080 Ti"""
        try:
            # GTX 1080 Ti specific configuration
            config_data = {
                'options': {
                    'numa': False,
                    'num_gpu': 1,
                    'gpu_layers': 35,     # Optimal for 11GB VRAM
                    'f16_kv': True,       # FP16 for memory efficiency
                    'batch_size': 12,     # Balanced for 1080 Ti
                    'cuda_launch_blocking': 0,
                    'tensor_split': '0'    # Use only GPU
                }
            }
            
            response = requests.post(
                f'{self.ollama_host}/api/config',
                headers={'Content-Type': 'application/json'},
                json=config_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logging.info("GPU configuration successful - GTX 1080 Ti detected")
            else:
                logging.warning("Warning: GPU configuration may not be fully applied")
                
        except Exception as e:
            logging.error(f"GPU configuration warning: {e}")

    def _get_gpu_optimized_options(self):
        """Get options optimized for GTX 1080 Ti"""
        return {
            'temperature': 0.1,
            'top_p': 0.2,
            'num_predict': 1024,      # Reduced to prevent VRAM overflow
            'num_ctx': 2048,          # Balanced context size for 1080 Ti
            'repeat_penalty': 1.1,
            'mirostat': 2,
            'mirostat_tau': 5.0,
            'mirostat_eta': 0.1,
            'num_thread': 6,          # Balanced CPU threads for 1080 Ti
            'num_gpu': 1,
            'num_batch': 12,          # Optimized for 1080 Ti
            'f16_kv': True,
            'rope_frequency_base': 10000.0,
            'rope_frequency_scale': 1.0,
            'num_keep': 32,
            'gpu_layers': 35,         # Optimal layer split for 11GB VRAM
            'gpu_split': 0,
            'tensor_split': '0'       # Use GPU exclusively
        }

    def get_performance_metrics(self):
        """Get current performance metrics with GPU details"""
        total_requests = self.perf_stats['total_requests']
        cache_hit_rate = (self.perf_stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        avg_api_time = 0

        return {
            'cache_hit_rate': f"{cache_hit_rate:.2f}%",
            'total_requests': total_requests,
            'api_error_rate': f"{(self.perf_stats['error_count'] / max(1, total_requests) * 100):.2f}%",
            'avg_api_time': f"{avg_api_time:.2f}s",
            'gpu_enabled': True,
            'gpu_model': 'GTX 1080 Ti',
            'gpu_layers': 35,
            'batch_size': 12,
            'context_window': 2048
        }

    async def _make_api_request(self, prompt):
        """Make API request without rate limiting."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                ) as response:
                    if response.status != 200:
                        raise Exception(f"API error: {response.status}")
                        
                    result = await response.json()
                    self.perf_stats['total_requests'] += 1
                    return result['response']
                    
        except asyncio.TimeoutError:
            raise Exception("request timeout")

    def _call_ollama(self, prompt, system_prompt=None):
        """Make a call to Ollama API with GPU optimization"""
        return asyncio.run(self._process_with_retry(prompt))

    async def _process_with_retry(self, prompt, max_retries=5):
        """Process prompt with simple retry logic."""
        retries = 0
        last_error = None
        
        while retries < max_retries:
            try:
                response = await self._make_api_request(prompt)
                return response
                
            except Exception as e:
                logging.warning(f"API error encountered. Retrying. Error: {e}")
                retries += 1
                last_error = e
                if retries < max_retries:
                    await asyncio.sleep(1)  # Brief pause between retries
                continue
            
        raise Exception(f"Max retries exceeded. Last error: {last_error}")

    def _get_cache_key(self, prompt, system_prompt):
        """Generate a cache key from prompt and system prompt."""
        return f"{prompt}::{system_prompt or ''}"
        
    def _call_ollama_gpu(self, prompt, system_prompt=None, stream=False):
        """Optimized GPU inference with Flash Attention-style memory management."""
        url = f"{self.ollama_host}/api/generate"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt if system_prompt else "",
            "stream": stream,
            "options": {
                **self.ollama_config,
                "num_predict": 2048,  # Limit response length
                "temperature": 0.7,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        
        max_retries = 3
        timeout = 90  # Reduced timeout to fail faster
        backoff_factor = 2
        
        for attempt in range(max_retries):
            try:
                logging.info(f"\nProcessing with GPU:")
                logging.info(f"- Prompt length: {len(prompt)} chars")
                logging.info(f"- System prompt: {'Yes' if system_prompt else 'No'}")
                logging.info(f"- Sending request to Ollama (attempt {attempt + 1}/{max_retries})...")
                
                start_time = time.time()
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self._track_performance(start_time, time.time())
                    logging.info(f"- Success! Generated {len(result['response'])} chars")
                    return result['response']
                else:
                    error_msg = f"Error: {response.status_code} - {response.text}"
                    logging.error(error_msg)
                    if attempt == max_retries - 1:
                        raise Exception(error_msg)
                    time.sleep(backoff_factor ** attempt)
                    
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise Exception(f"Request timed out after {max_retries} attempts")
                time.sleep(backoff_factor ** attempt)
            except Exception as e:
                error_msg = f"Error in GPU processing: {e}"
                logging.error(error_msg)
                if attempt == max_retries - 1:
                    raise Exception(error_msg)
                time.sleep(backoff_factor ** attempt)

    def _track_performance(self, start_time, end_time):
        """Track performance metrics."""
        duration = end_time - start_time
        self.perf_stats['total_requests'] += 1
        self.perf_stats['avg_response_time'] = duration
        # Track memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        current_memory = memory_info.rss / 1024 / 1024  # Convert to MB
        self.perf_stats['peak_memory'] = max(self.perf_stats['peak_memory'], current_memory)
        
        logging.info(f"\nPerformance Metrics:")
        logging.info(f"- Response Time: {duration:.2f}s")
        logging.info(f"- Avg Response Time: {self.perf_stats['avg_response_time']:.2f}s")
        logging.info(f"- Memory Usage: {current_memory:.1f}MB")
        logging.info(f"- Peak Memory: {self.perf_stats['peak_memory']:.1f}MB")

    def process_notion_database(self, database_id):
        """Process all pages in a Notion database."""
        try:
            pages = self.get_database_pages(database_id)
            enhanced_pages = []
            
            for page in pages:
                try:
                    enhanced_page = self.process_page(page)
                    enhanced_pages.append(enhanced_page)
                except Exception as e:
                    page_id = page.get("id", "Unknown")
                    logging.error(f"Error processing page {page_id}: {e}")
                    self.perf_stats['error_count'] += 1
                    continue
            
            return enhanced_pages
        except Exception as e:
            logging.error(f"Error accessing database {database_id}: {e}")
            raise

    def get_database_pages(self, database_id):
        """Retrieve all pages from a Notion database."""
        pages = []
        query = self.notion.databases.query(database_id=database_id)
        
        for result in query["results"]:
            pages.append(result)
            
        return pages

    def prepare_prompt(self, content):
        """Prepare content for LLM processing."""
        # Limit content to avoid context window issues
        max_chars_per_block = 800  # Conservative limit
        formatted_content = []
        current_length = 0
        
        for block in content:
            block_text = f"{block['type']}: {block['text']}"
            if current_length + len(block_text) > max_chars_per_block:
                break
            formatted_content.append(block_text)
            current_length += len(block_text)
        
        return "\n".join(formatted_content)

    def process_page(self, page):
        """Process a single Notion page with the local LLM."""
        page_id = page["id"]
        page_content = self.get_page_content(page_id)
        
        # Process content in chunks to avoid context window limits
        chunks = self._split_content_into_chunks(page_content)
        enhanced_chunks = []
        
        for chunk in chunks:
            # Prepare system prompt
            system_prompt = """You are an AI assistant helping to enhance Notion pages. Focus on:
            1. Improving clarity and readability
            2. Fixing grammatical errors
            3. Maintaining original meaning
            Keep the response concise and well-structured."""
            
            # Process with LLM
            try:
                enhanced_chunk = self._call_ollama_gpu(
                    prompt=chunk,
                    system_prompt=system_prompt
                )
                enhanced_chunks.append(enhanced_chunk)
                
                # Add small delay between chunks to prevent GPU overload
                time.sleep(1)
            except Exception as e:
                logging.error(f"Error processing chunk: {e}")
                enhanced_chunks.append(chunk)  # Keep original if processing fails
        
        # Combine enhanced chunks
        enhanced_content = "\n".join(enhanced_chunks)
        
        # Update the page
        self.update_page_content(page_id, enhanced_content)
        
        return {
            "id": page_id,
            "title": self.get_page_title(page),
            "status": "enhanced",
            "original_length": len(str(page_content)),
            "enhanced_length": len(enhanced_content)
        }

    def _split_content_into_chunks(self, content, max_chunk_size=1500):
        """Split content into manageable chunks."""
        if len(content) <= max_chunk_size:
            return [content]

        chunks = []
        current_chunk = []
        current_size = 0
        
        for line in content.split('\n'):
            line_length = len(line)
            if current_size + line_length > max_chunk_size:
                if current_chunk:  # Only append if there's content
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_length
            else:
                current_chunk.append(line)
                current_size += line_length
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def get_page_content(self, page_id):
        """Retrieve the content of a Notion page."""
        try:
            response = self.notion.blocks.children.list(block_id=page_id)
            if response and "results" in response:
                return self._blocks_to_text(response["results"])
            return ""
        except Exception as e:
            logging.error(f"Error retrieving page content: {str(e)}")
            return ""

    def _blocks_to_text(self, blocks: List[Dict]) -> str:
        """Convert Notion blocks to plain text."""
        if not blocks or not isinstance(blocks, list):
            return ""
        
        text_content = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            
            block_type = block.get("type")
            if not block_type:
                continue
            
            content = ""
            
            if block_type == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                if rich_text and isinstance(rich_text, list):
                    content = " ".join(
                        text.get("plain_text", "")
                        for text in rich_text
                        if isinstance(text, dict)
                    )
                
            elif block_type == "bulleted_list_item":
                rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
                if rich_text and isinstance(rich_text, list):
                    content = "• " + " ".join(
                        text.get("plain_text", "")
                        for text in rich_text
                        if isinstance(text, dict)
                    )
                
            elif block_type == "numbered_list_item":
                rich_text = block.get("numbered_list_item", {}).get("rich_text", [])
                if rich_text and isinstance(rich_text, list):
                    content = "1. " + " ".join(
                        text.get("plain_text", "")
                        for text in rich_text
                        if isinstance(text, dict)
                    )
                
            elif block_type == "heading_1":
                rich_text = block.get("heading_1", {}).get("rich_text", [])
                if rich_text and isinstance(rich_text, list):
                    content = "# " + " ".join(
                        text.get("plain_text", "")
                        for text in rich_text
                        if isinstance(text, dict)
                    )
                
            elif block_type == "heading_2":
                rich_text = block.get("heading_2", {}).get("rich_text", [])
                if rich_text and isinstance(rich_text, list):
                    content = "## " + " ".join(
                        text.get("plain_text", "")
                        for text in rich_text
                        if isinstance(text, dict)
                    )
                
            elif block_type == "heading_3":
                rich_text = block.get("heading_3", {}).get("rich_text", [])
                if rich_text and isinstance(rich_text, list):
                    content = "### " + " ".join(
                        text.get("plain_text", "")
                        for text in rich_text
                        if isinstance(text, dict)
                    )
                
            if content:
                text_content.append(content)
            
        return "\n\n".join(text_content)

    def update_page_content(self, page_id: str, content: str) -> None:
        """Update the content of a Notion page."""
        # Clear existing content
        logging.info("Clearing existing content...")
        existing_blocks = self.notion.blocks.children.list(page_id)
        for block in existing_blocks.get("results", []):
            self.notion.blocks.delete(block["id"])
        
        blocks = self._convert_to_notion_blocks(content)
        
        # Process blocks in batches of 100 (Notion API limit)
        batch_size = 100
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            logging.info(f"Updating blocks {i+1} to {min(i+batch_size, len(blocks))} of {len(blocks)}")
            try:
                self.notion.blocks.children.append(page_id, children=batch)
            except Exception as e:
                logging.error(f"Error updating batch {i//batch_size + 1}: {str(e)}")
                raise

    def parse_enhanced_content(self, content):
        """Parse enhanced content into Notion blocks."""
        blocks = []
        for line in content.split("\n"):
            if line.strip():
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": line}
                        }]
                    }
                })
        return blocks

    def get_page_title(self, page):
        """Extract the title of a Notion page."""
        if "properties" in page and "title" in page["properties"]:
            title_content = page["properties"]["title"]
            if "title" in title_content and title_content["title"]:
                return title_content["title"][0]["plain_text"]
        return "Untitled"

    def get_linked_databases(self, page_id):
        """Get linked databases in a page."""
        try:
            blocks = self.notion.blocks.children.list(block_id=page_id)
            linked_dbs = []
            
            for block in blocks.get("results", []):
                if block["type"] == "child_database":
                    try:
                        # Query the database
                        db_pages = self.notion.databases.query(**{
                            "database_id": block["id"],
                            "page_size": 100  # Get up to 100 pages
                        })
                        
                        # Get database title
                        db_info = self.notion.databases.retrieve(database_id=block["id"])
                        db_title = db_info["title"][0]["plain_text"] if db_info.get("title") else "Untitled Database"
                        
                        linked_dbs.append({
                            "id": block["id"],
                            "title": db_title,
                            "pages": db_pages.get("results", [])
                        })
                        
                        logging.info(f"Found database: {db_title} with {len(db_pages.get('results', []))} pages")
                        
                    except Exception as e:
                        logging.error(f"Error querying database {block['id']}: {str(e)}")
                        continue
            
            return linked_dbs
            
        except Exception as e:
            logging.error(f"Error getting linked databases: {str(e)}")
            return []

    def get_subpages(self, page_id):
        """Get subpages of a page."""
        blocks = self.notion.blocks.children.list(block_id=page_id)
        subpages = []
        
        for block in blocks["results"]:
            if block["type"] == "child_page":
                subpages.append({
                    "id": block["id"],
                    "title": block.get("child_page", {}).get("title", "Untitled Page")
                })
        
        return subpages

    def enhance_and_update_pages(self, pages):
        """Enhance and update multiple pages with LLM processing."""
        enhanced_pages = []
        
        logging.info(f"\nProcessed {len(pages)} pages. Now enhancing with LLM...")
        
        for page in pages:
            try:
                # Get current page content
                page_content = self.get_page_content(page["id"])
                
                # Prepare system prompt for consistent enhancement
                system_prompt = """You are an AI assistant helping to enhance Notion pages. Your task is to:
                1. Improve clarity and readability
                2. Fix any grammatical or spelling errors
                3. Add relevant details where appropriate
                4. Maintain the original meaning and structure
                5. Keep a professional and consistent tone
                Please provide the enhanced content in a clean format."""
                
                # Process with LLM
                enhanced_content = self._call_ollama_gpu(
                    prompt=self.prepare_prompt(page_content),
                    system_prompt=system_prompt
                )
                
                # Update the page
                self.update_page_content(page["id"], enhanced_content)
                
                # Add to enhanced pages list
                enhanced_pages.append({
                    "id": page["id"],
                    "title": page["title"],
                    "status": "enhanced",
                    "original_length": len(str(page_content)),
                    "enhanced_length": len(enhanced_content)
                })
                
                logging.info(f"Enhanced page: {page['title']}")
                logging.info(f"- Original length: {len(str(page_content))} chars")
                logging.info(f"- Enhanced length: {len(enhanced_content)} chars")
                
            except Exception as e:
                logging.error(f"Error enhancing page {page.get('title', 'Unknown')}: {e}")
                self.perf_stats['error_count'] += 1
                continue
        
        return enhanced_pages

    def update_notion_page_in_batches(self, page_id: str, blocks: List[Dict], batch_size: int = 80) -> None:
        """Update a Notion page in batches to avoid the 100 block limit."""
        # First, clear existing content
        try:
            existing_blocks = self.notion.blocks.children.list(block_id=page_id).get("results", [])
            for block in existing_blocks:
                self.notion.blocks.delete(block_id=block["id"])
                time.sleep(0.1)  # Rate limiting
        except Exception as e:
            logging.error(f"Error clearing existing blocks: {str(e)}")
            return

        # Then add new content in batches
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            try:
                self.notion.blocks.children.append(
                    block_id=page_id,
                    children=batch
                )
                time.sleep(0.5)  # Rate limiting
                logging.info(f"Successfully updated batch {i//batch_size + 1}/{len(blocks)//batch_size + 1}")
            except Exception as e:
                logging.error(f"Error updating batch {i//batch_size + 1}: {str(e)}")
                continue

    def _split_content_into_chunks(self, content: str, max_chars: int = 1000) -> List[str]:
        """Split content into smaller chunks for processing."""
        if len(content) <= max_chars:
            return [content]

        chunks = []
        current_chunk = []
        current_length = 0

        for line in content.split('\n'):
            line_length = len(line)
            if current_length + line_length > max_chars:
                if current_chunk:  # Only append if there's content
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def enhance_notion_page(self, page_id: str) -> None:
        """Enhance a Notion page with LLM processing."""
        try:
            blocks = self.get_page_content(page_id)
            if not blocks:
                return

            # Convert blocks to text for processing
            content = self._blocks_to_text(blocks)
            if not content:
                logging.warning(f"No text content found in page {page_id}")
                return

            chunks = self._split_content_into_chunks(content)
            enhanced_blocks = []
            
            for chunk in chunks:
                try:
                    result = self.process_chunk_with_retry(chunk)
                    if result:
                        enhanced_blocks.extend(self._convert_to_notion_blocks(result))
                    else:
                        # Keep original content if processing fails
                        enhanced_blocks.extend(self._convert_to_notion_blocks(chunk))
                except Exception as e:
                    logging.error(f"Error processing chunk: {str(e)}")
                    # Keep original content on error
                    enhanced_blocks.extend(self._convert_to_notion_blocks(chunk))
                
                # Small delay between chunks
                time.sleep(1)
            
            if enhanced_blocks:
                self.update_notion_page_in_batches(page_id, enhanced_blocks)
                
        except Exception as e:
            logging.error(f"Error processing page {page_id}: {str(e)}")

    def _convert_to_notion_blocks(self, text: str) -> List[Dict]:
        """Convert enhanced text back to Notion blocks."""
        if not text or not isinstance(text, str):
            return []
        
        blocks = []
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # Handle headings
            if paragraph.startswith('# '):
                blocks.append({
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": paragraph[2:].strip()}
                        }],
                        "color": "default",
                        "is_toggleable": False
                    }
                })
            elif paragraph.startswith('## '):
                blocks.append({
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": paragraph[3:].strip()}
                        }],
                        "color": "default",
                        "is_toggleable": False
                    }
                })
            elif paragraph.startswith('### '):
                blocks.append({
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": paragraph[4:].strip()}
                        }],
                        "color": "default",
                        "is_toggleable": False
                    }
                })
            # Handle bulleted lists
            elif paragraph.startswith('• '):
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": paragraph[2:].strip()}
                        }],
                        "color": "default"
                    }
                })
            # Handle numbered lists
            elif paragraph.lstrip()[0].isdigit() and paragraph.lstrip()[1:].startswith('. '):
                content = paragraph.lstrip()[paragraph.lstrip().find(' ')+1:].strip()
                blocks.append({
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": content}
                        }],
                        "color": "default"
                    }
                })
            # Handle quotes
            elif paragraph.startswith('> '):
                blocks.append({
                    "type": "quote",
                    "quote": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": paragraph[2:].strip()}
                        }],
                        "color": "default"
                    }
                })
            # Handle code blocks
            elif paragraph.startswith('```') and paragraph.endswith('```'):
                code_content = paragraph[3:-3].strip()
                language = "plain text"
                if '\n' in code_content:
                    first_line = code_content.split('\n')[0].strip()
                    if first_line in ["python", "javascript", "typescript", "java", "cpp", "c", "rust", "go"]:
                        language = first_line
                        code_content = '\n'.join(code_content.split('\n')[1:])
                blocks.append({
                    "type": "code",
                    "code": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": code_content}
                        }],
                        "language": language,
                        "caption": []
                    }
                })
            # Handle callouts
            elif paragraph.startswith('📝 ') or paragraph.startswith('💡 ') or paragraph.startswith('⚠️ '):
                emoji = paragraph[0:2]
                content = paragraph[2:].strip()
                blocks.append({
                    "type": "callout",
                    "callout": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": content}
                        }],
                        "icon": {"emoji": emoji.strip()},
                        "color": "default"
                    }
                })
            # Handle to-do items
            elif paragraph.startswith('[ ] ') or paragraph.startswith('[x] '):
                checked = paragraph.startswith('[x] ')
                content = paragraph[4:].strip()
                blocks.append({
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": content}
                        }],
                        "checked": checked,
                        "color": "default"
                    }
                })
            # Default to paragraph
            else:
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": paragraph.strip()}
                        }],
                        "color": "default"
                    }
                })
            
        return blocks

    def _blocks_to_text(self, blocks: List[Dict]) -> str:
        """Convert Notion blocks to plain text with formatting markers."""
        if not blocks or not isinstance(blocks, list):
            return ""
        
        text_content = []
        
        for block in blocks:
            if not isinstance(block, dict):
                continue
            
            block_type = block.get("type")
            if not block_type:
                continue
            
            content = ""
            
            # Extract rich text content helper
            def get_rich_text_content(rich_text_array):
                if not rich_text_array or not isinstance(rich_text_array, list):
                    return ""
                return " ".join(
                    text.get("plain_text", "")
                    for text in rich_text_array
                    if isinstance(text, dict)
                )
            
            # Handle different block types
            if block_type == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                content = get_rich_text_content(rich_text)
            
            elif block_type == "heading_1":
                rich_text = block.get("heading_1", {}).get("rich_text", [])
                content = "# " + get_rich_text_content(rich_text)
            
            elif block_type == "heading_2":
                rich_text = block.get("heading_2", {}).get("rich_text", [])
                content = "## " + get_rich_text_content(rich_text)
            
            elif block_type == "heading_3":
                rich_text = block.get("heading_3", {}).get("rich_text", [])
                content = "### " + get_rich_text_content(rich_text)
            
            elif block_type == "bulleted_list_item":
                rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
                content = "• " + get_rich_text_content(rich_text)
            
            elif block_type == "numbered_list_item":
                rich_text = block.get("numbered_list_item", {}).get("rich_text", [])
                content = "1. " + get_rich_text_content(rich_text)
            
            elif block_type == "quote":
                rich_text = block.get("quote", {}).get("rich_text", [])
                content = "> " + get_rich_text_content(rich_text)
            
            elif block_type == "code":
                rich_text = block.get("code", {}).get("rich_text", [])
                language = block.get("code", {}).get("language", "plain text")
                code_content = get_rich_text_content(rich_text)
                content = f"```{language}\n{code_content}\n```"
            
            elif block_type == "callout":
                rich_text = block.get("callout", {}).get("rich_text", [])
                icon = block.get("callout", {}).get("icon", {})
                emoji = icon.get("emoji", "💡") if icon else "💡"
                content = f"{emoji} {get_rich_text_content(rich_text)}"
            
            elif block_type == "to_do":
                rich_text = block.get("to_do", {}).get("rich_text", [])
                checked = block.get("to_do", {}).get("checked", False)
                mark = "x" if checked else " "
                content = f"[{mark}] {get_rich_text_content(rich_text)}"
            
            elif block_type == "child_page":
                title = block.get("child_page", {}).get("title", "")
                content = f"📄 {title}"
            
            elif block_type == "child_database":
                title = block.get("child_database", {}).get("title", "")
                content = f"📊 {title}"
            
            if content:
                text_content.append(content)
            
        return "\n\n".join(text_content)

    def process_chunk_with_retry(self, chunk: str, max_retries: int = 5) -> Optional[str]:
        """Process a chunk of content with retry logic."""
        logging.info("\nProcessing with GPU:")
        logging.info(f"- Input length: {len(chunk)} chars")
        
        model_params = {
            'model': os.getenv('MODEL_NAME', 'notionsync-gpu'),
            'prompt': f"""
            Enhance and structure the following health dashboard content. 
            Maintain the original meaning while improving clarity and organization:

            {chunk}
            """,
            'stream': False,
            'options': {
                'num_ctx': 2048,
                'num_predict': -2,
                'temperature': 0.7,
                'top_k': 40,
                'top_p': 0.9,
                'repeat_last_n': 64,
                'repeat_penalty': 1.1,
                'seed': 42,
                'mirostat': 1,
                'mirostat_eta': 0.1,
                'mirostat_tau': 5.0,
                'num_gpu': 32,
                'num_thread': 8
            }
        }
        
        for attempt in range(max_retries):
            try:
                logging.info(f"- Sending request to Ollama (attempt {attempt + 1}/{max_retries})...")
                start_time = time.time()
                
                response = requests.post(
                    f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/generate",
                    json=model_params,
                    timeout=90  # Increased from 60 to handle larger chunks
                )
                
                if response.status_code == 200:
                    result = response.json()
                    enhanced_text = result.get('response', '')
                    
                    duration = time.time() - start_time
                    self._log_performance_metrics(duration, len(enhanced_text))
                    
                    return enhanced_text
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = min(30, 2 ** attempt)  # Cap exponential backoff at 30 seconds
                    logging.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"All attempts failed: {str(e)}")
                    raise
        
        return None

    def _log_performance_metrics(self, duration: float, response_length: int) -> None:
        """Log performance metrics."""
        logging.info(f"Processing completed in {duration:.2f}s")
        logging.info(f"Response length: {response_length} chars")
        logging.info(f"Processing speed: {response_length/duration:.2f} chars/s")

    def process_dashboard(self) -> None:
        """Process and enhance the entire health dashboard."""
        try:
            logging.info("Starting dashboard processing...")
            
            # Process main dashboard page
            self._process_single_page(self.dashboard_page_id)
            
            # Process linked databases
            linked_dbs = self.get_linked_databases(self.dashboard_page_id)
            for db in linked_dbs:
                logging.info(f"\nProcessing linked database: {db['title']}")
                try:
                    # Process each page in the database
                    for page in db['pages']:
                        logging.info(f"Processing database page: {self.get_page_title(page)}")
                        self._process_single_page(page['id'])
                except Exception as e:
                    logging.error(f"Error processing database {db['title']}: {str(e)}")
                    continue
            
            # Process subpages
            subpages = self.get_subpages(self.dashboard_page_id)
            for subpage in subpages:
                logging.info(f"\nProcessing subpage: {subpage['title']}")
                try:
                    self._process_single_page(subpage['id'])
                except Exception as e:
                    logging.error(f"Error processing subpage {subpage['title']}: {str(e)}")
                    continue
            
            logging.info("Dashboard processing completed successfully!")
            
        except Exception as e:
            logging.error(f"Error processing dashboard: {str(e)}")
            raise

    def _process_single_page(self, page_id: str) -> None:
        """Process and enhance a single page."""
        try:
            # Get page content
            page_content = self.get_page_content(page_id)
            if not page_content:
                logging.warning(f"No content found in page {page_id}")
                return
                
            logging.info(f"Retrieved {len(page_content)} chars of content")
            
            # Process content in chunks
            chunk_size = 800  # Reduced from 1000 to prevent timeouts
            chunks = [page_content[i:i+chunk_size] for i in range(0, len(page_content), chunk_size)]
            
            enhanced_chunks = []
            for i, chunk in enumerate(chunks, 1):
                logging.info(f"\nProcessing chunk {i}/{len(chunks)}")
                try:
                    enhanced = self.process_chunk_with_retry(chunk)
                    if enhanced:
                        enhanced_chunks.append(enhanced)
                    else:
                        enhanced_chunks.append(chunk)
                except Exception as e:
                    logging.error(f"Error processing chunk {i}: {str(e)}")
                    enhanced_chunks.append(chunk)
                    
            # Combine enhanced content
            enhanced_content = "\n\n".join(enhanced_chunks)
            
            # Update page
            logging.info("\nUpdating page content...")
            self.update_page_content(page_id, enhanced_content)
            
        except Exception as e:
            logging.error(f"Error processing page {page_id}: {str(e)}")
            raise

if __name__ == "__main__":
    # Initialize and run processor
    processor = DashboardLLMProcessor()
    processor.process_dashboard()
