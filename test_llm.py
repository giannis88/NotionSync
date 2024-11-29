import os
import logging
import time
import GPUtil
import asyncio
import sys
import codecs

# Force CUDA/GPU settings
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ['GGML_CUDA_NO_PINNED'] = '1'
os.environ['GGML_CUDA_FORCE_MMQ'] = '1'
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'

# Set console to UTF-8 mode
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

from dashboard_llm_processor import DashboardLLMProcessor

def monitor_gpu():
    gpus = GPUtil.getGPUs()
    if gpus:
        gpu = gpus[0]
        return f"GPU Load: {gpu.load*100:.1f}%, Memory Use: {gpu.memoryUsed}MB/{gpu.memoryTotal}MB"
    return "No GPU found"

async def test_llm():
    processor = DashboardLLMProcessor()
    
    try:
        # Test 1: Initial queries
        prompts = [
            ("Simple math", "What is 2+2?", "Be concise."),
            ("Short answer", "Name one color.", "Answer in one word."),
        ]
        
        print("\nTest 1: Initial Queries")
        print("-" * 50)
        
        for test_name, prompt, system_prompt in prompts:
            print(f"\nQuery: {test_name}")
            print(f"Prompt: {prompt}")
            print("GPU Status:", monitor_gpu())
            
            start = time.time()
            response = processor._call_ollama_gpu(
                prompt,
                system_prompt=system_prompt
            )
            duration = time.time() - start
            
            print(f"Response: {response}")
            print(f"Time: {duration:.2f}s")
            print("GPU Status:", monitor_gpu())
            print()
        
        # Test 2: Cache hits
        print("\nTest 2: Cache Hits")
        print("-" * 50)
        
        for test_name, prompt, system_prompt in prompts:
            print(f"\nQuery: {test_name} (Cached)")
            print(f"Prompt: {prompt}")
            
            start = time.time()
            response = processor._call_ollama_gpu(
                prompt,
                system_prompt=system_prompt
            )
            duration = time.time() - start
            
            print(f"Response: {response}")
            print(f"Time: {duration:.2f}s")
            print()
        
        # Print final statistics
        print("\nFinal Statistics:")
        print(f"Total Requests: {processor.perf_stats['total_requests']}")
        print(f"Cache Hits: {processor.perf_stats['cache_hits']}")
        print(f"Average Response Time: {processor.perf_stats['avg_response_time']:.2f}s")
        print(f"Peak Memory Usage: {processor.perf_stats['peak_memory']:.1f}MB")
        print(f"Errors: {processor.perf_stats['error_count']}")
        print(f"Final GPU Status: {monitor_gpu()}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(test_llm())
