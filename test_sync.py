import logging
import json
from ai_sync import NotionAISync
from ai_handler import AIHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_health_analysis():
    handler = AIHandler()
    test_content = """
    Patient Status Update:
    - Energy level: 6/10
    - Sleep quality: Good, 7.5 hours
    - Exercise: 30 min walking
    - Medication: Taken as prescribed
    - Pain level: 2/10 (mild)
    - Hydration: 2L water intake
    
    Notes:
    Showing improvement in sleep pattern but energy levels still fluctuating.
    Exercise routine maintained despite mild joint discomfort.
    """
    
    result = handler.analyze_health_content(test_content)
    logger.info("Health Analysis Result:")
    logger.info(json.dumps(result, indent=2))
    return result

def test_sync():
    sync = NotionAISync()
    sync.sync()

if __name__ == "__main__":
    logger.info("Starting test sync...")
    test_health_analysis()
    test_sync() 