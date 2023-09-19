from flask import Flask, render_template, redirect, url_for, request, session
from flask_socketio import SocketIO, join_room, leave_room, emit
import random
import string
from datetime import datetime
from markupsafe import escape


app = Flask(__name__)
app.config["SECRET_KEY"] = "ss"

socketio = SocketIO(app)

existing_rooms = {}
MAX_MESSAGE_LENGTH = 4000


def get_current_datetime():
    return datetime.now().strftime("%d/%m/%Y, %H:%M:%S")


def generate_room_code(length):
    while new_room_code := ''.join(random.choices(string.ascii_uppercase, k=length)):
        if new_room_code not in existing_rooms:
            existing_rooms[new_room_code] = []
            return new_room_code


@app.route("/", methods=["GET", "POST"])
def index():
    session.clear()
    if request.method == "POST":
        name = str(escape(request.form["name"])).upper().strip()
        code = str(escape(request.form["code"].upper())).strip()
        join = escape(request.form.get("join", False))
        create = escape(request.form.get("create", False))

        if not name:
            return render_template("index.html", error="Name is required", name=name, code=code)

        if join != "False":
            if not code:
                return render_template("index.html", error="Code is required", name=name, code=code)
            elif code not in existing_rooms:
                return render_template("index.html", error="Room does not exist", name=name, code=code)

        room = code

        if create != "False":
            room = generate_room_code(4)
            existing_rooms[room] = {
                "members": [],
                "num_members": 0,
                "messages": [],
            }

        if name in existing_rooms[room]["members"]:
            return render_template("index.html", error="Name already exists in room", name=name, code=code)

        session["room"] = room
        session["name"] = name

        return redirect(url_for("chat_room"))
    return render_template("index.html")


@app.route("/chat")
def chat_room():
    room_code = session.get("room")
    # Make sure user can only access chat if they have gone through the index page
    if room_code is None or session.get("name") is None or room_code not in existing_rooms:
        return redirect(url_for("index"))
    return render_template("chat-room.html", room_code=room_code, messages=existing_rooms[room_code]["messages"], member_names=existing_rooms[room_code]["members"])


@socketio.on("connect")
def on_connect():
    room = session.get("room")
    name = session.get("name")

    if name is None or room is None:
        return

    if room not in existing_rooms:
        return

    join_room(room)
    existing_rooms[room]["members"].append(name)
    existing_rooms[room]["num_members"] += 1
    emit("userConnected", {"name": name, "message": "has entered the room",
         "dateTime": get_current_datetime()}, room=room)


@socketio.on("messageSent")
def on_message(data):
    room = session.get("room")
    name = session.get("name")

    if room not in existing_rooms:
        return

    content = {
        "name": name,
        "message": str(escape(data["message"].strip()[:MAX_MESSAGE_LENGTH])),
        "dateTime": str(escape(data["dateTime"])),
    }

    # When messageSent event is received by the server, emit messageReceived event to all clients in the room
    emit("messageReceived", content, room=room, include_self=False)
    existing_rooms[room]["messages"].append(content)
    print(existing_rooms)


@socketio.on("disconnect")
def on_disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in existing_rooms:
        existing_rooms[room]["num_members"] -= 1
        existing_rooms[room]["members"].remove(name)

        if existing_rooms[room]["num_members"] == 0:
            del existing_rooms[room]

    emit("userDisconnected", {"name": name, "message": "has left the room",
         "dateTime": get_current_datetime(), }, room=room)


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
