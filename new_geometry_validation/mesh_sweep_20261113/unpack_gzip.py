from pathlib import Path
import gzip
root=Path(__file__).resolve().parent
for source in root.rglob("*.gz"):
    target=source.with_suffix("")
    if target.exists():
        print("Skip existing",target)
        continue
    target.write_bytes(gzip.decompress(source.read_bytes()))
    print(target.relative_to(root))
