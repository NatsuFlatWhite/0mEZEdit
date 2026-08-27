# 0mEZEdit

Unpacks the 0m structure into clean, easy-to-read JSON so it can be viewed and edited, then repacks the modified JSON into a working 0m file.

## Runtime Behavior

The 0m file is used as the client's initial configuration.

The `cc` value is loaded by the client and sent during the initial connection, where it is checked against the GameServer's configured country code. If the values do not match, the connection is rejected.

Content settings from the 0m file are used during client initialization. After a successful FirstPacket exchange, the client's active content settings are replaced by the content settings provided by the server.

The country code is also used by regional feature checks. The client generally contains the same functionality across regions, but the enabled state of those features can differ depending on the country code and server-side settings.

## Country Code

Set the country with the `cc` field:

```json
{
  "cc": "kr"
}
```

| Name | Code   | Region        |
| ---- | ------ | ------------- |
| `cn` | `0x2F` | China         |
| `hk` | `0x5D` | Hong Kong     |
| `jp` | `0x6E` | Japan         |
| `kr` | `0x76` | South Korea   |
| `sg` | `0xBF` | Singapore     |
| `th` | `0xD1` | Thailand      |
| `tw` | `0xDB` | Taiwan        |
| `us` | `0xE0` | United States |
| `zz` | `0xF1` | Global        |

Country aliases, decimal integers, and hexadecimal strings such as `"0x76"` are supported.

## Content

Fields inside `content` can be edited directly in the generated JSON:

```json
{
  "content": {
    "grade": "true",
    "CannotMoveToTownUntilUserLevel5": "false"
  }
}
```

Values are preserved and written back into the original block structure when repacking.

## Server

Server and channel entries can be edited, added, or removed:

```json
{
  "server": {
    "name": "Server",
    "channel": [
      {
        "name": "Channel-1",
        "ip": "127.0.0.1",
        "port": "2180"
      }
    ]
  }
}
```

Multiple `server` and `channel` blocks are represented as JSON arrays.

Depending on the original 0m file, servers may also be nested inside blocks such as `serverlist`. The original block structure is preserved when repacking.

## Validation

The editor validates the header, size fields, Adler-32 checksum, zlib stream, internal prefix, strings, item counts, and block structure before unpacking.
