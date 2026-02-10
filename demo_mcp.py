import sys
sys.path.insert(0, 'src')
import asyncio
from jdocmunch_mcp.tools.index_repo import index_repo

async def demo():
    print('Indexing raspberrypi/linux...')
    result = await index_repo('raspberrypi/linux', use_ai_summaries=True)
    print(f"Success: {result['success']}")
    print(f"Files: {result['file_count']}")
    print(f"Sections: {result['section_count']}")

asyncio.run(demo())
