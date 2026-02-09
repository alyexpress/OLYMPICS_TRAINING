from flask import Flask, render_template, request, redirect, abort
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from json import load
from requests import get
from bs4 import BeautifulSoup as bs

from os.path import isfile
from sys import argv

from data import db_session
from data.users import User
from data.tasks import Task
from data.actions import Action

from scripts.utils import hashed, progress, elo
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
    if current_user.is_authenticated:
        date = current_user.created_date.strftime("%d.%m.%Y")
        db_sess = db_session.create_session()
        __progress = db_sess.query(Action).filter(Action.user_id == current_user.id)
        _progress = list(map(lambda x: int((x.status - 1.5) * 2), __progress))
        absolute, resolve = len(_progress), _progress.count(1)
        percent = round((resolve / absolute) * 100) if absolute else 0
        progress(_progress, current_user.id)
        resolved_tasks = set(map(lambda x: x.task_id, __progress.filter(Action.status == 2)))
        _tasks, difficult = [], ["simple", "medium", "hard"][_progress[-5:].count(1) // 2]
        for _task in db_sess.query(Task).filter(Task.difficult == difficult)[::-1]:
            if _task.id in resolved_tasks: continue
            actions = db_sess.query(Action).filter(Action.task_id == _task.id)
            _percent = len(actions.filter(Action.status == 2).all())
            _percent /= len(actions.all()) if len(actions.all()) != 0 else 1
            _tasks.append({
                "url": f"/tasks/{_task.id}",
                "title": _task.title,
                "subject": _task.subject,
                "difficult": {"simple": "Лёгкая", "medium": "Средняя",
                              "hard": "Сложная"}[_task.difficult],
                "percent": round(_percent * 100) })
            if len(_tasks) == 5: break
        _tasks.sort(key=lambda x: -x["percent"])
        return render_template("index.html", date=date, percent=percent,
                               absolute=absolute, resolve=resolve, tasks=_tasks)
    db_sess, _tasks = db_session.create_session(), []
    for _task in db_sess.query(Task).all()[::-1]:
        actions = db_sess.query(Action).filter(Action.task_id == _task.id)
        _percent = len(actions.filter(Action.status == 2).all())
        _percent /= len(actions.all()) if len(actions.all()) != 0 else 1
        _tasks.append({
            "url": f"/tasks/{_task.id}",
            "title": _task.title,
            "subject": _task.subject,
            "difficult": {"simple": "Лёгкая", "medium": "Средняя",
                          "hard": "Сложная"}[_task.difficult],
            "percent": round(_percent * 100)})
        if len(_tasks) == 5: break
    _tasks.sort(key=lambda x: -x["percent"])
    return render_template("index.html", tasks=_tasks)


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

@app.route("/tasks")
def tasks():
    db_sess = db_session.create_session()
    t, _tasks = db_sess.query(Task).all(), []
    subjects = set(map(lambda x: x.subject, t))
    for _task in t:
        actions = db_sess.query(Action).filter(Action.task_id == _task.id)
        percent = len(actions.filter(Action.status == 2).all())
        percent /= len(actions.all()) if len(actions.all()) != 0 else 1
        _tasks.append({
            "url": f"/tasks/{_task.id}",
            "title": _task.title,
            "subject": _task.subject,
            "difficult": {"simple": "Лёгкая", "medium": "Средняя",
                          "hard": "Сложная"}[_task.difficult],
            "percent": round(percent * 100)
        })
    return render_template("tasks.html", tasks=_tasks[::-1],
                           subjects=sorted(list(subjects)))

@app.route("/tasks/<int:number>", methods=["GET", "POST"])
def task(number):
    db_sess = db_session.create_session()
    _task = db_sess.query(Task).filter(Task.id == number).first()
    if _task is None: return redirect("/")
    _tasks = db_sess.query(Task).filter(Task.subject == _task.subject,
                                        Task.id != _task.id).all()[::-1]
    resolved = (set(map(lambda x: x.task_id, db_sess.query(Action).filter(
        Action.user_id == current_user.id, Action.status == 2)))
                if current_user.is_authenticated else [])
    _tasks = list(filter(lambda x: x.id not in resolved, _tasks))
    if _task.difficult == "simple": sort = ["simple", "medium", "hard"]
    elif _task.difficult == "medium": sort = ["medium", "simple", "hard"]
    elif _task.difficult == "hard": sort = ["hard", "medium", "simple"]
    _tasks.sort(key=lambda t: sort.index(t.difficult))
    if request.method == "POST":
        answer = request.form.get("answer").replace(".", ",")
        correct = answer == _task.answer
        if current_user.is_authenticated:
            db_sess.add(Action(user_id=current_user.id,
                task_id=number, status= 2 if correct else 1))
            db_sess.commit()
        return render_template("task.html", task=_task, tasks=_tasks,
                               correct=correct, answer=answer)
    if request.method == "GET":
        return render_template("task.html", task=_task, tasks=_tasks)

@app.route("/add-task")
def add_task_redirect():
    return redirect("/add-task/manually")


@app.route("/add-task/<method>", methods=["GET", "POST"])
@login_required
def add_task(method):
    if not current_user.admin: return abort(403)
    if method not in ["manually", "sdam-gia", "json"]:
        return redirect("/")
    if request.method == "POST" and method == "manually":
        image, image_path = request.files.get("image"), None
        if image.filename:
            ext, n = image.filename.split(".")[-1], 0
            filename = image.filename.split(f".{ext}")[0]
            _path = f"static/condition/{filename}_"
            while isfile(f"{_path}{n}.{ext}"): n += 1
            image_path = f"condition/{filename}_{n}.{ext}"
            image.save("static/" + image_path)
        db_sess = db_session.create_session()
        db_sess.add(Task(
            title=request.form.get("title"),
            condition=request.form.get("condition"),
            image=image_path,
            answer=request.form.get("answer").replace(".", ","),
            subject=request.form.get("subject"),
            difficult=request.form.get("difficult")
        ))
        db_sess.commit()
    elif request.method == "POST" and method == "json":
        try:
            image, image_path = request.files.get("image"), None
            if image.filename:
                ext, n = image.filename.split(".")[-1], 0
                filename = image.filename.split(f".{ext}")[0]
                _path = f"static/condition/{filename}_"
                while isfile(f"{_path}{n}.{ext}"): n += 1
                image_path = f"condition/{filename}_{n}.{ext}"
                image.save("static/" + image_path)
            request.files.get("json").save("data/task.json")
            db_sess = db_session.create_session()
            with open("data/task.json") as file:
                data = load(file)
                db_sess.add(Task(
                    title=data["title"],
                    condition=data["condition"],
                    image=image_path,
                    answer=str(data["answer"]).replace(".", ","),
                    subject=data["subject"],
                    difficult=(data["difficult"] if data["difficult"] in
                        ["simple", "medium", "hard"] else "simple")))
                db_sess.commit()
        except Exception:
            return render_template("add-task.html", method=method, error=True)
    elif request.method == "POST" and method == "sdam-gia":
        try:
            response = get(request.form.get("url"))
            host = request.form.get("url").split("sdamgia.ru/")[0]
            soup = bs(response.text, "html.parser")
            block = soup.select(".pbody > p")[0]
            image = list(filter(lambda x: "/get_file?"
                in x["src"], block.select("img")))
            image = image[0] if image else None
            condition = str(block)
            for r in ['<p class="left_margin">',
                      str(image), '</p>']:
                condition = condition.replace(r, "")
            answer = soup.select(".answer > span")[0].text
            db_sess = db_session.create_session()
            db_sess.add(Task(
                title=request.form.get("title"),
                condition=condition,
                image=((image["src"] if image["src"].startswith("https://")
                        else f"{host}sdamgia.ru" + image["src"])
                        if image is not None else None),
                answer=answer.replace("Ответ: ", ""),
                subject=request.form.get("subject"),
                difficult=request.form.get("difficult")
            ))
            db_sess.commit()
        except Exception:
            return render_template("add-task.html", method=method, error=True)
    return render_template("add-task.html", method=method)

@app.route("/find/<difficult>")
@login_required
def find(difficult):
    if difficult not in "simple medium hard".split():
        return redirect("/")
    return render_template("find.html")


@app.route("/battle/<int:number>")
@login_required
def battle(number):
    if not rooms.check(number, current_user.id) or \
            all(rooms.resolve(number)):
        return redirect("/")
    _tasks, other_id = [], rooms.other(number, current_user.id)
    db_sess = db_session.create_session()
    other = db_sess.query(User).filter(User.id == other_id).first()
    for _task in rooms.tasks(number):
        _tasks.append({
            "id": _task.id,
            "title": _task.title,
            "condition": _task.condition,
            "image": _task.image
        })
    return render_template("battle.html", tasks=_tasks, other=other,
                    roomResolve=rooms.resolve(number), number=number)


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


@socketio.on("start")
def start_battle():
    join_room(current_user.id)


@socketio.on("disconnect")
def disconnect():
    leave_room(current_user.id)
    rooms.leave(current_user.id)
    print("Disconnect", current_user.id)


@socketio.on("check")
def check_answer(data):
    number, answer = data[0], data[1].replace(".", ",")
    if not rooms.check(number, current_user.id): return
    if rooms.check_answer(number, answer, current_user.id):
        db_sess = db_session.create_session()
        db_sess.add(Action(user_id=current_user.id,
                           task_id=number, status=2))
        db_sess.commit()
        _other = rooms.other(number, current_user.id)
        s_user = rooms.resolve(number).count(current_user.id)
        s_other = rooms.resolve(number).count(_other)
        if all(rooms.resolve(number)):
            S = 0.5 if s_user == s_other else (
                1 if s_user > s_other else 0)
            user = db_sess.query(User).filter(User.id == current_user.id).first()
            other = db_sess.query(User).filter(User.id == _other).first()
            user.rating, other.rating = elo(user.rating, other.rating, S)
            db_sess.commit()
        emit("loose", [rooms.resolve(number), f"{s_other} : {s_user}"], room=_other)
        emit("correct", [rooms.resolve(number), f"{s_user} : {s_other}"], room=current_user.id)
    else:
        db_sess = db_session.create_session()
        db_sess.add(Action(user_id=current_user.id, task_id=number, status=1))
        db_sess.commit()
        emit("invalid", room=current_user.id)


if __name__ == "__main__":
    if len(argv) > 1 and argv[1] == "--make-admin":
        login = input("Укажите логин пользователя: ")
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.login == login).first()
        user.admin = True
        db_sess.commit()
        print(f"Пользователь {login} теперь администратор!")
        exit()
    socketio.run(app, host=HOST, port=PORT, debug=DEBUG)
