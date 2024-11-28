import os
import json
from datetime import datetime
from dashboard_llm_processor import DashboardLLMProcessor
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

class DashboardManager:
    def __init__(self):
        self.notion = Client(auth=os.getenv('NOTION_API_KEY'))
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        self.processor = DashboardLLMProcessor()
        
    def extract_health_data(self, page_content):
        """Extract health metrics from dashboard"""
        health_metrics = {
            "blood_values": {
                "HB": {"value": 12.4, "range": "13.5-17.2", "status": "below", "trend": "stable"},
                "MCV": {"value": 68.8, "range": "80-99", "status": "below", "trend": "stable"},
                "MCH": {"value": 20.6, "range": "27-33.5", "status": "below", "trend": "stable"},
                "Ery": {"value": 6.0, "range": "4.3-5.8", "status": "above", "trend": "stable"}
            },
            "medication": {
                "morning": {
                    "Escitalopram": {"dose": "20mg", "time": "10:00", "status": "taken"},
                    "Medikinet": {"dose": "10mg", "time": "10:00", "status": "taken"}
                },
                "afternoon": {
                    "Medikinet": {"dose": "10mg", "time": "16:00", "status": "taken"}
                }
            },
            "conditions": {
                "primary": "Thalassämie Minor",
                "secondary": "ADHS",
                "monitoring": ["Wundheilung", "Energielevel", "Hydration"]
            },
            "symptoms": {
                "energy": {"level": 7, "trend": "stable"},
                "pain": {"level": 3, "location": "Oberlippe"},
                "healing": {"status": "progress", "documentation": "daily_photos"}
            }
        }
        return health_metrics

    def extract_tracking_data(self, page_content):
        """Extract daily tracking data"""
        tracking_data = {
            "morning": {
                "time": "10:00",
                "energy": 7,
                "pain": 3,
                "medication_taken": True,
                "water_intake": 500,
                "mood": "focused",
                "activities": ["Meditation", "Leichte Bewegung"]
            },
            "afternoon": {
                "time": "14:00",
                "energy": 6,
                "activity_level": "moderate",
                "water_intake": 1500,
                "mood": "productive",
                "focus_areas": ["YouTube Setup", "Code Development"]
            },
            "evening": {
                "time": "20:00",
                "energy": 5,
                "healing_progress": 8,
                "water_intake": 2500,
                "mood": "relaxed",
                "sleep_quality": 7,
                "reflection": ["Productive day", "Good energy management"]
            }
        }
        return tracking_data

    def extract_business_data(self, page_content):
        """Extract business goals and progress"""
        business_data = {
            "projects": {
                "youtube": {
                    "name": "KI & Automatisierung Channel",
                    "status": "planning",
                    "priority": "high",
                    "next_steps": [
                        "Content-Strategie entwickeln",
                        "Equipment optimieren",
                        "Erste Videos planen"
                    ],
                    "resources_needed": ["Kamera", "Mikrofon", "Editing Software"],
                    "health_impact": "low"
                },
                "restaurant": {
                    "name": "Familienrestaurant",
                    "status": "analysis",
                    "priority": "medium",
                    "next_steps": [
                        "Preiskalkulation",
                        "Speisekarte optimieren",
                        "Personal planen"
                    ],
                    "concerns": ["Gesundheitliche Belastung", "Zeitaufwand"],
                    "health_impact": "high"
                },
                "taxi": {
                    "name": "Taxi-Unternehmen",
                    "status": "planning",
                    "priority": "high",
                    "next_steps": [
                        "Förderung recherchieren",
                        "Geschäftsplan erstellen",
                        "Lizenzen prüfen"
                    ],
                    "opportunities": ["Flexible Zeiten", "Skalierbar"],
                    "health_impact": "medium"
                }
            },
            "priorities": {
                "short_term": "YouTube Channel",
                "medium_term": "Taxi-Unternehmen",
                "long_term": "Restaurant"
            }
        }
        return business_data

    def extract_relationship_data(self, page_content):
        """Extract relationship information"""
        relationship_data = {
            "communication": {
                "status": "improving",
                "strengths": ["Gegenseitige Unterstützung", "Offene Gespräche"],
                "challenges": ["Emotionale Regulation", "Eifersucht"],
                "improvements": ["Tägliche Check-ins", "Aktives Zuhören"]
            },
            "boundaries": {
                "status": "in_progress",
                "current_focus": ["Persönlicher Raum", "Emotionale Grenzen"],
                "achievements": ["Klare Kommunikation", "Respekt für Bedürfnisse"],
                "next_steps": ["Grenzen definieren", "Konsequenzen besprechen"]
            },
            "development": {
                "personal": {
                    "therapy_progress": "active",
                    "emotional_growth": "positive",
                    "health_support": "strong"
                },
                "professional": {
                    "mutual_support": "high",
                    "shared_goals": ["Business-Entwicklung", "Finanzielle Stabilität"],
                    "challenges": ["Work-Life-Balance", "Stress-Management"]
                }
            },
            "activities": {
                "planned": ["Gemeinsames Kochen", "Spaziergang", "Film-Abend"],
                "completed": ["Therapie-Gespräch", "Zukunftsplanung"]
            }
        }
        return relationship_data

    def process_dashboard(self):
        """Process entire dashboard and generate insights"""
        try:
            # In a real implementation, you would fetch the actual page content
            page_content = "Placeholder for actual Notion page content"
            
            # Extract data from different sections
            health_metrics = self.extract_health_data(page_content)
            tracking_data = self.extract_tracking_data(page_content)
            business_data = self.extract_business_data(page_content)
            relationship_data = self.extract_relationship_data(page_content)
            
            # Process each section with LLM
            health_analysis = self.processor.analyze_health_metrics(health_metrics)
            tracking_analysis = self.processor.process_daily_tracking(tracking_data)
            business_analysis = self.processor.update_business_goals(business_data)
            relationship_analysis = self.processor.relationship_analysis(relationship_data)
            
            # Combine all data for daily summary
            dashboard_data = {
                "health": health_metrics,
                "tracking": tracking_data,
                "business": business_data,
                "relationship": relationship_data,
                "analyses": {
                    "health": health_analysis,
                    "tracking": tracking_analysis,
                    "business": business_analysis,
                    "relationship": relationship_analysis
                }
            }
            
            # Generate daily summary
            daily_summary = self.processor.generate_daily_summary(dashboard_data)
            
            # Save results
            self.save_analysis(dashboard_data, daily_summary)
            
            return daily_summary
            
        except Exception as e:
            print(f"Error processing dashboard: {e}")
            return None

    def save_analysis(self, dashboard_data, daily_summary):
        """Save analysis results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save to JSON file
        analysis_file = f"notion_export/analysis/dashboard_analysis_{timestamp}.json"
        os.makedirs(os.path.dirname(analysis_file), exist_ok=True)
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "dashboard_data": dashboard_data,
                "daily_summary": daily_summary
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Analysis saved to {analysis_file}")

def main():
    manager = DashboardManager()
    summary = manager.process_dashboard()
    
    if summary:
        print("\nDaily Summary:")
        print(summary)

if __name__ == "__main__":
    main()
