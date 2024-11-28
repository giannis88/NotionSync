import os
import markdown
from notion_client import Client
from datetime import datetime

# Set up Notion client
NOTION_TOKEN = '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'
DATABASE_ID = '14ce4a7d-76a4-8180-ad20-c77d2560761a'
notion = Client(auth=NOTION_TOKEN)

def read_markdown_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def chunk_content(content, max_length=2000):
    """Split content into chunks that fit within Notion's limits."""
    chunks = []
    lines = content.split('\n')
    current_chunk = []
    current_length = 0
    
    for line in lines:
        if current_length + len(line) + 1 > max_length:
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_length = len(line) + 1
        else:
            current_chunk.append(line)
            current_length += len(line) + 1
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

def create_page_with_content(title, content, page_type):
    """Create a new page with content and return its ID."""
    # First create a blank page
    page = notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "Type": {"select": {"name": page_type}},
            "Status": {"select": {"name": "Active"}},
            "Priority": {"select": {"name": "High"}},
            "Created": {"date": {"start": datetime.now().date().isoformat()}}
        }
    )
    
    # Then add the content blocks
    notion.blocks.children.append(
        block_id=page['id'],
        children=[
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": title}}]
                }
            }
        ]
    )
    
    # Add content in chunks
    content_chunks = chunk_content(content)
    for chunk in content_chunks:
        notion.blocks.children.append(
            block_id=page['id'],
            children=[{
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                }
            }]
        )
    
    return page['id']

def sync_dashboards():
    # Clear existing database entries
    existing_pages = notion.databases.query(database_id=DATABASE_ID).get('results')
    for page in existing_pages:
        notion.pages.update(page_id=page['id'], archived=True)
    
    # Create Business Center
    print("\nCreating Business Center page...")
    business_content = read_markdown_file('dashboard/business_center.md')
    business_id = create_page_with_content("Business Center", business_content, "Business")
    business_url = f"https://notion.so/{business_id.replace('-', '')}"
    print(f"Business Center created!")
    print(f"Direct URL: {business_url}")
    
    # Create Health Hub
    print("\nCreating Health Hub page...")
    health_content = read_markdown_file('dashboard/health_hub.md')
    health_id = create_page_with_content("Health Hub", health_content, "Health")
    health_url = f"https://notion.so/{health_id.replace('-', '')}"
    print(f"Health Hub created!")
    print(f"Direct URL: {health_url}")
    
    # Print main dashboard URL
    print(f"\nMain Dashboard URL: https://notion.so/{DATABASE_ID.replace('-', '')}")
    print("\nNote: You can now click on the page names in the database to open them directly!")

if __name__ == "__main__":
    print("Starting dashboard sync...")
    sync_dashboards()
    print("\nDashboard content synced successfully!")
