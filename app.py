
import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)


# =========================================================
# 데이터베이스 설정
# =========================================================

database_url = os.environ.get("DATABASE_URL", "sqlite:///gomusin.db")

# 일부 PostgreSQL 서비스의 postgres:// 주소 호환
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )


app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY"
)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("COOKIE_SECURE", "false").lower() == "true"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


db = SQLAlchemy(app)


# =========================================================
# 데이터베이스 모델
# =========================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default="staff"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    phone = db.Column(
        db.String(30),
        index=True
    )

    device = db.Column(
        db.String(100)
    )

    carrier = db.Column(
        db.String(30)
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="상담중"
    )

    memo = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    phone = db.Column(
        db.String(30)
    )

    visit_date = db.Column(
        db.String(30)
    )

    device = db.Column(
        db.String(100)
    )

    memo = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    device = db.Column(
        db.String(100),
        nullable=False
    )

    carrier = db.Column(
        db.String(30),
        nullable=False
    )

    sale_type = db.Column(
        db.String(30),
        nullable=False
    )

    price = db.Column(
        db.String(100),
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# =========================================================
# 관리자 계정 자동 생성 / 동기화
# =========================================================

def sync_admin():

    username = os.environ.get(
        "ADMIN_USERNAME",
        ""
    ).strip()

    password = os.environ.get(
        "ADMIN_PASSWORD",
        ""
    )

    # Render 환경변수가 없으면 아무 작업도 하지 않음
    if not username or not password:
        return

    # 관리자 아이디 찾기
    user = User.query.filter_by(
        username=username
    ).first()

    # 관리자 계정이 없으면 새로 생성
    if user is None:

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role="admin"
        )

        db.session.add(user)

    # 이미 있으면 Render 환경변수의 비밀번호로 갱신
    else:

        user.password_hash = generate_password_hash(password)

        user.role = "admin"

    db.session.commit()


# =========================================================
# 로그인 권한 확인
# =========================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user_id" not in session:
            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped


def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if session.get("role") != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# 서버 실행 시 관리자 계정 확인
# =========================================================

with app.app_context():

    db.create_all()

    sync_admin()


# =========================================================
# 서버 상태 확인
# =========================================================

@app.route("/health")
def health():

    return {
        "status": "ok"
    }, 200


# =========================================================
# 로그인
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # 로그인할 때마다 관리자 계정 동기화
    sync_admin()

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password_hash,
            password
        ):

            session.clear()

            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role

            return redirect(
                url_for("dashboard")
            )

        flash(
            "아이디 또는 비밀번호가 올바르지 않습니다."
        )

    return render_template(
        "login.html"
    )


# =========================================================
# 로그아웃
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# 대시보드
# =========================================================

@app.route("/")
@login_required
def dashboard():

    today = datetime.now().date()

    total = Customer.query.count()

    today_count = Customer.query.filter(
        db.func.date(Customer.created_at) == str(today)
    ).count()

    recent = Customer.query.order_by(
        Customer.created_at.desc()
    ).limit(8).all()

    bookings = Booking.query.order_by(
        Booking.created_at.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        total=total,
        today_count=today_count,
        recent=recent,
        bookings=bookings
    )


# =========================================================
# 고객 목록
# =========================================================

@app.route("/customers")
@login_required
def customers():

    q = request.args.get(
        "q",
        ""
    ).strip()

    query = Customer.query

    if q:

        query = query.filter(
            db.or_(
                Customer.name.contains(q),
                Customer.phone.contains(q)
            )
        )

    customer_list = query.order_by(
        Customer.created_at.desc()
    ).all()

    return render_template(
        "customers.html",
        customers=customer_list,
        q=q
    )


# =========================================================
# 고객 등록
# =========================================================

