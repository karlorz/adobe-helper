"""
Bypass local usage limits example

This example demonstrates how to bypass local usage tracking
to mimic the behavior of clearing browser data in Chrome.

Adobe tracks usage server-side, so clearing local session data
(similar to clearing browser cookies/storage) allows continued use.
"""

import asyncio
from pathlib import Path

from adobe import AdobePDFConverter


async def example_with_bypass():
    """Convert PDFs with local limits bypassed"""
    
    pdf_file = Path("document.pdf")
    
    # Method 1: Create converter with bypass enabled (default)
    async with AdobePDFConverter(
        bypass_local_limits=True,  # This is the key setting
        track_usage=False,  # Don't track locally - Adobe tracks server-side
    ) as converter:
        print(f"Converting {pdf_file.name}...")
        
        output_file = await converter.convert_pdf_to_word(pdf_file)
        print(f"✓ Conversion complete: {output_file}")


async def example_with_session_reset():
    """Manually reset session when needed"""
    
    pdf_file = Path("document.pdf")
    
    converter = AdobePDFConverter()
    await converter.initialize()
    
    try:
        # Convert first file
        output1 = await converter.convert_pdf_to_word(pdf_file)
        print(f"✓ First conversion: {output1}")
        
        # If you hit any limits, reset session (mimics clearing browser data)
        print("\nResetting session data (like clearing browser cookies)...")
        await converter.reset_session_data()
        
        # Continue converting
        output2 = await converter.convert_pdf_to_word(pdf_file)
        print(f"✓ Second conversion: {output2}")
        
    finally:
        await converter.close()


async def example_fresh_session():
    """Create converter with completely fresh session"""
    
    pdf_file = Path("document.pdf")
    
    # This creates a brand new converter with fresh session
    # (equivalent to opening a new incognito window)
    converter = await AdobePDFConverter.create_with_fresh_session()
    
    try:
        output = await converter.convert_pdf_to_word(pdf_file)
        print(f"✓ Conversion with fresh session: {output}")
    finally:
        await converter.close()


async def batch_convert_with_session_rotation():
    """Convert multiple files with automatic session rotation"""
    
    pdf_files = list(Path(".").glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found")
        return
    
    # Session will automatically rotate every 2 conversions
    async with AdobePDFConverter(
        use_session_rotation=True,  # Enable automatic rotation
        bypass_local_limits=True,   # Bypass local tracking
    ) as converter:
        
        for i, pdf_file in enumerate(pdf_files, 1):
            try:
                print(f"\n[{i}/{len(pdf_files)}] Converting {pdf_file.name}...")
                
                output = await converter.convert_pdf_to_word(pdf_file)
                print(f"✓ Success: {output}")
                
                # Show session stats
                stats = converter.get_session_stats()
                if stats:
                    print(f"  Session: {stats['conversions']}/{stats['limit']} conversions")
                    
            except Exception as e:
                print(f"✗ Failed: {e}")
                
                # On error, try resetting session
                print("  Resetting session and retrying...")
                await converter.reset_session_data()
                
                try:
                    output = await converter.convert_pdf_to_word(pdf_file)
                    print(f"✓ Retry success: {output}")
                except Exception as retry_error:
                    print(f"✗ Retry failed: {retry_error}")


if __name__ == "__main__":
    print("Adobe Helper - Bypass Usage Limits Example\n")
    print("=" * 60)
    
    # Run the simple bypass example
    asyncio.run(example_with_bypass())
    
    # Uncomment to try other examples:
    # asyncio.run(example_with_session_reset())
    # asyncio.run(example_fresh_session())
    # asyncio.run(batch_convert_with_session_rotation())
