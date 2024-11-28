import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import yaml
from pathlib import Path

load_dotenv()

class DashboardLLMProcessor:
    def __init__(self):
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model = os.getenv('MODEL_NAME', 'llama2')
        self.data_dir = Path("data")
        self.model_name = "llama2"  # Default to llama2 for local processing

    def _call_ollama(self, prompt, system_prompt=None):
        """Make a call to Ollama API"""
        headers = {'Content-Type': 'application/json'}
        data = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.1,
                'top_p': 0.2,
                'num_predict': 2048,
            }
        }
        
        if system_prompt:
            data['system'] = system_prompt
            
        try:
            response = requests.post(f'{self.ollama_host}/api/generate', 
                                   headers=headers, 
                                   json=data)
            response.raise_for_status()
            return response.json()['response']
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return None

    def analyze_health_metrics(self, metrics):
        """Analyze health metrics and provide insights"""
        system_prompt = """Du bist ein medizinischer Datenanalyst, spezialisiert auf Blutbildanalyse und Thalassämie Minor.
        Analysiere die Gesundheitsdaten unter Berücksichtigung der Thalassämie Minor Diagnose.
        Gib präzise, umsetzbare Empfehlungen in deutscher Sprache.
        Berücksichtige dabei:
        - Typische Thalassämie-Werte
        - ADHS-Medikation
        - Energie-Management
        - Wundheilung"""
        
        prompt = f"""Analysiere diese Gesundheitsdaten im Kontext von Thalassämie Minor:
        {json.dumps(metrics, indent=2)}
        
        Bitte gib folgende Informationen:
        1. Kritische Abweichungen und deren Bedeutung
        2. Positive Indikatoren
        3. Konkrete Handlungsempfehlungen für:
           - Ernährung
           - Bewegung
           - Medikation
           - Energiemanagement
        4. Vorgeschlagene Kontrolluntersuchungen"""
        
        return self._call_ollama(prompt, system_prompt)

    def process_daily_tracking(self, tracking_data):
        """Process daily tracking data and generate insights"""
        system_prompt = """Du bist ein Gesundheits- und Wellness-Berater.
        Analysiere die täglichen Tracking-Daten unter Berücksichtigung von:
        - ADHS
        - Thalassämie Minor
        - Wundheilung
        - Medikation (Escitalopram/Medikinet)"""
        
        prompt = f"""Analysiere diese Tagestracking-Daten:
        {json.dumps(tracking_data, indent=2)}
        
        Bitte gib folgende Informationen:
        1. Muster im Tagesverlauf
        2. Optimale Zeitfenster für Aktivitäten
        3. Medikations-Effektivität
        4. Empfehlungen für:
           - Energiemanagement
           - Medikations-Timing
           - Aktivitätsplanung
           - Wundheilung"""
        
        return self._call_ollama(prompt, system_prompt)

    def update_business_goals(self, current_goals):
        """Process and update business goals"""
        system_prompt = """Du bist ein Business-Strategieberater.
        Analysiere die Geschäftsziele unter Berücksichtigung von:
        - YouTube-Kanal (KI & Automatisierung)
        - Restaurant-Option
        - Taxi-Unternehmen
        - Monteurzimmer-Vermietung
        Berücksichtige dabei die gesundheitlichen Einschränkungen."""
        
        prompt = f"""Analysiere diese Geschäftsziele und gib strategische Empfehlungen:
        {json.dumps(current_goals, indent=2)}
        
        Bitte gib folgende Informationen:
        1. Priorisierung der Projekte basierend auf:
           - ROI-Potenzial
           - Gesundheitliche Belastung
           - Zeitaufwand
           - Ressourcenbedarf
        2. Konkrete nächste Schritte für jedes Projekt
        3. Risikobewertung
        4. Optimale Ressourcenverteilung"""
        
        return self._call_ollama(prompt, system_prompt)

    def relationship_analysis(self, relationship_data):
        """Analyze relationship dynamics and provide insights"""
        system_prompt = """Du bist ein Beziehungsberater.
        Analysiere die Beziehungsdynamik unter Berücksichtigung von:
        - Eifersuchtsproblematik
        - Emotionale Regulation
        - Berufliche Entwicklung
        - Gesundheitliche Aspekte
        Gib konstruktive, umsetzbare Empfehlungen."""
        
        prompt = f"""Analysiere diese Beziehungsdynamik und gib Handlungsempfehlungen:
        {json.dumps(relationship_data, indent=2)}
        
        Bitte gib folgende Informationen:
        1. Kommunikationsmuster:
           - Stärken
           - Verbesserungspotenzial
           - Konkrete Übungen
        2. Grenzen und Vertrauen:
           - Aktuelle Situation
           - Entwicklungsbereiche
           - Praktische Schritte
        3. Gemeinsame Entwicklung:
           - Berufliche Unterstützung
           - Emotionale Balance
           - Gesundheitliche Aspekte
        4. Konkrete Aktionspunkte für:
           - Tägliche Kommunikation
           - Konfliktprävention
           - Gemeinsame Aktivitäten"""
        
        return self._call_ollama(prompt, system_prompt)

    def generate_daily_summary(self, dashboard_data):
        """Generate a comprehensive daily summary"""
        system_prompt = """Du bist ein persönlicher Entwicklungsberater.
        Erstelle eine umfassende Tageszusammenfassung.
        Berücksichtige dabei alle Lebensbereiche:
        - Gesundheit (Thalassämie Minor, ADHS)
        - Business (YouTube, Restaurant, Taxi)
        - Beziehung (Entwicklung, Kommunikation)
        - Persönliche Entwicklung"""
        
        prompt = f"""Erstelle eine Tageszusammenfassung basierend auf diesen Daten:
        {json.dumps(dashboard_data, indent=2)}
        
        Bitte gib folgende Informationen:
        1. Wichtigste Erfolge des Tages
        2. Kritische Beobachtungen
        3. Anpassungen der Prioritäten
        4. Fokus für morgen:
           - Gesundheit
           - Business
           - Beziehung
           - Persönliche Entwicklung"""
        
        return self._call_ollama(prompt, system_prompt)

    def process_section(self, section_name, data):
        """Process a dashboard section with AI insights."""
        try:
            # Add basic insights based on section type
            insights = {}
            
            if section_name == "health_hub":
                insights = self._process_health_data(data)
            elif section_name == "business_center":
                insights = self._process_business_data(data)
            elif section_name == "personal_growth":
                insights = self._process_personal_data(data)
            
            return insights
        except Exception as e:
            print(f"Error processing {section_name}: {str(e)}")
            return {}

    def _process_health_data(self, data):
        """Process health-related data."""
        insights = {
            "health_summary": "Basierend auf den aktuellen Werten:",
            "recommendations": []
        }
        
        # Process blood values if available
        if "hb_value" in data:
            hb = float(data["hb_value"])
            if hb < 13.5:
                insights["recommendations"].append(
                    "HB-Wert unter Normalbereich. Empfehlung: Eisenreiche Ernährung und Rücksprache mit Arzt."
                )

        # Process energy levels
        if "energy_level" in data:
            energy = int(data["energy_level"])
            if energy < 5:
                insights["recommendations"].append(
                    "Niedriges Energielevel. Empfehlung: Ruhezeiten einplanen und Aktivitäten anpassen."
                )

        return insights

    def _process_business_data(self, data):
        """Process business-related data."""
        insights = {
            "business_summary": "Geschäftliche Entwicklung:",
            "focus_areas": []
        }
        
        # Process project progress
        if "youtube_progress" in data:
            progress = int(data["youtube_progress"])
            if progress < 50:
                insights["focus_areas"].append(
                    "YouTube-Kanal benötigt mehr Aufmerksamkeit. Nächste Schritte: Content-Planung und Equipment-Setup."
                )

        return insights

    def _process_personal_data(self, data):
        """Process personal growth data."""
        insights = {
            "personal_summary": "Persönliche Entwicklung:",
            "growth_areas": []
        }
        
        # Process therapy progress
        if "therapy_progress" in data:
            progress = int(data["therapy_progress"])
            if progress > 70:
                insights["growth_areas"].append(
                    "Gute Fortschritte in der Therapie. Fokus auf Implementierung der gelernten Strategien."
                )

        return insights

    def save_insights(self, insights, section_name):
        """Save insights to a file for later reference."""
        insights_dir = self.data_dir / "insights"
        insights_dir.mkdir(exist_ok=True)
        
        filename = f"{section_name}_insights_{datetime.now().strftime('%Y%m%d')}.yaml"
        filepath = insights_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(insights, f, allow_unicode=True)

def main():
    # Example usage
    processor = DashboardLLMProcessor()
    
    # Example health metrics
    health_metrics = {
        "HB": {"value": 12.4, "range": "13.5-17.2", "status": "below"},
        "MCV": {"value": 68.8, "range": "80-99", "status": "below"},
        "MCH": {"value": 20.6, "range": "27-33.5", "status": "below"},
        "Ery": {"value": 6.0, "range": "4.3-5.8", "status": "above"}
    }
    
    # Get health analysis
    health_analysis = processor.analyze_health_metrics(health_metrics)
    print("\nHealth Analysis:")
    print(health_analysis)

if __name__ == "__main__":
    main()
