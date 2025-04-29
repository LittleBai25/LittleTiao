#!/usr/bin/env python
"""
Test script for the Serper MCP client.
This script can be used to test if the Serper MCP client is working correctly.
"""

import asyncio
import json
from dotenv import load_dotenv
from agents.serper_client import SerperClient

async def test_initialize():
    """Test initializing the Serper client and listing available tools."""
    print("Testing Serper client initialization...")
    client = SerperClient()
    result = await client.initialize()
    
    if result:
        print("✅ Serper client initialized successfully")
        print(f"Available tools: {', '.join(client.available_tools)}")
    else:
        print("❌ Failed to initialize Serper client")
    
    return result

async def test_search(query="UCL Computer Science programs"):
    """Test performing a web search with the Serper client."""
    print(f"\nTesting web search with query: '{query}'...")
    client = SerperClient()
    result = await client.search_web(query)
    
    if "error" in result:
        print(f"❌ Search failed: {result['error']}")
        return False
    
    print("✅ Search completed successfully")
    print("\nSearch results:")
    print(json.dumps(result, indent=2))
    
    return True

async def test_program_search(keywords=None):
    """Test searching for UCL programs with the Serper client."""
    if keywords is None:
        keywords = ["Computer Science", "Data Science"]
    
    print(f"\nTesting UCL program search with keywords: {keywords}...")
    client = SerperClient()
    programs = await client.search_ucl_programs(keywords)
    
    if not programs:
        print("❌ No programs found")
        return False
    
    print(f"✅ Found {len(programs)} programs")
    print("\nProgram results:")
    for program in programs:
        print(f"- {program['program_name']} ({program['department']})")
    
    return True

async def run_tests():
    """Run all tests."""
    init_result = await test_initialize()
    
    if not init_result:
        print("\n❌ Initialization failed, skipping other tests")
        return
    
    search_result = await test_search()
    program_result = await test_program_search()
    
    print("\nTest Summary:")
    print(f"- Initialization: {'✅ Pass' if init_result else '❌ Fail'}")
    print(f"- Web Search: {'✅ Pass' if search_result else '❌ Fail'}")
    print(f"- Program Search: {'✅ Pass' if program_result else '❌ Fail'}")

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Run the tests
    asyncio.run(run_tests()) 