from flask import Flask, render_template, redirect, url_for, request, session
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from markupsafe import escape
import random
import string
import uuid


app = Flask(__name__)
app.config["SECRET_KEY"] = "ss"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"

db = SQLAlchemy(app)
socketio = SocketIO(app)

MAX_MESSAGE_LENGTH = 4000


# Database models

class Room(db.Model):
    # Represents a chat room
    code = db.Column(db.String(4), primary_key=True)
    members = db.relationship('Member', backref='room', lazy=True)
    messages = db.relationship('Message', backref='room', lazy=True)

class Message(db.Model):
    # Represents a message in a chat room
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_code = db.Column(db.String(4), db.ForeignKey('room.code'), nullable=False)
    message = db.Column(db.String(4000), nullable=False)
    sender_name = db.Column(db.String(50), nullable=False)
    sender_id = db.Column(db.String(36), db.ForeignKey('member.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Member(db.Model):
    # Represents a member in a chat room
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_code = db.Column(db.String(4), db.ForeignKey('room.code'), nullable=False)
    name = db.Column(db.String(50), nullable=False)



with app.app_context():
    # Delete all tables and create new ones when server is started
    # Data only needs to exist while chats exist and is not persistent
    # If server were to crash, all data would have stayed if tables were not dropped as data was only deleted when all members left a room
    db.drop_all()
    db.create_all()


def get_current_utc():
    return datetime.now(timezone.utc)


def generate_room_code(length):
    while new_room_code := ''.join(random.choices(string.ascii_uppercase, k=length)):
        if Room.query.filter_by(code=new_room_code).first() is None:
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
            elif Room.query.filter_by(code=code).first() is None:
                return render_template("index.html", error="Room does not exist", name=name, code=code)

        room = Room.query.filter_by(
            code=code).first() if join != "False" else None

        if room is not None:
            if Member.query.filter_by(room_code=room.code, name=name).first() is not None:
                return render_template("index.html", error="Name already exists in room", name=name, code=code)

        if create != "False":
            new_room_code = generate_room_code(4)
            db.session.add(Room(code=new_room_code))
            db.session.commit()

        session["room"] = room.code if join != "False" else new_room_code
        session["name"] = name

        return redirect(url_for("chat_room"))
    return render_template("index.html")


@app.route("/chat")
def chat_room():
    room_code = session.get("room")
    name = session.get("name")
    # Make sure user can only access chat if they have gone through the index page
    if room_code is None or name is None:
        return redirect(url_for("index"))

    room = Room.query.filter_by(code=room_code).first()
    if room is None:
        return redirect(url_for("index"))

    return render_template("chat-room.html", room_code=room_code, messages=room.messages, member_names=[member.name for member in room.members])


@socketio.on("connect")
def on_connect():
    room_code = session.get("room")
    name = session.get("name")

    if name is None or room_code is None:
        return

    room = Room.query.filter_by(code=room_code).first()

    if room is None:
        return

    join_room(room_code)
    new_member = Member(name=name, room_code=room.code)
    db.session.add(new_member)
    db.session.commit()

    # Connect time converted to iso format as datetime object cannot be JSON serialized
    connect_time = get_current_utc().isoformat()

    emit("userConnected", {"id": new_member.id, "name": name, "message": "has entered the room",
         "timestamp": connect_time}, room=room_code)


@socketio.on("messageSent")
def on_message(data):
    room_code = session.get("room")
    name = session.get("name")

    room = Room.query.filter_by(code=room_code).first()

    if room is None:
        return

    sender = Member.query.filter_by(room_code=room_code, name=name).first()
    message = str(escape(data["message"].strip()[:MAX_MESSAGE_LENGTH]))

    content = Message(room_code=sender.room_code, message=message, sender_name=sender.name, sender_id=sender.id)
    db.session.add(content)
    db.session.commit()

    iso_timestamp = content.timestamp.isoformat()

    # When messageSent event is received by the server, emit messageReceived event to all clients in the room
    emit("messageReceived", {"name": name, "message": content.message,
         "timestamp": iso_timestamp}, room=room_code, include_self=False)


@socketio.on("disconnect")
def on_disconnect():
    room_code = session.get("room")
    name = session.get("name")

    room = Room.query.filter_by(code=room_code).first()

    if room is not None:
        leave_room(room_code)

        member = Member.query.filter_by(
            room_code=room_code, name=name).first()

        if member is not None:
            db.session.delete(member)
            db.session.commit()

            # Disconnect time converted to iso format as datetime object cannot be JSON serialized
            disconnect_time = get_current_utc().isoformat()

            emit("userDisconnected", {"name": name, "message": "has left the room",
                                      "timestamp": disconnect_time}, room=room_code)

            if len(room.members) == 0:
                # Delete all messages for the room
                Message.query.filter_by(room_code=room_code).delete()
                db.session.commit()

                # Delete the room
                db.session.delete(room)
                db.session.commit()

                session.clear()


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
