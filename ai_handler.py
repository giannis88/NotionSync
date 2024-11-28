import os
import logging
import aiohttp
import asyncio
from datetime import datetime
import json
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class AIHandler:
    def __init__(self):
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model_name = os.getenv('MODEL_NAME', 'llama2')
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def get_session(self) -> aiohttp.ClientSession:
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def analyze_health_content(self, content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze health-related content using AI"""
        try:
            prompt = self._build_health_prompt(content)
            response = await self._get_ai_response(prompt)
            return self._parse_health_insights(response)
        except Exception as e:
            logger.error(f"Error analyzing health content: {str(e)}")
            return {}
            
    async def analyze_business_content(self, content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze business-related content using AI"""
        try:
            prompt = self._build_business_prompt(content)
            response = await self._get_ai_response(prompt)
            return self._parse_business_insights(response)
        except Exception as e:
            logger.error(f"Error analyzing business content: {str(e)}")
            return {}
            
    def _build_health_prompt(self, content: List[Dict[str, Any]]) -> str:
        """Build prompt for health content analysis"""
        prompt = "Analyze the following health-related content and provide insights:\n\n"
        for item in content:
            if isinstance(item, dict):
                prompt += json.dumps(item, indent=2) + "\n"
            else:
                prompt += str(item) + "\n"
        return prompt
        
    def _build_business_prompt(self, content: List[Dict[str, Any]]) -> str:
        """Build prompt for business content analysis"""
        prompt = "Analyze the following business-related content and provide insights:\n\n"
        for item in content:
            if isinstance(item, dict):
                prompt += json.dumps(item, indent=2) + "\n"
            else:
                prompt += str(item) + "\n"
        return prompt
        
    async def _get_ai_response(self, prompt: str) -> str:
        """Get AI response using Ollama API"""
        try:
            session = await self.get_session()
            
            data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            
            async with session.post(f"{self.ollama_host}/api/generate", json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('response', '')
                else:
                    error_text = await response.text()
                    logger.error(f"Ollama API error: {response.status} - {error_text}")
                    return ''
                    
        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            return ''
            
    def _parse_health_insights(self, response: str) -> Dict[str, Any]:
        """Parse AI response for health insights"""
        try:
            # Add more sophisticated parsing logic here
            insights = {
                'mood_analysis': '',
                'energy_trend': '',
                'health_recommendations': [],
                'areas_of_concern': [],
                'positive_indicators': []
            }
            
            # Basic parsing of response
            lines = response.split('\n')
            current_section = ''
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if 'mood' in line.lower():
                    insights['mood_analysis'] = line
                elif 'energy' in line.lower():
                    insights['energy_trend'] = line
                elif 'recommend' in line.lower():
                    insights['health_recommendations'].append(line)
                elif 'concern' in line.lower():
                    insights['areas_of_concern'].append(line)
                elif 'positive' in line.lower():
                    insights['positive_indicators'].append(line)
                    
            return insights
            
        except Exception as e:
            logger.error(f"Error parsing health insights: {str(e)}")
            return {}
            
    def _parse_business_insights(self, response: str) -> Dict[str, Any]:
        """Parse AI response for business insights"""
        try:
            # Add more sophisticated parsing logic here
            insights = {
                'revenue_analysis': '',
                'growth_trend': '',
                'business_recommendations': [],
                'risks': [],
                'opportunities': []
            }
            
            # Basic parsing of response
            lines = response.split('\n')
            current_section = ''
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if 'revenue' in line.lower():
                    insights['revenue_analysis'] = line
                elif 'growth' in line.lower():
                    insights['growth_trend'] = line
                elif 'recommend' in line.lower():
                    insights['business_recommendations'].append(line)
                elif 'risk' in line.lower():
                    insights['risks'].append(line)
                elif 'opportunit' in line.lower():
                    insights['opportunities'].append(line)
                    
            return insights
            
        except Exception as e:
            logger.error(f"Error parsing business insights: {str(e)}")
            return {}

if __name__ == "__main__":
    # Test the AI handler
    async def main():
        async with AIHandler() as handler:
            test_content = [{"text": "Patient reports good sleep quality but low energy levels. Exercise routine maintained."}]
            print(await handler.analyze_health_content(test_content))
            
    asyncio.run(main())