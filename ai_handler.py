import os
import logging
from datetime import datetime
import ollama
import json
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIHandler:
    def __init__(self):
        load_dotenv()
        self.host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model = os.getenv('MODEL_NAME', 'llama2')
        
    def analyze_health_content(self, content):
        try:
            prompt = f"""
            You are a health analytics AI. Analyze this health data and provide a structured response:

            {content}

            Respond in this exact format:

            Summary:
            Patient shows stable condition with moderate energy levels and good medication compliance.

            Metrics:
            energy_level: 7/10
            sleep_quality: Good (7.5 hours)
            pain_level: 2/10 (mild)
            medication_adherence: Compliant

            Recommendations:
            - Maintain current medication schedule
            - Consider light exercise to improve energy levels

            Trends:
            - Sleep quality improving
            - Pain levels stable

            Alerts:
            - Monitor energy levels
            - Ensure continued medication compliance

            Do not include any additional text or instructions in your response.
            """
            
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                system="You are a precise medical analysis AI. Respond only with the analysis in the exact format specified.",
                options={
                    "temperature": 0.2,  # Even lower temperature for more consistent output
                    "top_k": 5,         # More restrictive token selection
                    "top_p": 0.8,       # More focused sampling
                    "num_predict": 500,  # Limit response length
                    "stop": [           # Stop sequences to prevent additional text
                        "\n\n\n",
                        "Remember:",
                        "Note:"
                    ]
                }
            )
            
            # Parse the response
            result = self._parse_structured_response(response.response)
            logger.info(f"AI Analysis Result: {json.dumps(result, indent=2)}")
            return result
            
        except Exception as e:
            logger.error(f"Error in AI health analysis: {str(e)}")
            return {
                'summary': '',
                'metrics': {},
                'recommendations': [],
                'trends': [],
                'alerts': []
            }
    
    def analyze_business_content(self, content):
        try:
            prompt = f"""
            As a business analytics AI, analyze this business content:

            {content}

            Provide a structured analysis in JSON format:
            {{
                "summary": "Brief performance overview",
                "metrics": {{
                    "efficiency": "Efficiency assessment",
                    "productivity": "Productivity indicators",
                    "revenue_trends": "Revenue pattern analysis",
                    "resource_utilization": "Resource usage assessment"
                }},
                "recommendations": [
                    "List of actionable business recommendations"
                ],
                "risks": [
                    "Identified business risks"
                ],
                "opportunities": [
                    "Potential growth opportunities"
                ]
            }}
            """
            
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                temperature=0.7,
                top_k=50
            )
            return self._parse_json_response(response.response)
            
        except Exception as e:
            logger.error(f"Error in AI business analysis: {str(e)}")
            return {
                'summary': '',
                'metrics': {},
                'recommendations': [],
                'risks': [],
                'opportunities': []
            }
    
    def _parse_json_response(self, response):
        """Parse JSON response with fallback to text parsing"""
        try:
            # Try to parse as JSON first
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, falling back to text parsing")
            try:
                # Fallback to text parsing
                lines = response.split('\n')
                result = {
                    'summary': '',
                    'metrics': {},
                    'recommendations': [],
                    'risks': [],
                    'trends': [],
                    'alerts': [],
                    'opportunities': []
                }
                
                current_section = None
                current_subsection = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Handle section headers
                    if line.endswith(':'):
                        current_section = line[:-1].lower()
                        current_subsection = None
                        continue
                    
                    # Handle content
                    if current_section:
                        # Handle metrics section specially
                        if current_section == 'metrics':
                            if ':' in line:
                                key, value = [x.strip() for x in line.split(':', 1)]
                                result['metrics'][key] = value
                        # Handle summary section
                        elif current_section == 'summary':
                            if not result['summary']:  # Only set if empty
                                result['summary'] = line
                        # Handle list sections
                        elif current_section in result and isinstance(result[current_section], list):
                            # Clean up bullet points and dashes
                            if line.startswith('- '):
                                line = line[2:]
                            elif line.startswith('* '):
                                line = line[2:]
                            result[current_section].append(line)
                
                return result
                
            except Exception as e:
                logger.error(f"Error in fallback parsing: {str(e)}")
                return {
                    'summary': response[:200] + '...' if len(response) > 200 else response,
                    'metrics': {},
                    'recommendations': [],
                    'risks': [],
                    'trends': [],
                    'alerts': [],
                    'opportunities': []
                }
    
    def _parse_structured_response(self, response):
        """Parse structured response with specific section handling"""
        try:
            sections = {
                'summary': '',
                'metrics': {},
                'recommendations': [],
                'trends': [],
                'alerts': []
            }
            
            current_section = None
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check for section headers
                lower_line = line.lower()
                if lower_line.endswith(':'):
                    section_name = lower_line[:-1].strip()
                    if section_name in sections:
                        current_section = section_name
                    continue
                
                # Process content based on section
                if current_section:
                    if current_section == 'summary':
                        if not sections['summary']:
                            sections['summary'] = line
                    elif current_section == 'metrics':
                        if ':' in line:
                            key, value = [x.strip() for x in line.split(':', 1)]
                            sections['metrics'][key] = value
                    else:
                        # Handle list items
                        if line.startswith('- '):
                            line = line[2:]
                        elif line.startswith('* '):
                            line = line[2:]
                        if line:
                            sections[current_section].append(line)
            
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing structured response: {str(e)}")
            return {
                'summary': response[:200] + '...' if len(response) > 200 else response,
                'metrics': {},
                'recommendations': [],
                'trends': [],
                'alerts': []
            }

if __name__ == "__main__":
    # Test the AI handler
    handler = AIHandler()
    test_content = "Patient reports good sleep quality but low energy levels. Exercise routine maintained."
    print(handler.analyze_health_content(test_content)) 