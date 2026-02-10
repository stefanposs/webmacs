"""Controller entry point."""

import asyncio
import sys

from webmacs_controller.app import Application


def main() -> None:
    """Run the WebMACS IoT Controller."""
    try:
        app = Application()
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\nController stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
