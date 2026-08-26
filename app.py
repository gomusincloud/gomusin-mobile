
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-before-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///gomusin.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="staff", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30))
    device = db.Column(db.String(100))
    carrier = db.Column(db.String(30))
    status = db.Column(db.String(30), default="상담중")
    memo = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30))
    visit_date = db.Column(db.String(30))
    device = db.Column(db.String(100))
    memo = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device = db.Column(db.String(100), nullable=False)
    carrier = db.Column(db.String(30))
    type = db.Column(db.String(30))
    price = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def login_required(fn):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

def admin_required(fn):
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("관리자 권한이 필요합니다.")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password_hash, request.form["password"]):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("dashboard"))
        flash("아이디 또는 비밀번호가 올바르지 않습니다.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    today = datetime.now().date()
    total = Customer.query.count()
    today_count = Customer.query.filter(db.func.date(Customer.created_at) == str(today)).count()
    bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    recent = Customer.query.order_by(Customer.created_at.desc()).limit(8).all()
    return render_template("dashboard.html", total=total, today_count=today_count,
                           recent=recent, bookings=bookings)

@app.route("/customers")
@login_required
def customers():
    q = request.args.get("q","").strip()
    query = Customer.query
    if q:
        query = query.filter((Customer.name.contains(q)) | (Customer.phone.contains(q)))
    items = query.order_by(Customer.created_at.desc()).all()
    return render_template("customers.html", customers=items, q=q)

@app.route("/customers/new", methods=["GET","POST"])
@login_required
def customer_new():
    if request.method == "POST":
        c = Customer(
            name=request.form["name"], phone=request.form.get("phone"),
            device=request.form.get("device"), carrier=request.form.get("carrier"),
            status=request.form.get("status","상담중"), memo=request.form.get("memo")
        )
        db.session.add(c); db.session.commit()
        flash("고객이 등록되었습니다.")
        return redirect(url_for("customers"))
    return render_template("customer_form.html", customer=None)

@app.route("/customers/<int:id>/edit", methods=["GET","POST"])
@login_required
def customer_edit(id):
    c = Customer.query.get_or_404(id)
    if request.method == "POST":
        c.name=request.form["name"]; c.phone=request.form.get("phone")
        c.device=request.form.get("device"); c.carrier=request.form.get("carrier")
        c.status=request.form.get("status","상담중"); c.memo=request.form.get("memo")
        db.session.commit(); flash("고객 정보가 수정되었습니다.")
        return redirect(url_for("customers"))
    return render_template("customer_form.html", customer=c)

@app.route("/customers/<int:id>/delete", methods=["POST"])
@login_required
def customer_delete(id):
    c = Customer.query.get_or_404(id)
    db.session.delete(c); db.session.commit()
    flash("고객 정보가 삭제되었습니다.")
    return redirect(url_for("customers"))

@app.route("/bookings", methods=["GET","POST"])
@login_required
def bookings():
    if request.method == "POST":
        b=Booking(name=request.form["name"], phone=request.form.get("phone"),
                  visit_date=request.form.get("visit_date"), device=request.form.get("device"),
                  memo=request.form.get("memo"))
        db.session.add(b); db.session.commit(); flash("예약이 등록되었습니다.")
        return redirect(url_for("bookings"))
    items=Booking.query.order_by(Booking.visit_date.asc()).all()
    return render_template("bookings.html", bookings=items)

@app.route("/prices", methods=["GET","POST"])
@login_required
def prices():
    if request.method == "POST":
        if session.get("role") != "admin":
            flash("시세 수정은 관리자만 가능합니다.")
            return redirect(url_for("prices"))
        p=Price(device=request.form["device"], carrier=request.form["carrier"],
                type=request.form["type"], price=request.form["price"])
        db.session.add(p); db.session.commit(); flash("시세가 등록되었습니다.")
        return redirect(url_for("prices"))
    items=Price.query.order_by(Price.updated_at.desc()).all()
    return render_template("prices.html", prices=items)

@app.route("/prices/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def price_delete(id):
    p=Price.query.get_or_404(id); db.session.delete(p); db.session.commit()
    return redirect(url_for("prices"))

def init_data():
    db.create_all()
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_password and not User.query.filter_by(username=admin_username).first():
        db.session.add(User(username=admin_username, password_hash=generate_password_hash(admin_password), role="admin"))
        db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        init_data()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)