@app.route("/customers/new", methods=["GET", "POST"])
@login_required
def customer_new():

    if request.method == "POST":

        customer = Customer(

            name=request.form.get(
                "name",
                ""
            ).strip(),

            phone=request.form.get(
                "phone",
                ""
            ).strip(),

            device=request.form.get(
                "device",
                ""
            ).strip(),

            carrier=request.form.get(
                "carrier",
                ""
            ).strip(),

            status=request.form.get(
                "status",
                "상담중"
            ),

            memo=request.form.get(
                "memo",
                ""
            ).strip()
        )

        db.session.add(customer)

        db.session.commit()

        flash(
            "고객이 등록되었습니다."
        )

        return redirect(
            url_for("customers")
        )

    return render_template(
        "customer_form.html",
        customer=None
    )


# =========================================================
# 고객 수정
# =========================================================

@app.route(
    "/customers/<int:customer_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def customer_edit(customer_id):

    customer = Customer.query.get_or_404(
        customer_id
    )

    if request.method == "POST":

        customer.name = request.form.get(
            "name",
            ""
        ).strip()

        customer.phone = request.form.get(
            "phone",
            ""
        ).strip()

        customer.device = request.form.get(
            "device",
            ""
        ).strip()

        customer.carrier = request.form.get(
            "carrier",
            ""
        ).strip()

        customer.status = request.form.get(
            "status",
            "상담중"
        )

        customer.memo = request.form.get(
            "memo",
            ""
        ).strip()

        db.session.commit()

        flash(
            "고객 정보가 수정되었습니다."
        )

        return redirect(
            url_for("customers")
        )

    return render_template(
        "customer_form.html",
        customer=customer
    )


# =========================================================
# 고객 삭제
# =========================================================

@app.route(
    "/customers/<int:customer_id>/delete",
    methods=["POST"]
)
@login_required
@admin_required
def customer_delete(customer_id):

    customer = Customer.query.get_or_404(
        customer_id
    )

    db.session.delete(customer)

    db.session.commit()

    flash(
        "고객 정보가 삭제되었습니다."
    )

    return redirect(
        url_for("customers")
    )


# =========================================================
# 예약 관리
# =========================================================

@app.route(
    "/bookings",
    methods=["GET", "POST"]
)
@login_required
def bookings():

    if request.method == "POST":

        booking = Booking(

            name=request.form.get(
                "name",
                ""
            ).strip(),

            phone=request.form.get(
                "phone",
                ""
            ).strip(),

            visit_date=request.form.get(
                "visit_date",
                ""
            ),

            device=request.form.get(
                "device",
                ""
            ).strip(),

            memo=request.form.get(
                "memo",
                ""
            ).strip()
        )

        db.session.add(booking)

        db.session.commit()

        flash(
            "예약이 등록되었습니다."
        )

        return redirect(
            url_for("bookings")
        )

    booking_list = Booking.query.order_by(
        Booking.created_at.desc()
    ).all()

    return render_template(
        "bookings.html",
        bookings=booking_list
    )


# =========================================================
# 시세표 관리
# =========================================================

@app.route(
    "/prices",
    methods=["GET", "POST"]
)
@login_required
def prices():

    if request.method == "POST":

        if session.get("role") != "admin":
            abort(403)

        item = Price(

            device=request.form.get(
                "device",
                ""
            ).strip(),

            carrier=request.form.get(
                "carrier",
                ""
            ),

            sale_type=request.form.get(
                "sale_type",
                ""
            ),

            price=request.form.get(
                "price",
                ""
            ).strip()
        )

        db.session.add(item)

        db.session.commit()

        flash(
            "시세가 등록되었습니다."
        )

        return redirect(
            url_for("prices")
        )

    price_list = Price.query.order_by(
        Price.updated_at.desc()
    ).all()

    return render_template(
        "prices.html",
        prices=price_list
    )


# =========================================================
# 시세 삭제
# =========================================================

@app.route(
    "/prices/<int:price_id>/delete",
    methods=["POST"]
)
@login_required
@admin_required
def price_delete(price_id):

    item = Price.query.get_or_404(
        price_id
    )

    db.session.delete(item)

    db.session.commit()

    flash(
        "시세가 삭제되었습니다."
    )

    return redirect(
        url_for("prices")
    )


# =========================================================
# 로컬 실행
# =========================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                "5000"
            )
        )
    )
