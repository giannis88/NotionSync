import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from notion_client import Client
import pandas as pd
import json
from ai_handler import AIHandler
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NotionAISync:
    def __init__(self):
        load_dotenv()
        self.notion = Client(auth=os.getenv('NOTION_TOKEN'))
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        self.health_database_id = os.getenv('HEALTH_DATABASE_ID')
        self.business_database_id = os.getenv('BUSINESS_DATABASE_ID')
        self.ai_handler = AIHandler()
        
    async def sync(self):
        """Main sync function that handles all database synchronization"""
        try:
            logger.info("Starting Notion AI sync process")
            
            sync_tasks = []
            
            # Add main database sync task
            sync_tasks.append(self.sync_database(self.database_id, "main"))
            
            # Add health database sync task if configured
            if self.health_database_id:
                try:
                    await self.validate_database(self.health_database_id)
                    sync_tasks.append(self.sync_database(self.health_database_id, "health"))
                except Exception as e:
                    logger.error(f"Health database validation failed: {str(e)}")
            
            # Add business database sync task if configured
            if self.business_database_id:
                try:
                    await self.validate_database(self.business_database_id)
                    sync_tasks.append(self.sync_database(self.business_database_id, "business"))
                except Exception as e:
                    logger.error(f"Business database validation failed: {str(e)}")
            
            # Run all sync tasks concurrently
            results = await asyncio.gather(*sync_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Sync task {i} failed: {str(result)}")
                else:
                    logger.info(f"Sync task {i} completed successfully")
            
            logger.info("All syncs completed")
            
        except Exception as e:
            logger.error(f"Sync process failed: {str(e)}")
            raise
    
    async def validate_database(self, database_id: str) -> bool:
        """Validate that a database exists and is accessible"""
        try:
            await self.notion.databases.retrieve(database_id=database_id)
            return True
        except Exception as e:
            logger.error(f"Database validation failed for {database_id}: {str(e)}")
            raise
    
    async def sync_database(self, database_id, db_type):
        try:
            logger.info(f"Starting sync for {db_type} database")
            
            # Verify database access and schema
            try:
                if not await self.verify_database_schema(database_id, db_type):
                    logger.error(f"Failed to verify/update schema for {db_type} database")
                    return
            except Exception as e:
                logger.error(f"Cannot access {db_type} database: {str(e)}")
                return
            
            # Query database
            response = await self.notion.databases.query(database_id=database_id)
            
            for page in response['results']:
                await self.process_page(page, db_type)
                
            logger.info(f"Completed sync for {db_type} database")
            
        except Exception as e:
            logger.error(f"Error syncing {db_type} database: {str(e)}")
    
    async def process_page(self, page, db_type):
        try:
            page_id = page['id']
            logger.info(f"Processing {db_type} page: {page_id}")
            
            # Get page properties
            content = await self.notion.pages.retrieve(page_id=page_id)
            
            # Get page content
            page_content = await self.get_block_content(page_id)
            
            # Save content for analysis
            await self.save_content_snapshot(page_id, page_content)
            
            # Process based on database type
            if db_type == "health":
                await self.process_health_page(page_id, content, page_content)
            elif db_type == "business":
                await self.process_business_page(page_id, content, page_content)
            else:
                await self.update_page(page_id, content)
            
        except Exception as e:
            logger.error(f"Error processing page {page_id}: {str(e)}")
    
    async def get_block_content(self, block_id):
        """Recursively get content from blocks"""
        try:
            blocks = await self.notion.blocks.children.list(block_id=block_id)
            content = []
            
            for block in blocks.get('results', []):
                block_type = block.get('type', '')
                if block_type == 'paragraph':
                    text = block.get('paragraph', {}).get('rich_text', [])
                    content.extend([t.get('plain_text', '') for t in text])
                elif block_type == 'heading_1':
                    text = block.get('heading_1', {}).get('rich_text', [])
                    content.extend([f"# {t.get('plain_text', '')}" for t in text])
                elif block_type == 'heading_2':
                    text = block.get('heading_2', {}).get('rich_text', [])
                    content.extend([f"## {t.get('plain_text', '')}" for t in text])
                elif block_type == 'bulleted_list_item':
                    text = block.get('bulleted_list_item', {}).get('rich_text', [])
                    content.extend([f"- {t.get('plain_text', '')}" for t in text])
                
                # Recursively get content from child blocks
                if block.get('has_children', False):
                    child_content = await self.get_block_content(block['id'])
                    content.extend(child_content)
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting block content: {str(e)}")
            return []
    
    async def save_content_snapshot(self, page_id, content):
        """Save page content for analysis"""
        try:
            data_dir = os.getenv('DATA_DIR', 'data')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{data_dir}/page_{page_id}_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'page_id': page_id,
                    'timestamp': timestamp,
                    'content': content
                }, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved content snapshot: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving content snapshot: {str(e)}")
    
    async def process_health_page(self, page_id, properties, content):
        try:
            # Extract metrics from properties
            metrics = await self.extract_health_metrics(properties)
            
            # Analyze content for health insights
            insights = await self.ai_handler.analyze_health_content(content)
            
            # Combine metrics and insights
            status = await self.get_health_status(metrics, insights)
            
            # Get existing properties
            existing_props = properties.get('properties', {})
            
            # Remove any properties we don't want to update
            if 'Type' in existing_props:
                del existing_props['Type']
            
            # Prepare update properties
            update_props = {
                'properties': {
                    **existing_props,
                    "updated_at": {
                        "type": "date",
                        "date": {
                            "start": datetime.now().isoformat(),
                            "end": None
                        }
                    },
                    "status": {
                        "type": "select",
                        "select": {
                            "name": status
                        }
                    },
                    "ai_insights": {
                        "type": "rich_text",
                        "rich_text": [{
                            "type": "text",
                            "text": {
                                "content": insights.get('summary', '')
                            }
                        }]
                    }
                }
            }
            
            # Update page with enhanced content
            await self.notion.pages.update(
                page_id=page_id,
                **update_props
            )
            logger.info(f"Updated health page with insights: {page_id}")
            
        except Exception as e:
            logger.error(f"Error processing health page {page_id}: {str(e)}")
    
    async def process_business_page(self, page_id, content):
        try:
            # Extract business metrics
            metrics = await self.extract_business_metrics(content)
            
            # Update with enhanced content
            await self.notion.pages.update(
                page_id=page_id,
                properties={
                    "Last Updated": {"date": {"start": datetime.now().isoformat()}},
                    "Status": {"select": {"name": await self.get_business_status(metrics)}}
                }
            )
            logger.info(f"Updated business page: {page_id}")
            
        except Exception as e:
            logger.error(f"Error processing business page {page_id}: {str(e)}")
    
    async def extract_health_metrics(self, content):
        try:
            metrics = {
                'energy_level': None,
                'sleep_quality': None,
                'exercise_done': False,
                'medication_taken': False,
                'pain_level': None,
                'hydration': None,
                'lab_values': {}
            }
            
            # Extract metrics from content
            if 'properties' in content:
                props = content['properties']
                if 'Energy Level' in props:
                    metrics['energy_level'] = props['Energy Level'].get('number', 0)
                if 'Sleep Quality' in props:
                    metrics['sleep_quality'] = props['Sleep Quality'].get('number', 0)
                if 'Exercise' in props:
                    metrics['exercise_done'] = props['Exercise'].get('checkbox', False)
                if 'Medication' in props:
                    metrics['medication_taken'] = props['Medication'].get('checkbox', False)
                if 'Pain Level' in props:
                    metrics['pain_level'] = props['Pain Level'].get('number', 0)
                if 'Hydration' in props:
                    metrics['hydration'] = props['Hydration'].get('number', 0)
                
            logger.info(f"Extracted health metrics: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error extracting health metrics: {str(e)}")
            return {}
    
    async def extract_business_metrics(self, content):
        try:
            metrics = {
                'revenue': 0.0,
                'tasks_completed': 0,
                'tasks_pending': 0,
                'priority_level': 'Medium',
                'deadline_status': 'On Track',
                'team_size': 0
            }
            
            # Extract metrics from content
            if 'properties' in content:
                props = content['properties']
                if 'Revenue' in props:
                    metrics['revenue'] = props['Revenue'].get('number', 0.0)
                if 'Tasks Completed' in props:
                    metrics['tasks_completed'] = props['Tasks Completed'].get('number', 0)
                if 'Tasks Pending' in props:
                    metrics['tasks_pending'] = props['Tasks Pending'].get('number', 0)
                if 'Priority' in props:
                    metrics['priority_level'] = props['Priority'].get('select', {}).get('name', 'Medium')
                if 'Deadline Status' in props:
                    metrics['deadline_status'] = props['Deadline Status'].get('select', {}).get('name', 'On Track')
                if 'Team Size' in props:
                    metrics['team_size'] = props['Team Size'].get('number', 0)
                
            logger.info(f"Extracted business metrics: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error extracting business metrics: {str(e)}")
            return {}
    
    async def get_health_status(self, metrics, insights):
        try:
            # Calculate health status based on metrics and insights
            status = "Active"
            
            if metrics.get('energy_level', 0) < 5:
                status = "Rest Needed"
            elif metrics.get('pain_level', 0) > 7:
                status = "Medical Attention"
            elif not metrics.get('medication_taken', False):
                status = "Medication Due"
            elif metrics.get('hydration', 0) < 6:
                status = "Hydration Needed"
            
            # Check for any critical insights
            if insights['recommendations']:
                status = "Medical Attention"
            
            logger.info(f"Calculated health status: {status}")
            return status
            
        except Exception as e:
            logger.error(f"Error calculating health status: {str(e)}")
            return "Unknown"
    
    async def get_business_status(self, metrics):
        try:
            # Calculate business status based on metrics
            status = "In Progress"
            
            if metrics.get('tasks_pending', 0) == 0:
                status = "Completed"
            elif metrics.get('priority_level') == 'High' and metrics.get('deadline_status') != 'On Track':
                status = "At Risk"
            elif metrics.get('revenue', 0) > 10000:
                status = "Performing"
            
            logger.info(f"Calculated business status: {status}")
            return status
            
        except Exception as e:
            logger.error(f"Error calculating business status: {str(e)}")
            return "Unknown"
    
    async def update_page(self, page_id, content):
        """Update a Notion page with basic content"""
        try:
            # Get existing properties to preserve them
            existing_props = content.get('properties', {})
            
            # Create a clean copy of properties without type information
            clean_props = {}
            for key, value in existing_props.items():
                if key != 'Last Updated' and key != 'Created':  # Skip these as we'll update them
                    clean_props[key] = value
            
            # Add our update timestamp
            clean_props["Last Updated"] = {
                "date": {
                    "start": datetime.now().isoformat(),
                    "end": None
                }
            }
            
            # Update the page
            update_data = {
                "properties": clean_props
            }
            
            await self.notion.pages.update(
                page_id=page_id,
                **update_data
            )
            logger.info(f"Updated page: {page_id}")
            
        except Exception as e:
            logger.error(f"Error updating page {page_id}: {str(e)}")
    
    async def verify_database_schema(self, database_id, db_type):
        """Verify and update database schema if needed"""
        try:
            logger.info(f"Verifying schema for {db_type} database")
            database = await self.notion.databases.retrieve(database_id=database_id)
            existing_props = database.get('properties', {})
            
            required_props = {
                'health': {
                    'updated_at': {
                        'date': {}
                    },
                    'status': {
                        'select': {
                            'options': [
                                {'name': 'Active', 'color': 'green'},
                                {'name': 'Rest Needed', 'color': 'yellow'},
                                {'name': 'Medical Attention', 'color': 'red'},
                                {'name': 'Medication Due', 'color': 'orange'},
                                {'name': 'Hydration Needed', 'color': 'blue'}
                            ]
                        }
                    },
                    'ai_insights': {
                        'rich_text': {}
                    }
                },
                'business': {
                    'updated_at': {
                        'date': {}
                    },
                    'status': {
                        'select': {
                            'options': [
                                {'name': 'In Progress', 'color': 'blue'},
                                {'name': 'Completed', 'color': 'green'},
                                {'name': 'At Risk', 'color': 'red'},
                                {'name': 'Performing', 'color': 'yellow'}
                            ]
                        }
                    },
                    'ai_analysis': {
                        'rich_text': {}
                    }
                },
                'main': {
                    'updated_at': {
                        'date': {}
                    }
                }
            }
            
            # Get required properties for this database type
            props_to_add = required_props.get(db_type, {})
            
            # Check for missing properties
            missing_props = {
                name: config for name, config in props_to_add.items()
                if name.lower() not in {k.lower() for k in existing_props.keys()}
            }
            
            if missing_props:
                logger.info(f"Adding missing properties to {db_type} database: {list(missing_props.keys())}")
                
                # Update database schema
                update_data = {
                    'properties': missing_props
                }
                
                await self.notion.databases.update(
                    database_id=database_id,
                    **update_data
                )
                
            return True
            
        except Exception as e:
            logger.error(f"Error verifying database schema: {str(e)}")
            return False

if __name__ == "__main__":
    import asyncio
    sync = NotionAISync()
    asyncio.run(sync.sync())
