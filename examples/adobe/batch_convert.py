"""
Batch conversion example for Adobe Helper

This example shows how to convert multiple PDF files concurrently.
"""

import asyncio
from pathlib import Path

from adobe import AdobePDFConverter, QuotaExceededError


async def convert_single_file(
    converter: AdobePDFConverter, pdf_file: Path
) -> tuple[Path, Path | Exception]:
    """
    Convert a single PDF file

    Args:
        converter: AdobePDFConverter instance
        pdf_file: Path to PDF file

    Returns:
        Tuple of (input_path, output_path_or_exception)
    """
    try:
        output_file = await converter.convert_pdf_to_word(pdf_file)
        return (pdf_file, output_file)
    except Exception as e:
        return (pdf_file, e)


async def batch_convert_sequential():
    """Convert multiple PDFs one at a time"""

    # List of PDF files to convert
    pdf_files = [
        Path("document1.pdf"),
        Path("document2.pdf"),
        Path("document3.pdf"),
    ]

    async with AdobePDFConverter() as converter:
        print(f"Converting {len(pdf_files)} files sequentially...\n")

        results = []

        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"[{i}/{len(pdf_files)}] Converting {pdf_file.name}...")

            try:
                output_file = await converter.convert_pdf_to_word(pdf_file)
                print(f"  ✓ Success: {output_file}")
                results.append((pdf_file, output_file))

            except QuotaExceededError as e:
                print(f"  ✗ Quota exceeded: {e}")
                print("  Remaining files will not be converted.")
                break

            except Exception as e:
                print(f"  ✗ Failed: {e}")
                results.append((pdf_file, e))

        # Show summary
        print("\n" + "=" * 60)
        print("Conversion Summary:")
        print("=" * 60)

        success_count = sum(1 for _, result in results if isinstance(result, Path))
        failed_count = len(results) - success_count

        print(f"Total: {len(results)} files")
        print(f"Success: {success_count}")
        print(f"Failed: {failed_count}")

        # Show usage
        usage = converter.get_usage_summary()
        if usage:
            print(f"\nQuota: {usage['count']}/{usage['limit']} conversions used")


async def batch_convert_concurrent():
    """Convert multiple PDFs concurrently (faster but uses quota quickly)"""

    # Find all PDF files in current directory
    pdf_files = list(Path(".").glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in current directory")
        return

    print(f"Found {len(pdf_files)} PDF files")

    async with AdobePDFConverter() as converter:
        print(f"Converting {len(pdf_files)} files concurrently...\n")

        # Create conversion tasks
        tasks = [convert_single_file(converter, pdf_file) for pdf_file in pdf_files]

        # Run all conversions concurrently
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Show results
        print("\n" + "=" * 60)
        print("Conversion Results:")
        print("=" * 60)

        for pdf_file, result in results:
            if isinstance(result, Path):
                print(f"✓ {pdf_file.name} -> {result.name}")
            elif isinstance(result, Exception):
                print(f"✗ {pdf_file.name} -> Error: {result}")

        # Show summary
        success_count = sum(1 for _, result in results if isinstance(result, Path))
        failed_count = len(results) - success_count

        print(f"\nSuccess: {success_count}/{len(results)}")
        print(f"Failed: {failed_count}/{len(results)}")


async def batch_convert_with_custom_output():
    """Convert PDFs with custom output directory"""

    pdf_files = [
        Path("input/document1.pdf"),
        Path("input/document2.pdf"),
    ]

    output_dir = Path("output/converted")
    output_dir.mkdir(parents=True, exist_ok=True)

    async with AdobePDFConverter() as converter:
        for pdf_file in pdf_files:
            # Generate custom output path
            output_file = output_dir / f"{pdf_file.stem}_converted.docx"

            print(f"Converting {pdf_file.name}...")

            try:
                result = await converter.convert_pdf_to_word(
                    pdf_file,
                    output_path=output_file,
                )
                print(f"  ✓ Saved to: {result}")

            except Exception as e:
                print(f"  ✗ Failed: {e}")


if __name__ == "__main__":
    print("Adobe Helper - Batch Conversion Example\n")

    # Choose one of the following:

    # Option 1: Sequential conversion (safer, respects rate limits)
    asyncio.run(batch_convert_sequential())

    # Option 2: Concurrent conversion (faster, but may hit quota quickly)
    # asyncio.run(batch_convert_concurrent())

    # Option 3: Custom output paths
    # asyncio.run(batch_convert_with_custom_output())
