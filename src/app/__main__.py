from . import create_app, socketio

app = create_app()


def main() -> None:
    socketio.run(app, debug=True, port=5001)


if __name__ == "__main__":
    main()
