"""
Multi-tenant conversion example

This example demonstrates how different sessions automatically use
different tenant IDs extracted from their IMS authentication tokens.
"""

import asyncio
import logging
from pathlib import Path

from adobe import AdobePDFConverter

# Configure logging to see tenant IDs in action
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def convert_with_new_session(pdf_file: Path, session_num: int):
    """
    Convert a PDF using a fresh session

    Each new session will get its own tenant ID from Adobe IMS
    """
    print(f"\n{'='*60}")
    print(f"Session {session_num}: Creating fresh converter instance")
    print(f"{'='*60}")

    async with AdobePDFConverter(
        bypass_local_limits=True,
        track_usage=False,
    ) as converter:
        # The session will automatically get a tenant ID from IMS
        session_stats = converter.get_session_stats()
        if session_stats:
            print(f"Session {session_num} initialized")

        # Get the tenant ID
        if isinstance(converter.session_manager, type(converter.session_manager)):
            tenant_id = getattr(converter.session_manager, "tenant_id", None)
            if tenant_id:
                print(f"✓ Session {session_num} using tenant ID: {tenant_id}")
            else:
                print(f"⚠ Session {session_num} has no tenant ID yet")

        print(f"\nConverting {pdf_file.name}...")

        try:
            output_file = await converter.convert_pdf_to_word(pdf_file)
            print(f"✓ Session {session_num} conversion complete: {output_file}")
            return output_file
        except Exception as e:
            print(f"✗ Session {session_num} conversion failed: {e}")
            return None


async def main():
    """
    Demonstrate multi-tenant support by creating multiple sessions

    Each session will:
    1. Get a fresh IMS access token
    2. Extract its tenant ID
    3. Use tenant-specific API endpoints
    """
    pdf_file = Path("document.pdf")

    if not pdf_file.exists():
        print(f"Error: {pdf_file} not found")
        print("Please create a test PDF file first")
        return

    print("\nDemonstrating Multi-Tenant Support")
    print("=" * 60)
    print("Each session will extract its own tenant ID from the IMS token")
    print("and use tenant-specific API endpoints")
    print("=" * 60)

    # Session 1
    result1 = await convert_with_new_session(pdf_file, session_num=1)

    # Session 2 (if you want to test multiple sessions)
    # Uncomment to create a second session with potentially different tenant
    # result2 = await convert_with_new_session(pdf_file, session_num=2)

    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")
    if result1:
        print(f"✓ Session 1: Success")
    else:
        print(f"✗ Session 1: Failed")

    print("\nNote: Each session automatically:")
    print("  1. Fetches a guest access token from Adobe IMS")
    print("  2. Extracts the tenant ID from the token")
    print("  3. Builds tenant-specific API endpoint URLs")
    print("  4. Uses those endpoints for upload/convert/download")


async def show_tenant_extraction():
    """
    Show how tenant ID extraction works
    """
    print("\nTenant ID Extraction Process:")
    print("=" * 60)

    converter = AdobePDFConverter()
    await converter.initialize()

    from adobe.session_cycling import AnonymousSessionManager

    if isinstance(converter.session_manager, AnonymousSessionManager):
        session_mgr = await converter.session_manager.get_session()
        session_info = await session_mgr.ensure_access_token()

        print(f"Access Token: {session_info.access_token[:30]}..." if session_info.access_token else "None")
        print(f"Tenant ID: {session_info.tenant_id}")

        if session_info.tenant_id:
            from adobe.urls import get_endpoints_for_session

            endpoints = get_endpoints_for_session(tenant_id=session_info.tenant_id)
            print(f"\nTenant-specific endpoints:")
            for name, url in endpoints.items():
                print(f"  {name:12} → {url}")
        else:
            print("\n⚠ No tenant ID extracted from token")

    await converter.close()


if __name__ == "__main__":
    # Run the main conversion demo
    asyncio.run(main())

    # Uncomment to see tenant extraction details
    # asyncio.run(show_tenant_extraction())
