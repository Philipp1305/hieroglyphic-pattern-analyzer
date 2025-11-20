from . import create_app

app = create_app()


def main() -> None:
    app.run(debug=True)


if __name__ == "__main__":
    main()
