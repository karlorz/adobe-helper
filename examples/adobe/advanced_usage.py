"""
Advanced configuration example for Adobe Helper

This example demonstrates advanced features and configuration options.
"""

import asyncio
import logging
from pathlib import Path

from adobe import AdobePDFConverter

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def convert_with_progress_tracking():
    """Convert PDF with progress callback"""

    def progress_callback(progress):
        """Callback function to track upload/download progress"""
        print(
            f"  Progress: {progress.percentage:.1f}% ({progress.bytes_uploaded}/{progress.total_bytes} bytes)"
        )

    pdf_file = Path("document.pdf")

    async with AdobePDFConverter() as converter:
        print(f"Converting {pdf_file.name} with progress tracking...")

        output_file = await converter.convert_pdf_to_word(
            pdf_file,
            progress_callback=progress_callback,  # Track progress
        )

        print(f"✓ Complete: {output_file}")


async def convert_with_custom_settings():
    """Convert with custom configuration"""

    converter = AdobePDFConverter(
        session_dir=Path(".adobe-cache"),  # Custom cache directory
        use_session_rotation=True,  # Enable session rotation
        track_usage=True,  # Track daily usage
        enable_rate_limiting=True,  # Enable rate limiting
    )

    try:
        await converter.initialize()

        # Show session stats
        session_stats = converter.get_session_stats()
        if session_stats:
            print(f"Session: {session_stats['session_id']}")
            print(f"Conversions: {session_stats['conversions']}/{session_stats['limit']}")

        # Convert file
        output_file = await converter.convert_pdf_to_word(Path("document.pdf"))
        print(f"✓ Converted: {output_file}")

        # Show updated stats
        usage = converter.get_usage_summary()
        if usage:
            print(f"\nDaily usage: {usage['count']}/{usage['limit']}")
            print(f"Percentage used: {usage['percentage_used']:.1f}%")

    finally:
        await converter.close()


async def convert_without_session_rotation():
    """Convert using a single session (simpler, but limited conversions)"""

    converter = AdobePDFConverter(
        use_session_rotation=False,  # Disable session rotation
        track_usage=False,  # Disable usage tracking
        enable_rate_limiting=False,  # Disable rate limiting
    )

    try:
        await converter.initialize()

        output_file = await converter.convert_pdf_to_word(Path("document.pdf"))
        print(f"✓ Converted: {output_file}")

    finally:
        await converter.close()


async def handle_errors_gracefully():
    """Example of proper error handling"""

    from adobe import (
        ConversionError,
        DownloadError,
        QuotaExceededError,
        UploadError,
        ValidationError,
    )

    pdf_file = Path("document.pdf")

    async with AdobePDFConverter() as converter:
        try:
            output_file = await converter.convert_pdf_to_word(pdf_file)
            print(f"✓ Success: {output_file}")

        except QuotaExceededError as e:
            print(f"✗ Daily quota exceeded: {e}")
            print(f"  Limit: {e.limit}, Current: {e.current}")
            print("  Please try again tomorrow or use a different session.")

        except ValidationError as e:
            print(f"✗ Invalid file: {e}")
            print(f"  Details: {e.details}")
            print("  Please check that the file exists and is a valid PDF.")

        except UploadError as e:
            print(f"✗ Upload failed: {e}")
            print("  Network issue or server rejected the file.")

        except ConversionError as e:
            print(f"✗ Conversion failed: {e}")
            print("  The PDF might be corrupted or have unsupported features.")

        except DownloadError as e:
            print(f"✗ Download failed: {e}")
            print("  Failed to download the converted file.")

        except Exception as e:
            print(f"✗ Unexpected error: {e}")


async def convert_multiple_with_session_management():
    """Convert multiple files with intelligent session management"""

    pdf_files = [
        Path("file1.pdf"),
        Path("file2.pdf"),
        Path("file3.pdf"),
        Path("file4.pdf"),
        Path("file5.pdf"),
    ]

    # Session rotation will automatically refresh after 2 conversions
    async with AdobePDFConverter(use_session_rotation=True) as converter:
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] Converting {pdf_file.name}")

            try:
                # Check session stats before conversion
                stats = converter.get_session_stats()
                if stats:
                    print(f"  Session: {stats['conversions']}/{stats['limit']} conversions")

                output_file = await converter.convert_pdf_to_word(pdf_file)
                print(f"  ✓ Output: {output_file}")

                # Session will auto-rotate if limit reached
                stats_after = converter.get_session_stats()
                if stats and stats_after:
                    if stats["session_id"] != stats_after["session_id"]:
                        print("  → Session rotated to new identity")

            except Exception as e:
                print(f"  ✗ Failed: {e}")


if __name__ == "__main__":
    print("Adobe Helper - Advanced Configuration Examples\n")

    # Choose one of the following examples:

    # Example 1: Progress tracking
    # asyncio.run(convert_with_progress_tracking())

    # Example 2: Custom settings
    asyncio.run(convert_with_custom_settings())

    # Example 3: Without session rotation
    # asyncio.run(convert_without_session_rotation())

    # Example 4: Error handling
    # asyncio.run(handle_errors_gracefully())

    # Example 5: Multiple files with session management
    # asyncio.run(convert_multiple_with_session_management())
