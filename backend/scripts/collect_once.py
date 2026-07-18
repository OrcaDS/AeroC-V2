from app.runtime.collection_runner import CollectionRunner


def main():
    CollectionRunner().run_once()
    print("Collection completed")


if __name__ == "__main__":
    main()
