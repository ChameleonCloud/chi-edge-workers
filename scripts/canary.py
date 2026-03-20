from functools import wraps
import os

import balena
import click
from rich.console import Console
from rich.table import Table

RELEASE_TRACK_TAG = "release_track"
BETA_RELEASE_TRACK = "beta"

console = Console()


@click.group("release")
def main(token: str = None):
    """Manage canary releases to the CHI@Edge fleet on Balena.

    New application releases can be set as "drafts" in Balena, and are not automatically
    deployed to all devices in this case. This tool enables you to promote such releases
    to a subset of devices as a canary deployment.
    """
    pass


def _balena_client(token):
    client = balena.Balena()
    client.auth.login_with_token(token)
    return client


def _canary_devices_for_fleet(balena_client: "balena.Balena", fleet: str):
    fleet_model = balena_client.models.application.get(fleet)
    device_tags = balena_client.models.device.tags.get_all_by_application(
        fleet_model["id"]
    )

    device_map = {
        device["id"]: device
        for device in balena_client.models.device.get_all_by_application(
            fleet_model["id"],
            {"$expand": {"should_be_running__release": {"$select": ["id", "commit"]}}},
        )
    }
    beta_device_ids = [
        tag["device"]["__id"]
        for tag in device_tags
        if tag["tag_key"] == RELEASE_TRACK_TAG and tag["value"] == BETA_RELEASE_TRACK
    ]

    return [
        device_map.get(device_id)
        for device_id in beta_device_ids
        if device_id in device_map
    ]


def _find_device(balena_client: "balena.Balena", device_name: str):
    matching = balena_client.models.device.get_by_name(device_name)
    if not matching:
        raise click.ClickException(f"No devices with name '{device_name}'")
    return matching[0]


def _current_canary_release(balena_client: "balena.Balena", fleet: str):
    canary_devices = _canary_devices_for_fleet(balena_client, fleet)
    if not canary_devices:
        return None
    pinned = canary_devices[0].get("should_be_running__release") or []
    if not pinned:
        return None
    return balena_client.models.release.get(pinned[0]["id"])


def _common_options(func):
    @wraps(func)
    @click.option(
        "--token",
        metavar="TOKEN",
        default=os.getenv("BALENA_TOKEN"),
        help="Balena API token",
    )
    @click.option(
        "--token-file",
        metavar="FILE",
        default="~/.balena/token",
        help="Path to file containing Balena API token",
    )
    @click.option(
        "--fleet",
        metavar="NAME",
        default="chameleon/chi-edge-workers",
        help="The name of the Balena fleet to operate on",
    )
    def wrapper(*args, token: str = None, token_file: str = None, **kwargs):
        if not (token or token_file):
            raise click.UsageError("Either a token or token file must be specified")
        if not token:
            with open(os.path.expanduser(token_file), "r") as f:
                token = f.read()
        kwargs["balena_client"] = _balena_client(token)
        return func(*args, **kwargs)

    return wrapper


@main.command()
@click.argument("release_id")
@_common_options
def deploy(release_id: str, balena_client: "balena.Balena", fleet: str = None):
    """Deploy a draft release as a canary to a subset of devices in the fleet."""
    release = balena_client.models.release.get(int(release_id))
    commit = release["commit"]
    for device in _canary_devices_for_fleet(balena_client, fleet):
        balena_client.models.device.pin_to_release(device["uuid"], commit)
        console.print(f"Added {device['device_name']} to canary pool for {commit}")


@main.command()
@_common_options
def rollback(balena_client: "balena.Balena", fleet: str = None):
    """Roll back a canary release to the latest stable version."""
    for device in _canary_devices_for_fleet(balena_client, fleet):
        device_uuid, device_name = device["uuid"], device["device_name"]
        if not balena_client.models.device.is_tracking_application_release(device_uuid):
            balena_client.models.device.track_application_release(device_uuid)
            console.print(f"Removed {device_name} from canary set")
        else:
            console.print(f"Device {device_name} already rolled back")


@main.command()
@_common_options
def show(balena_client: "balena.Balena", fleet: str = None):
    """Show information about the current release deployed to the canary pool."""
    release_map = {}

    table = Table()
    table.add_column("Device")
    table.add_column("Release")
    for device in _canary_devices_for_fleet(balena_client, fleet):
        pinned = device.get("should_be_running__release") or []
        if pinned:
            release_id = pinned[0]["id"]
            if release_id not in release_map:
                release_map[release_id] = balena_client.models.release.get(release_id)
            release_commit = release_map[release_id]["commit"]
        else:
            release_commit = None
        table.add_row(device["device_name"], release_commit)

    console.print(table)


@main.command()
@click.argument("device_name")
@_common_options
def add_device(
    balena_client: "balena.Balena", fleet: str = None, device_name: str = None
):
    """Add a device to the canary pool.

    This will immediately apply the canary release to this device, if one is deployed.
    """
    canary_release = _current_canary_release(balena_client, fleet)

    device = _find_device(balena_client, device_name)
    balena_client.models.device.tags.set(
        device["uuid"], RELEASE_TRACK_TAG, BETA_RELEASE_TRACK
    )
    console.print(f"Device {device_name} added to canary pool")

    # Also apply the latest canary build... if any
    if canary_release:
        release_id = canary_release["commit"]
        balena_client.models.device.pin_to_release(device["uuid"], release_id)
        console.print(f"Applying existing canary release {release_id} to {device_name}")


@main.command()
@click.argument("device_name")
@_common_options
def remove_device(
    balena_client: "balena.Balena", fleet: str = None, device_name: str = None
):
    """Remove a device from the canary pool.

    This will also reset the device to track the latest release.
    """
    device = _find_device(balena_client, device_name)
    balena_client.models.device.tags.set(device["uuid"], RELEASE_TRACK_TAG, "")
    balena_client.models.device.track_application_release(device["uuid"])
    console.print(f"Removed {device_name} from canary pool")


if __name__ == "__main__":
    main()
