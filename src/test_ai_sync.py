import pytest
import os
from ai_sync import NotionAISync
from datetime import datetime
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

@pytest.fixture
def ai_sync():
    """Create an instance of NotionAISync for testing"""
    # Create a new event loop for each test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Create instance with test configuration
    sync = NotionAISync()
    sync.database_id = "test-db-id"  # Set test database ID
    
    # Mock the Notion client with AsyncMock
    sync.notion = MagicMock()
    sync.notion.databases = AsyncMock()
    sync.notion.pages = AsyncMock()
    sync.notion.blocks = AsyncMock()
    sync.notion.blocks.children = AsyncMock()
    
    return sync

@pytest.mark.asyncio
async def test_init(ai_sync):
    """Test initialization of NotionAISync"""
    assert ai_sync.notion is not None
    assert ai_sync.database_id is not None
    assert ai_sync.ai_handler is not None

@pytest.mark.asyncio
async def test_validate_database(ai_sync):
    """Test database validation"""
    # Mock the Notion API call
    mock_response = {"object": "database"}
    ai_sync.notion.databases.retrieve.return_value = mock_response
    
    # Test valid database
    result = await ai_sync.validate_database("test-db-id")
    assert result is True
    
    # Test invalid database
    ai_sync.notion.databases.retrieve.side_effect = Exception("Database not found")
    with pytest.raises(Exception):
        await ai_sync.validate_database("invalid-db-id")

@pytest.mark.asyncio
async def test_sync_database(ai_sync):
    """Test database synchronization"""
    # Mock database query response
    mock_pages = {
        "results": [
            {
                "id": "page1",
                "properties": {
                    "Name": {"title": [{"text": {"content": "Test Page"}}]},
                    "Status": {"select": {"name": "Active"}}
                }
            }
        ]
    }
    
    # Mock the necessary Notion API calls
    ai_sync.notion.databases.query.return_value = mock_pages
    ai_sync.notion.pages.retrieve.return_value = {}
    ai_sync.notion.blocks.children.list.return_value = {"results": []}
    ai_sync.notion.databases.retrieve.return_value = {"properties": {}}
    ai_sync.notion.databases.update.return_value = {"properties": {}}
    
    # Test sync
    await ai_sync.sync_database("test-db-id", "main")
    
    # Verify API calls were made
    assert ai_sync.notion.databases.query.await_count == 1
    assert ai_sync.notion.pages.retrieve.await_count >= 1

@pytest.mark.asyncio
async def test_process_page(ai_sync):
    """Test page processing"""
    # Mock page data
    page_id = "test-page-id"
    page_data = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Page"}}]},
            "Status": {"select": {"name": "Active"}}
        }
    }
    
    # Mock Notion API calls
    ai_sync.notion.pages.retrieve.return_value = page_data
    ai_sync.notion.blocks.children.list.return_value = {"results": []}
    ai_sync.notion.pages.update.return_value = {}
    
    # Test processing
    await ai_sync.process_page({"id": page_id}, "main")
    
    # Verify API calls
    assert ai_sync.notion.pages.retrieve.await_count >= 1
    assert ai_sync.notion.pages.update.await_count >= 1

@pytest.mark.asyncio
async def test_get_block_content(ai_sync):
    """Test block content retrieval"""
    # Mock block data
    mock_blocks = {
        "results": [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "Test content"}]
                },
                "has_children": False,
                "id": "child-block-id"
            }
        ]
    }
    
    # Mock Notion API call
    ai_sync.notion.blocks.children.list.return_value = mock_blocks
    
    # Test content retrieval
    content = await ai_sync.get_block_content("test-block-id")
    assert len(content) > 0
    assert content[0] == "Test content"
    
    # Test with children blocks
    mock_blocks["results"][0]["has_children"] = True
    mock_child_blocks = {
        "results": [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "Child content"}]
                },
                "has_children": False
            }
        ]
    }
    ai_sync.notion.blocks.children.list.side_effect = [mock_blocks, mock_child_blocks]
    
    content = await ai_sync.get_block_content("test-block-id")
    assert len(content) > 0
    assert "Test content" in content
    assert "Child content" in content

@pytest.mark.asyncio
async def test_save_content_snapshot(ai_sync, tmp_path):
    """Test content snapshot saving"""
    # Prepare test data
    page_id = "test-page-id"
    content = [{"type": "text", "content": "Test content"}]
    
    # Set up temporary directory
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    os.environ['DATA_DIR'] = str(data_dir)
    
    # Test saving
    await ai_sync.save_content_snapshot(page_id, content)
    
    # Get the most recent file in the directory
    snapshot_files = list(data_dir.glob(f"page_{page_id}_*.json"))
    assert len(snapshot_files) > 0
    snapshot_file = snapshot_files[0]
    assert snapshot_file.exists()
    
    # Verify content
    with open(snapshot_file) as f:
        saved_data = json.load(f)
        assert saved_data['page_id'] == page_id
        assert saved_data['content'] == content

@pytest.mark.asyncio
async def test_verify_database_schema(ai_sync):
    """Test database schema verification"""
    # Mock database data with missing required properties
    mock_db = {
        "properties": {}  # Start with no properties
    }
    
    # Mock Notion API calls
    ai_sync.notion.databases.retrieve.return_value = mock_db
    ai_sync.notion.databases.update.return_value = mock_db
    
    # Test verification for main database
    result = await ai_sync.verify_database_schema("test-db-id", "main")
    assert result is True
    
    # Verify update was called with correct properties
    assert ai_sync.notion.databases.update.await_count == 1
    call_args = ai_sync.notion.databases.update.call_args[1]
    assert 'database_id' in call_args
    assert 'properties' in call_args
    assert 'updated_at' in call_args['properties']
    
    # Test with health database
    mock_db = {
        "properties": {}
    }
    ai_sync.notion.databases.retrieve.return_value = mock_db
    ai_sync.notion.databases.update.reset_mock()
    
    result = await ai_sync.verify_database_schema("test-db-id", "health")
    assert result is True
    
    # Verify update was called with correct properties
    assert ai_sync.notion.databases.update.await_count == 1
    call_args = ai_sync.notion.databases.update.call_args[1]
    assert 'database_id' in call_args
    assert 'properties' in call_args
    assert 'updated_at' in call_args['properties']
    assert 'status' in call_args['properties']
    assert 'ai_insights' in call_args['properties']

if __name__ == '__main__':
    pytest.main(['-v', '--cov=.', '--cov-report=term-missing'])
