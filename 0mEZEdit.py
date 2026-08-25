import argparse
import io
import json
import zlib
from dataclasses import dataclass, field
from pathlib import Path

MAGIC = b"\xAA\x27\x00\x00"
TAG = b"\x53\x01"
PREFIX = bytes.fromhex("AA477F04D51A000076F1AA270000")
LISTS = {"server", "channel"}
UNK = "_unk"
MAX_RAW = 16 * 1024 * 1024
ccNames = {
    0x2F: "cn", 0x5D: "hk", 0x6E: "jp", 0x76: "kr", 0xBF: "sg",
    0xD1: "th", 0xDB: "tw", 0xE0: "us", 0xF1: "zz",
}
ccByName = {name: code for code, name in ccNames.items()}

@dataclass
class Block:
    name: str
    data: dict
    children: list = field(default_factory=list)
    unk: int = 0

def cc(value):
    if isinstance(value, int):
        return value
    value = str(value).strip().lower()
    if value in ccByName:
        return ccByName[value]
    base = 16 if value.startswith("0x") or any(c in "abcdef" for c in value) else 10
    return int(value, base)
def num(stream):
    data = stream.read(4)
    if len(data) != 4:
        raise SystemExit
    return int.from_bytes(data, "little")
def text(stream):
    size = num(stream) * 2
    if size > len(stream.getbuffer()) - stream.tell():
        raise SystemExit
    try:
        return stream.read(size).decode("utf-16le")
    except UnicodeError:
        raise SystemExit
def writeText(value):
    value = "" if value is None else str(value)
    data = value.encode("utf-16le")
    return (len(data) // 2).to_bytes(4, "little") + data
def readVal(value):
    return {"true": True, "false": False}.get(value, value)

def readBlocks(raw):
    if len(raw) < len(PREFIX):
        raise SystemExit
    stream = io.BytesIO(raw)
    stream.seek(len(PREFIX))
    blocks = []
    while stream.tell() < len(raw):
        name = text(stream)
        unk = num(stream)
        count = num(stream)
        if not name or count > (len(raw) - stream.tell()) // 8:
            raise SystemExit
        data = {}
        for _ in range(count):
            key = text(stream).replace("\x00", "")
            value = text(stream).replace("\x00", "")
            if not key or key in data:
                raise SystemExit
            data[key] = readVal(value)
        blocks.append((name, data, unk, num(stream)))
    return blocks

def makeTree(flat):
    index = 0
    def node(depth=0):
        nonlocal index
        if index >= len(flat) or depth > 64:
            raise SystemExit
        name, data, unk, count = flat[index]
        index += 1
        if count > len(flat) - index:
            raise SystemExit
        return Block(name, data, [node(depth + 1) for _ in range(count)], unk)
    roots = []
    while index < len(flat):
        roots.append(node())
    return roots
def put(target, name, value, many=False):
    if name not in target:
        target[name] = [value] if many else value
    elif isinstance(target[name], list):
        target[name].append(value)
    else:
        target[name] = [target[name], value]
def toValue(block):
    result = dict(block.data)
    if block.unk:
        result[UNK] = block.unk
    for child in block.children:
        put(result, child.name, toValue(child), child.name in LISTS)
    return result

def toConfig(roots, code):
    result = {"cc": ccNames.get(code, f"0x{code:02X}")}
    if len(roots) == 1 and roots[0].name == "content":
        content = roots[0]
        result["content"] = dict(content.data)
        if content.unk:
            result["content"][UNK] = content.unk
        for child in content.children:
            put(result, child.name, toValue(child))
        return result
    for root in roots:
        put(result, root.name, toValue(root))
    return result

def split(value):
    data = {}
    children = []
    unk = value.get(UNK, 0)
    if isinstance(unk, bool) or not isinstance(unk, int) or not 0 <= unk <= 0xFFFFFFFF:
        raise SystemExit
    for name, item in value.items():
        if name == UNK:
            continue
        if isinstance(item, dict):
            children.append((name, item))
        elif isinstance(item, list) and all(isinstance(v, dict) for v in item):
            children.append((name, item))
        else:
            data[name] = item
    return data, children, unk
def makeBlocks(name, value):
    entries = value if isinstance(value, list) else [value]
    blocks = []
    for entry in entries:
        data, items, unk = split(entry)
        children = []
        for childName, childValue in items:
            children.extend(makeBlocks(childName, childValue))
        blocks.append(Block(name, data, children, unk))
    return blocks

def toTree(config):
    items = [(name, value) for name, value in config.items() if name != "cc"]
    if "content" not in config:
        roots = []
        for name, value in items:
            roots.extend(makeBlocks(name, value))
        return roots
    data, nested, unk = split(config["content"])
    children = []
    for name, value in nested:
        children.extend(makeBlocks(name, value))
    legacy = None
    serverlist = config.get("serverlist")
    if isinstance(serverlist, dict) and "server" in config and "server" not in serverlist:
        legacy = dict(serverlist)
        legacy["server"] = config["server"]
    for name, value in items:
        if name == "content" or legacy is not None and name == "server":
            continue
        if legacy is not None and name == "serverlist":
            value = legacy
        children.extend(makeBlocks(name, value))
    return [Block("content", data, children, unk)]

def build(prefix, roots):
    raw = bytearray(prefix)
    def write(block):
        raw.extend(writeText(block.name))
        raw.extend(block.unk.to_bytes(4, "little"))
        raw.extend(len(block.data).to_bytes(4, "little"))
        for key, value in block.data.items():
            raw.extend(writeText(key))
            if isinstance(value, bool):
                value = "true" if value else "false"
            raw.extend(writeText(value))
        raw.extend(len(block.children).to_bytes(4, "little"))
        for child in block.children:
            write(child)
    for root in roots:
        write(root)
    return bytes(raw)

def unpack(path, output="Raycity.json"):
    data = Path(path).read_bytes()
    header = data[:18]
    if (len(header) != 18 or header[:4] != MAGIC or header[8:10] != TAG
            or int.from_bytes(header[4:8], "little") != len(data) - 8):
        raise SystemExit
    rawSize = int.from_bytes(header[14:18], "little")
    if not len(PREFIX) <= rawSize <= MAX_RAW:
        raise SystemExit
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(data[18:], rawSize + 1)
    except zlib.error:
        raise SystemExit
    if (not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
            or len(raw) != rawSize
            or zlib.adler32(raw, 0) & 0xFFFFFFFF != int.from_bytes(header[10:14], "little")
            or raw[:8] != PREFIX[:8] or raw[9:len(PREFIX)] != PREFIX[9:]):
        raise SystemExit
    config = toConfig(makeTree(readBlocks(raw)), raw[8])
    Path(output).write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
def pack(path, output="Raycity.0m"):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    prefix = bytearray(PREFIX)
    if config.get("cc") is not None:
        prefix[8] = cc(config["cc"])
    raw = build(prefix, toTree(config))
    packed = zlib.compress(raw, zlib.Z_BEST_COMPRESSION)
    header = MAGIC + (len(packed) + 10).to_bytes(4, "little") + TAG
    header += (zlib.adler32(raw, 0) & 0xFFFFFFFF).to_bytes(4, "little")
    header += len(raw).to_bytes(4, "little")
    Path(output).write_bytes(header + packed)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    path = parser.parse_args().filename
    if Path(path).suffix.lower() == ".json":
        pack(path)
    else:
        unpack(path)

if __name__ == "__main__":
    main()
