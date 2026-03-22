FAKE_BALENA_SERVICE_NAME = "wireguard"
FAKE_BALENA_SERVICE_MISSING = "wireguard-foo"

# defined here: https://docs.balena.io/reference/supervisor/supervisor-api/#get-v2statestatus
FAKE_BALENA_STATE_STATUS = {
    "status": "success",
    "appState": "applied",
    "overallDownloadProgress": None,
    "containers": [
        {
            "status": "Running",
            "serviceName": FAKE_BALENA_SERVICE_NAME,
            "appId": 1032480,
            "imageId": 959262,
            "serviceId": 29396,
            "containerId": "be4a860e34ffca609866f8af3596e9ee7b869e1e0bb9f51406d0b120b0a81cdd",
            "createdAt": "2019-03-11T16:05:34.506Z",
        }
    ],
    "images": [
        {
            "name": "registry2.balena-cloud.com/v2/fbf67cf6574fb0f8da3c8998226fde9e@sha256:9e328a53813e3c2337393c63cfd6c2f5294872cf0d03dc9f74d02e66b9ca1221",
            "appId": 1032480,
            "serviceName": "main",
            "imageId": 959262,
            "dockerImageId": "sha256:2662fc0ca0c7dd0f549e87e224f454165f260ff54aac59308d2641d99ca95e58",
            "status": "Downloaded",
            "downloadProgress": None,
        }
    ],
    "release": "804281fb17e8291c542f9640814ef546",
}

FAKE_APP_CREDENTIAL = "foo:bar:baz"
FAKE_HARDWARE_UUID = "22-33-44-55"
FAKE_HARDWARE_PATCH = [
    {"op": "replace", "path": "/workers/0/state_details/foo", "value": "bar"}
]

FAKE_DEVICE_NAME = "iot-rpi4-0015"
FAKE_DEVICE_ID = "002f5d15-b7b1-4bd4-99a3-e17fb5f394c8"
FAKE_BLAZAR_DEVICES_RESPONSE = {
    "devices": [
        {"id": FAKE_DEVICE_ID, "name": FAKE_DEVICE_NAME, "device_type": "container"},
        {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "name": "other-device", "device_type": "container"},
    ]
}
FAKE_BLAZAR_ALLOCATIONS_RESPONSE = {
    "allocations": [
        {
            "resource_id": FAKE_DEVICE_ID,
            "reservations": [
                {
                    "id": "res-1",
                    "lease_id": "lease-1",
                    "start_date": "2026-03-20T17:00:00.000000",
                    "end_date": "2026-03-20T19:00:00.000000",
                }
            ],
        },
        {"resource_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "reservations": []},
    ]
}

FAKE_CHANNEL_NAME = "fake_channel"
FAKE_CHANNEL = {}
FAKE_HARDWARE = {
    "workers": [
        {
            "worker_type": "tunelo",
            "state_details": {},
        },
    ],
    "properties": {
        "channels": {
            FAKE_CHANNEL_NAME: {},
        },
    },
}
