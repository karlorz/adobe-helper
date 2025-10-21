"""
Basic usage example for Adobe Helper

This example demonstrates the simplest way to convert a PDF to Word.
"""

import asyncio
import logging
from pathlib import Path

from adobe import AdobePDFConverter

# Configure logging to see conversion progress
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    """Convert a PDF file to Word format"""

    # Path to your PDF file
    pdf_file = Path("document.pdf")  # Replace with your PDF file path

    # Create converter instance with bypass enabled
    # This bypasses local usage tracking (Adobe tracks server-side)
    converter = AdobePDFConverter(
        bypass_local_limits=True,  # Mimic clearing browser data
        track_usage=False,  # Don't track locally
    )

    try:
        # Initialize the converter
        await converter.initialize()

        print(f"Converting {pdf_file.name} to Word...")

        # Convert PDF to Word
        # Output file will be automatically named (document.docx)
        output_file = await converter.convert_pdf_to_word(pdf_file)

        print(f"✓ Conversion complete: {output_file}")

        # Show session statistics
        stats = converter.get_session_stats()
        if stats:
            print(f"\nSession: {stats['conversions']}/{stats['limit']} conversions")

    except Exception as e:
        print(f"✗ Conversion failed: {e}")

    finally:
        # Clean up
        await converter.close()


# Alternative: Using async context manager (recommended)
async def main_with_context_manager():
    """Convert using context manager for automatic cleanup"""

    pdf_file = Path("document.pdf")

    # Bypass local limits - Adobe tracks usage server-side
    async with AdobePDFConverter(
        bypass_local_limits=True,
        track_usage=False,
    ) as converter:
        print(f"Converting {pdf_file.name} to Word...")

        output_file = await converter.convert_pdf_to_word(
            pdf_file,
            output_path=Path("output/converted.docx"),  # Custom output path
        )

        print(f"✓ Conversion complete: {output_file}")


if __name__ == "__main__":
    # Run the conversion
    asyncio.run(main())

    # Or use the context manager version
    # asyncio.run(main_with_context_manager())
