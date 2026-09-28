from store import INDEX_NAME, ensure_index

if __name__ == "__main__":
    ensure_index()
    print(f"index '{INDEX_NAME}' ready")
