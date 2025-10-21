def get_channel(hardware, channel_name):
    channel_workers = [w for w in hardware["workers"] if w["worker_type"] == "tunelo"]
    if not channel_workers:
        raise RuntimeError("Missing information for tunnel configuration")

    channels = hardware["properties"].get("channels", {})
    existing_channel = channels.get(channel_name, {}).copy()
    existing_channel.update(
        channel_workers[0]["state_details"].get("channels", {}).get(channel_name, {})
    )

    return existing_channel


def get_channel_patch(hardware, channel_name, pubkey):
    expected_channel = {"channel_type": "wireguard", "public_key": pubkey}

    channels = hardware["properties"].get("channels")
    if channels is None:
        # Corner case, no channels defined at all (Doni should really default this to
        # an empty obj better)
        return [
            {
                "op": "add",
                "path": "/properties/channels",
                "value": {channel_name: expected_channel},
            }
        ]

    existing_channel = channels.get(channel_name)
    if not existing_channel or existing_channel.get("public_key") != pubkey:
        return [
            {
                "op": "replace" if existing_channel else "add",
                "path": f"/properties/channels/{channel_name}",
                "value": expected_channel,
            }
        ]

    return []


def uuid_hex_to_dashed(uuid_hex: str):
    uuidlower = uuid_hex.lower()
    # Inventory service uses hyphenated UUIDs
    dashed_uuid = "-".join(
        [
            uuidlower[:8],
            uuidlower[8:12],
            uuidlower[12:16],
            uuidlower[16:20],
            uuidlower[20:],
        ]
    )

    return dashed_uuid
