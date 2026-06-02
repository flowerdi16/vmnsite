import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_key_change_me"

# База данных

database_url = os.environ.get("DATABASE_URL")
print("DATABASE_URL found:", bool(database_url))

if not database_url:
    raise RuntimeError(
        "DATABASE_URL не настроен. Проверь Environment Variables в Render."
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url.replace(
    "postgres://", "postgresql://"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Загрузка файлов
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# ====== АДМИН ======
ADMIN_LOGIN = "mindura"
ADMIN_PASSWORD = "gl4ssz02"


# ====== МОДЕЛИ ======
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    image = db.Column(db.String(255))
    short_desc = db.Column(db.Text)
    full_desc = db.Column(db.Text)


class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"))
    title = db.Column(db.String(120))
    url = db.Column(db.String(255))


# ====== ГЛАВНАЯ ======
@app.route("/")
def index():
    employees = Employee.query.all()
    return render_template("index.html", employees=employees)


# ====== СТРАНИЦА СОТРУДНИКА ======
@app.route("/employee/<int:id>")
def employee(id):
    emp = Employee.query.get_or_404(id)
    links = Link.query.filter_by(employee_id=id).all()
    return render_template("detail.html", emp=emp, links=links)


# ====== ЛОГИН ======
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["login"] == ADMIN_LOGIN and request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
    return render_template("login.html")


# ====== ВЫХОД ======
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")


# ====== ПРОВЕРКА АДМИНА ======
def is_admin():
    return session.get("admin")


# ====== АДМИН ПАНЕЛЬ ======
@app.route("/admin")
def admin():
    if not is_admin():
        return redirect("/login")

    employees = Employee.query.all()
    return render_template("admin.html", employees=employees)


# ====== ДОБАВЛЕНИЕ СОТРУДНИКА ======
@app.route("/add", methods=["POST"])
def add_employee():
    if not is_admin():
        return redirect("/login")

    file = request.files["image"]
    filename = ""

    if file and file.filename:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    emp = Employee(
        name=request.form["name"],
        image=filename,
        short_desc=request.form["short_desc"],
        full_desc=request.form["full_desc"]
    )

    db.session.add(emp)
    db.session.commit()

    # ссылки (сколько заполнили — столько и добавим)
    for i in range(1, 11):  # до 10 ссылок
        title = request.form.get(f"link_title_{i}")
        url = request.form.get(f"link_url_{i}")

        if title and url:
            db.session.add(Link(employee_id=emp.id, title=title, url=url))

    db.session.commit()
    return redirect("/admin")


# ====== УДАЛЕНИЕ СОТРУДНИКА ======
@app.route("/delete/<int:id>")
def delete_employee(id):
    if not is_admin():
        return redirect("/login")

    emp = Employee.query.get_or_404(id)

    Link.query.filter_by(employee_id=id).delete()
    db.session.delete(emp)
    db.session.commit()

    return redirect("/admin")


# ====== РЕДАКТИРОВАНИЕ СОТРУДНИКА ======
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_employee(id):
    if not is_admin():
        return redirect("/login")

    emp = Employee.query.get_or_404(id)

    if request.method == "POST":

        emp.name = request.form["name"]
        emp.short_desc = request.form["short_desc"]
        emp.full_desc = request.form["full_desc"]

        # обновление фото (если загружено новое)
        file = request.files["image"]
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            emp.image = filename

        # удалить старые ссылки
        Link.query.filter_by(employee_id=id).delete()

        # добавить новые
        for i in range(1, 11):
            title = request.form.get(f"link_title_{i}")
            url = request.form.get(f"link_url_{i}")

            if title and url:
                db.session.add(Link(employee_id=id, title=title, url=url))

        db.session.commit()
        return redirect("/admin")

    links = Link.query.filter_by(employee_id=id).all()
    return render_template("edit.html", emp=emp, links=links)

with app.app_context():
    db.create_all() 
    
# ====== ЗАПУСК ======
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
