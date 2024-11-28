import os
from pathlib import Path
import re
from datetime import datetime

class ClaudeFormatter:
    def __init__(self):
        self.base_path = Path("notion_export")
        
    def get_latest_dashboard(self):
        """Get the most recent dashboard file"""
        files = list(self.base_path.glob("master_dashboard_*.md"))
        if not files:
            raise FileNotFoundError("No dashboard files found")
        return max(files, key=lambda x: x.stat().st_mtime)
    
    def extract_section(self, content, start_marker, end_marker=None):
        """Extract a section from the content"""
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return ""
        
        if end_marker:
            end_idx = content.find(end_marker, start_idx)
            if end_idx == -1:
                return content[start_idx:]
            return content[start_idx:end_idx]
        return content[start_idx:]
    
    def format_health_analysis(self, content):
        """Format dashboard content for health analysis"""
        health_metrics = self.extract_section(content, "| Wert | Aktuell |", "Aktionspunkte:")
        medications = self.extract_section(content, "| Uhrzeit | Medikament |", "Bei Bedarf:")
        daily_tasks = self.extract_section(content, "Tagesaufgaben:", "Wissensbasis:")
        
        prompt = f"""Please analyze my current health dashboard data and provide insights:

Current Health Metrics:
{health_metrics}

Current medications:
{medications}

Daily Health Tasks:
{daily_tasks}

Please provide:
1. Analysis of blood values and their implications
2. Recommendations for health optimization
3. Suggestions for daily routine improvements
4. Any concerning patterns or areas needing attention
5. Specific questions I should ask at my next appointment"""
        
        return prompt

    def format_health_optimization(self, content):
        """Format dashboard content for health dashboard optimization"""
        prompt = f"""Please help optimize my health tracking dashboard. Here's my current setup:

{content}

Please suggest:
1. Additional metrics I should track
2. Better organization of information
3. Important correlations to monitor
4. Automation opportunities
5. Ways to make the dashboard more actionable"""
        
        return prompt
    
    def format_business_analysis(self, content):
        """Format dashboard content for business analysis"""
        business_section = ""
        if "Business |" in content:
            start = content.find("Business |")
            end = content.find("Beziehung |", start)
            business_section = content[start:end] if end != -1 else content[start:]
            
        prompt = f"""Please analyze my business dashboard and provide strategic insights:

Current Business Status:
{business_section}

Please provide:
1. Analysis of current business status
2. Strategic recommendations
3. Priority action items
4. Resource optimization suggestions
5. Growth opportunities"""
        
        return prompt

def main():
    formatter = ClaudeFormatter()
    
    try:
        # Get latest dashboard file
        latest_file = formatter.get_latest_dashboard()
        content = latest_file.read_text(encoding='utf-8')
        
        # Menu
        print("\nClaude Dashboard Formatter")
        print("========================")
        print("1. Health Analysis")
        print("2. Health Dashboard Optimization")
        print("3. Business Analysis")
        print("4. Exit")
        
        choice = input("\nSelect an option (1-4): ")
        
        if choice == "1":
            prompt = formatter.format_health_analysis(content)
        elif choice == "2":
            prompt = formatter.format_health_optimization(content)
        elif choice == "3":
            prompt = formatter.format_business_analysis(content)
        elif choice == "4":
            return
        else:
            print("Invalid choice!")
            return
            
        # Save prompt to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = formatter.base_path / f"claude_prompt_{timestamp}.txt"
        output_file.write_text(prompt, encoding='utf-8')
        
        print(f"\nPrompt saved to: {output_file}")
        print("\nCopy the content of this file and paste it into your Claude chat!")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()