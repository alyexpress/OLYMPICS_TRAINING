from flask import Flask, render_template, request, redirect
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from data import db_session
from data.users import User

from scripts.utils import hashed
from scripts.rooms import Rooms

from config import *

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins='*')
db_session.global_init(DATABASE)
login_manager = LoginManager()
login_manager.init_app(app)

rooms = Rooms()


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        _login = request.form.get("login")
        password = hashed(request.form.get("password"))
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.login == _login).first()
        response = {"login": [_login, ""], "password": ["", ""]}
        if user is None: response["login"] = ["", "Такой логин не зарегистрирован!"]
        elif user.password != password: response["password"][1] = "Неверный пароль!"
        if any(map(lambda x: x[1], response.values())):
            return render_template("login.html", error=response)
        login_user(user, remember=True)
        return redirect("/")
    elif request.method == "GET":
        return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        _login = request.form.get("login")
        password = request.form.get("password")
        check = request.form.get("check")
        response = {"login": [_login, ""],
            "password": ["", ""], "check": ["", ""]}
        db_sess = db_session.create_session()
        if not 3 < len(_login) <= 20: response["login"][1] = \
            "Логин должен быть от 4 до 20 символов"
        elif db_sess.query(User).filter(User.login == _login).first():
            response["login"][1] = "Такой логин уже занят!"
        if not 3 < len(password) <= 20: response["password"][1] = \
            "Пароль должен быть от 4 до 20 символов"
        elif password != check: response["check"][1] = \
            "Пароли должны совпадать!"
        else: response["password"][0] = response["check"][0] = password
        if any(map(lambda x: x[1], response.values())):
            return render_template("signup.html", error=response)
        user = User(login=_login, password=hashed(password))
        db_sess.add(user)
        db_sess.commit()
        login_user(user, remember=True)
        return redirect("/")
    elif request.method == "GET":
        return render_template("signup.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/find/<difficult>")
@login_required
def find(difficult):
    if difficult not in "simple medium hard".split():
        return redirect("/")
    return render_template("find.html")


@app.route("/battle/<int:number>")
@login_required
def battle(number):
    if not rooms.check(number, current_user.id):
        return redirect("/")
    return render_template("battle.html")


@socketio.on("join")
def join(difficult):
    join_room(current_user.id)
    response = rooms.join(current_user.id, difficult)
    print("Join:", current_user.id, difficult)
    if response is not None:
        other, number = response
        emit("response", number, room=other)
        emit("response", number, room=current_user.id)
        print("BATTLE:", number)


@socketio.on("disconnect")
def disconnect():
    leave_room(current_user.id)
    rooms.leave(current_user.id)
    print("Disconnect", current_user.id)




if __name__ == "__main__":
    # app.run(host=HOST, port=PORT, debug=DEBUG)
    # print("Link: http://127.0.0.1:8080/")
    socketio.run(app, host=HOST, port=PORT, debug=DEBUG)
