import os
import json
from datetime import datetime
import shutil
from pathlib import Path
import yaml
from dashboard_llm_processor import DashboardLLMProcessor

class TemplatePopulator:
    def __init__(self):
        self.llm_processor = DashboardLLMProcessor()
        self.template_dir = Path("templates")
        self.data_dir = Path("data")
        self.output_dir = Path("dashboard")
        
        # Create necessary directories
        for dir_path in [self.template_dir, self.data_dir, self.output_dir]:
            dir_path.mkdir(exist_ok=True)

    def load_template(self, template_name):
        """Load a template file from the templates directory."""
        template_path = self.template_dir / f"{template_name}.md"
        if not template_path.exists():
            raise FileNotFoundError(f"Template {template_name} not found")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def load_data(self, data_name):
        """Load data from YAML file."""
        data_path = self.data_dir / f"{data_name}.yaml"
        if not data_path.exists():
            return {}
        
        with open(data_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def save_dashboard(self, dashboard_name, content):
        """Save populated dashboard to output directory."""
        output_path = self.output_dir / f"{dashboard_name}.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def populate_template(self, template_content, data):
        """Populate template with data and dynamic content."""
        # Replace date placeholders
        now = datetime.now()
        content = template_content.replace("[[Today's Date]]", now.strftime("%Y-%m-%d"))
        content = content.replace("[[Date]]", now.strftime("%Y-%m-%d"))
        content = content.replace("[[Timestamp]]", now.strftime("%Y-%m-%d %H:%M:%S"))

        # Replace data placeholders if data exists
        if data:
            for key, value in data.items():
                placeholder = f"[[{key}]]"
                if isinstance(value, (str, int, float)):
                    content = content.replace(placeholder, str(value))

        return content

    def process_dashboard(self):
        """Process all dashboard templates and create populated versions."""
        templates = {
            "main_dashboard": "Main Dashboard",
            "health_hub": "Health Hub",
            "business_center": "Business Center",
            "personal_growth": "Personal Growth"
        }

        # Process each template
        for template_key, template_name in templates.items():
            print(f"Processing {template_name}...")
            
            # Load template and data
            template_content = self.load_template(template_key)
            template_data = self.load_data(template_key)
            
            # Get AI insights if needed
            ai_insights = self.llm_processor.process_section(template_key, template_data)
            if ai_insights:
                template_data.update(ai_insights)
            
            # Populate template
            populated_content = self.populate_template(template_content, template_data)
            
            # Save populated dashboard
            self.save_dashboard(template_key, populated_content)
            print(f"Created {template_key}.md in dashboard directory")

    def create_sample_data(self):
        """Create sample YAML data files for testing."""
        sample_data = {
            "main_dashboard": {
                "health_status": "⚠️ Monitoring",
                "business_status": "📈 Active",
                "personal_status": "🔄 In Progress",
                "health_trend": "↗️",
                "business_trend": "↗️",
                "personal_trend": "→"
            },
            "health_hub": {
                "hb_value": "12.4",
                "mcv_value": "68.8",
                "mch_value": "20.6",
                "ery_value": "6.0",
                "energy_level": "7",
                "hydration_goal": "2500",
                "pain_level": "3"
            },
            "business_center": {
                "youtube_progress": "40",
                "taxi_progress": "25",
                "restaurant_progress": "15",
                "current_investment": "5000",
                "roi": "0",
                "energy_impact": "6"
            },
            "personal_growth": {
                "therapy_progress": "75",
                "communication_score": "8",
                "boundary_score": "7",
                "mood_rating": "8",
                "anxiety_rating": "4",
                "focus_rating": "7"
            }
        }

        # Create data directory if it doesn't exist
        self.data_dir.mkdir(exist_ok=True)

        # Save sample data files
        for filename, data in sample_data.items():
            file_path = self.data_dir / f"{filename}.yaml"
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)

def main():
    populator = TemplatePopulator()
    
    # Create sample data if needed
    if not any(Path("data").glob("*.yaml")):
        print("Creating sample data files...")
        populator.create_sample_data()
    
    # Process dashboard templates
    print("Processing dashboard templates...")
    populator.process_dashboard()
    print("Dashboard creation complete!")

if __name__ == "__main__":
    main()
