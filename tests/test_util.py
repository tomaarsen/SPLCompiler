def open_file(filename: str) -> str:
    with open(filename, "r", encoding="utf8") as f:
        return f.read()
