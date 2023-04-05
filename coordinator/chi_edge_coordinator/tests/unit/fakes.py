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
