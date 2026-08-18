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
        """Queue a face change and return immediately with acceptance plus an event id."""
        return client.submit_event("set_face", {"name": name})

    @mcp.tool()
    def get_clock() -> dict:
        """Get the periodic clock overlay settings and current visibility state."""
        return client.clock()

    @mcp.tool()
    def set_clock_enabled(enabled: bool) -> dict:
        """Queue a clock overlay change and return immediately with acceptance plus an event id."""
        return client.submit_event("set_clock_enabled", {"enabled": enabled})

    @mcp.tool()
    def reload_code() -> dict:
        """Queue a MicroPython soft reset request and return immediately with acceptance plus an event id."""
        return client.submit_event("reload_code", {})

    @mcp.tool()
    def submit_event(type: str, arguments: dict | None = None) -> dict:
        """Queue an event and return immediately with acceptance plus an event id."""
        return client.submit_event(type, arguments)

    @mcp.tool()
    def submit_events(events: list[dict]) -> dict:
        """Queue multiple events and return immediately with acceptance plus event ids."""
        return client.submit_events(events)

    @mcp.tool()
    def get_event_status(event_id: str) -> dict:
        """Get queued/running/completed/failed status for a previously submitted event."""
        return client.event_status(event_id)

    @mcp.tool()
    def led_on(r: int, g: int, b: int, brightness: float = 1.0) -> dict:
        """Queue an LED-on change and return immediately with acceptance plus an event id."""
        return client.submit_event("led_on", {"r": r, "g": g, "b": b, "brightness": brightness})

    @mcp.tool()
    def led_off() -> dict:
        """Queue an LED-off change and return immediately with acceptance plus an event id."""
        return client.submit_event("led_off", {})

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
