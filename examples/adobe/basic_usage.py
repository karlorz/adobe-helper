"""
Basic usage example for Adobe Helper

This example demonstrates the simplest way to convert a PDF to Word.
"""

import asyncio
from pathlib import Path

from adobe import AdobePDFConverter


async def main():
    """Convert a PDF file to Word format"""

    # Path to your PDF file
    pdf_file = Path("document.pdf")  # Replace with your PDF file path

    # Create converter instance
    converter = AdobePDFConverter()

    try:
        # Initialize the converter
        await converter.initialize()

        print(f"Converting {pdf_file.name} to Word...")

        # Convert PDF to Word
        # Output file will be automatically named (document.docx)
        output_file = await converter.convert_pdf_to_word(pdf_file)

        print(f"✓ Conversion complete: {output_file}")

        # Show usage statistics
        usage = converter.get_usage_summary()
        if usage:
            print(f"\nUsage: {usage['count']}/{usage['limit']} conversions today")
            print(f"Remaining: {usage['remaining']}")

    except Exception as e:
        print(f"✗ Conversion failed: {e}")

    finally:
        # Clean up
        await converter.close()


# Alternative: Using async context manager (recommended)
async def main_with_context_manager():
    """Convert using context manager for automatic cleanup"""

    pdf_file = Path("document.pdf")

    async with AdobePDFConverter() as converter:
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
