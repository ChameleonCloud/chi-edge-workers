import os
from datetime import datetime, timezone

import balena as balena_sdk
import click
from rich.console import Console
from rich.table import Table

console = Console()


def time_ago(iso_str):
    if not iso_str:
        return "never"
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - dt
    days = delta.days
    if days >= 1:
        return f"{days}d ago"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"{hours}h ago"
    return f"{delta.seconds // 60}m ago"


@click.command()
@click.option("--token", default=os.getenv("BALENA_TOKEN"), metavar="TOKEN")
@click.option("--token-file", default="~/.balena/token", metavar="FILE")
@click.option("--fleet", default="chameleon/chi-edge-workers", metavar="NAME")
def main(token, token_file, fleet):
    """Show release and OS status for all devices in the fleet."""
    if not token:
        with open(os.path.expanduser(token_file)) as f:
            token = f.read().strip()

    client = balena_sdk.Balena()
    client.auth.login_with_token(token)

    app = client.models.application.get(fleet, {
        "$expand": {"should_be_running__release": {"$select": ["commit"]}}
    })
    fleet_pinned = ((app.get("should_be_running__release") or [{}])[0]).get("commit")

    latest_releases = client.models.release.get_all_by_application(fleet, {
        "$select": ["commit"],
        "$filter": {"is_final": True, "status": "success"},
        "$orderby": "created_at desc",
        "$top": 1,
    })
    latest = latest_releases[0]["commit"] if latest_releases else None

    devices = client.models.device.get_all_by_application(fleet, {
        "$select": ["device_name", "os_version", "is_online", "last_connectivity_event",
                    "is_running__release", "is_pinned_on__release", "is_of__device_type"],
        "$expand": {
            "is_running__release": {"$select": ["commit"]},
            "is_pinned_on__release": {"$select": ["commit"]},
            "is_of__device_type": {"$select": ["slug"]},
        },
    })

    def short(c):
        return c[:7] if c else "N/A"

    console.print(f"\nFleet: [bold]{fleet}[/bold]")
    console.print(f"  Latest release:       [bold]{short(latest)}[/bold]")
    console.print(f"  Fleet pinned release: [bold]{short(fleet_pinned)}[/bold]\n")

    table = Table(show_lines=False)
    table.add_column("Device Type", style="cyan")
    table.add_column("Device Name")
    table.add_column("Online")
    table.add_column("OS Version")
    table.add_column("Running")
    table.add_column("Pinned")

    rows = []
    for d in devices:
        device_type = (d.get("is_of__device_type") or [{}])[0].get("slug", "unknown")
        name = d.get("device_name", "unknown")
        online = d.get("is_online", False)
        last_seen = d.get("last_connectivity_event")
        os_version = (d.get("os_version") or "N/A").removeprefix("balenaOS ")
        running = (d.get("is_running__release") or [{}])[0].get("commit")
        pinned = (d.get("is_pinned_on__release") or [{}])[0].get("commit")
        rows.append((device_type, name, online, last_seen, os_version, running, pinned))

    for device_type, name, online, last_seen, os_version, running, pinned in sorted(rows, key=lambda x: (x[0], not x[2], x[1])):
        if online:
            online_str = "[green]yes[/green]"
        else:
            online_str = f"[red]no[/red] [dim]{time_ago(last_seen)}[/dim]"

        running_str = short(running)
        if running == latest:
            running_str = f"[green]{running_str}[/green]"
        elif running != fleet_pinned:
            running_str = f"[yellow]{running_str}[/yellow]"

        pinned_str = short(pinned) if pinned else "[dim]fleet[/dim]"

        table.add_row(device_type, name, online_str, os_version, running_str, pinned_str)

    console.print(table)


if __name__ == "__main__":
    main()
