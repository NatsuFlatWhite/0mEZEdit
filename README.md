# 0mEZEdit

Unpacks the 0m structure into clean, easy-to-read JSON so it can be viewed and edited, then repacks the modified JSON into a working 0m file.

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

## Validation

The editor validates the header, size fields, Adler-32 checksum, zlib stream, internal prefix, strings, item counts, and block structure before unpacking.
