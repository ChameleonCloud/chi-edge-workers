import os
import requests


def call_supervisor(path, method="get", json=None):
    # If the Balena device name does not match, update it from hardware via
    # calling the Balena supervisor.
    supervisor_api_url = os.getenv("BALENA_SUPERVISOR_ADDRESS")
    supervisor_api_key = os.getenv("BALENA_SUPERVISOR_API_KEY")
    if not (supervisor_api_url and supervisor_api_key):
        raise RuntimeError("Missing Balena supervisor configuration")

    res = requests.request(
        method, f"{supervisor_api_url}{path}?apikey={supervisor_api_key}", json=json
    )
    res.raise_for_status()
    try:
        data = res.json()
    except ValueError:
        print("Supervisor Response content is not valid JSON")
    else:
        return data


def sync_device_name(hardware, balena_device_name):
    hardware_name = hardware["name"]
    if hardware_name == balena_device_name:
        return

    if os.getenv("BALENA_SUPERVISOR_OVERRIDE_LOCK") != "1":
        print("Not updating hostname because update lock is in place")
        return
    print(f"Updating device hostname to {hardware_name}")
    call_supervisor(
        "/v1/device/host-config",
        method="patch",
        json={
            "network": {
                "hostname": hardware["name"],
            },
        },
    )


def find_k3s_services() -> list[str]:
    """List all services, find ones starting with k3s."""
    status = call_supervisor("/v2/state/status")

    k3s_services = [
        c["serviceName"]
        for c in status["containers"]
        if c["serviceName"].startswith("k3s")
    ]
    return k3s_services


def restart_service(service_name):
    status = call_supervisor("/v2/state/status")
    running_service = next(
        iter(
            c
            for c in status["containers"]
            if c["status"] == "Running" and c["serviceName"] == service_name
        ),
        None,
    )
    # Only restart it if it was not explicitly stopped or is updating
    if running_service:
        print(f"Restarting {service_name} service")
        call_supervisor(
            f"/v2/applications/{running_service['appId']}/restart-service",
            method="post",
            json={
                "serviceName": service_name,
            },
        )
