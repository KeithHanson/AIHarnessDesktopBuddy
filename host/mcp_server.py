import argparse
from api_client import BuddyApiClient
from mcp.server.fastmcp import FastMCP


def build_server(device_url: str):
    client = BuddyApiClient(device_url)
    mcp = FastMCP("AIHarnessDesktopBuddy")

    @mcp.tool()
    def list_faces() -> dict:
        """List available faces and when each should be used."""
        return client.faces()

    @mcp.tool()
    def set_face(name: str) -> dict:
        """Set the current OLED face."""
        return client.set_face(name)

    @mcp.tool()
    def led_on(r: int, g: int, b: int, brightness: float = 1.0) -> dict:
        """Turn on the device LED with RGB color and brightness from 0.0 to 1.0."""
        return client.led_on(r, g, b, brightness)

    @mcp.tool()
    def led_off() -> dict:
        """Turn off the device LED."""
        return client.led_off()

    @mcp.tool()
    def get_state() -> dict:
        """Get the current face and LED state."""
        return client.state()

    return mcp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-url", required=True, help="Example: http://192.168.1.50:8080")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "streamable-http"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    mcp = build_server(args.device_url)
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
