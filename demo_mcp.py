import sys
sys.path.insert(0, 'src')
import asyncio
from jdocmunch_mcp.tools.index_repo import index_repo
from jdocmunch_mcp.tools.index_local import index_local

async def demo_github():
    print('=== GitHub Repository Indexing ===')
    print('Indexing raspberrypi/linux...')
    result = await index_repo('raspberrypi/linux', use_ai_summaries=True)
    print(f"Success: {result['success']}")
    print(f"Files: {result['file_count']}")
    print(f"Sections: {result['section_count']}")

async def demo_local():
    print('\n=== Local Codebase Indexing ===')
    print('Indexing current directory...')
    result = await index_local('.', use_ai_summaries=False)
    print(f"Success: {result['success']}")
    print(f"Repo: {result['repo']}")
    print(f"Files: {result['file_count']}")
    print(f"Sections: {result['section_count']}")
    print(f"Indexed files: {result['files']}")

async def demo():
    await demo_local()
    # Uncomment to test GitHub indexing (requires GITHUB_TOKEN for private repos)
    # await demo_github()

asyncio.run(demo())
