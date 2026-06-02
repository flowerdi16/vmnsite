import os
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy

# ================== APP ==================
app = Flask(__name__)
app.secret_key = "super_secret_key_change_me"

# ================== CLOUDINARY ==================
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)

# ================== DATABASE ==================
database_url = os.environ.get("DATABASE_URL")

print("DATABASE_URL found:", bool(database_url))

if not database_url:
    print("WARNING: DATABASE_URL is missing")
    
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================== ADMIN ==================
ADMIN_LOGIN = "mindura"
ADMIN_PASSWORD = "gl4ssz02"

# ================== MODELS ==================
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    image = db.Column(db.Text)
    short_desc = db.Column(db.Text)
    full_desc = db.Column(db.Text)


class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"))
    title = db.Column(db.String(120))
    url = db.Column(db.String(255))

# ================== ROUTES ==================
@app.route("/")
def index():
    employees = Employee.query.all()
    return render_template("index.html", employees=employees)


@app.route("/employee/<int:id>")
def employee(id):
    emp = Employee.query.get_or_404(id)
    links = Link.query.filter_by(employee_id=id).all()
    return render_template("detail.html", emp=emp, links=links)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form["login"] == ADMIN_LOGIN and
            request.form["password"] == ADMIN_PASSWORD):
            session["admin"] = True
            return redirect("/admin")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")


def is_admin():
    return session.get("admin")


@app.route("/admin")
def admin():
    if not is_admin():
        return redirect("/login")

    employees = Employee.query.all()
    return render_template("admin.html", employees=employees)


# ================== ADD ==================
@app.route("/add", methods=["POST"])
def add_employee():
    if not is_admin():
        return redirect("/login")

    file = request.files.get("image")
    image_url = ""

    if file and file.filename:
        result = cloudinary.uploader.upload(file)
        image_url = result["secure_url"]

    emp = Employee(
        name=request.form["name"],
        image=image_url,
        short_desc=request.form["short_desc"],
        full_desc=request.form["full_desc"]
    )

    db.session.add(emp)
    db.session.commit()

    for i in range(1, 11):
        title = request.form.get(f"link_title_{i}")
        url = request.form.get(f"link_url_{i}")

        if title and url:
            db.session.add(Link(employee_id=emp.id, title=title, url=url))

    db.session.commit()
    return redirect("/admin")


# ================== DELETE ==================
@app.route("/delete/<int:id>")
def delete_employee(id):
    if not is_admin():
        return redirect("/login")

    Link.query.filter_by(employee_id=id).delete()
    emp = Employee.query.get_or_404(id)
    db.session.delete(emp)

    db.session.commit()
    return redirect("/admin")


# ================== EDIT ==================
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_employee(id):
    if not is_admin():
        return redirect("/login")

    emp = Employee.query.get_or_404(id)

    if request.method == "POST":
        emp.name = request.form["name"]
        emp.short_desc = request.form["short_desc"]
        emp.full_desc = request.form["full_desc"]

        file = request.files.get("image")

        if file and file.filename:
            result = cloudinary.uploader.upload(file)
            emp.image = result["secure_url"]

        Link.query.filter_by(employee_id=id).delete()

        for i in range(1, 11):
            title = request.form.get(f"link_title_{i}")
            url = request.form.get(f"link_url_{i}")

            if title and url:
                db.session.add(Link(employee_id=id, title=title, url=url))

        db.session.commit()
        return redirect("/admin")

    links = Link.query.filter_by(employee_id=id).all()
    return render_template("edit.html", emp=emp, links=links)


# ================== INIT DB ==================
with app.app_context():
    db.create_all()


# ================== RUN ==================
if __name__ == "__main__":
    app.run(debug=True)
