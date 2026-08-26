import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# Flask 기본 설정
# =========================================================

app = Flask(__name__)

database_url = os.environ.get("DATABASE_URL", "sqlite:///gomusin.db")

# postgres:// 형식 호환
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "CHANGE_THIS_SECRET_KEY"
)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# DB 연결이 무한정 멈추지 않도록 설정
engine_options = {
    "pool_pre_ping": True,
}

if database_url.startswith("postgresql"):
    engine_options["connect_args"] = {
        "connect_timeout": 10
    }

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options


# HTTPS 환경에서는 true
cookie_secure = os.environ.get(
    "COOKIE_SECURE",
    "true"
).lower()

app.config["SESSION_COOKIE_SECURE"] = cookie_secure == "true"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


db = SQLAlchemy(app)


# =========================================================
# 사용자 모델
# =========================================================

class User(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

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


# =========================================================
# 고객 모델
# =========================================================

class Customer(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

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


# =========================================================
# 예약 모델
# =========================================================

class Booking(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    phone = db.Column(
        db.String(30)
    )

    visit_date = db.Column(
        db.String(50)
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


# =========================================================
# 시세표 모델
# =========================================================

class Price(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

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
# 데이터베이스 준비
# =========================================================

def prepare_database():

    db.create_all()


# =========================================================
# 관리자 계정 생성 / 확인
# =========================================================

def sync_admin():

    prepare_database()

    username = os.environ.get(
        "ADMIN_USERNAME",
        ""
    ).strip()

    password = os.environ.get(
        "ADMIN_PASSWORD",
        ""
    )

    if not username or not password:
        return False

    user = User.query.filter_by(
        username=username
    ).first()

    if user is None:

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role="admin"
        )

        db.session.add(user)
        db.session.commit()

    else:

        # 기존 계정은 admin 권한만 보장
        if user.role != "admin":
            user.role = "admin"
            db.session.commit()

    return True


# =========================================================
# 로그인 확인
# =========================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("user_id"):
            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# 관리자 확인
# =========================================================

def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if session.get("role") != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# 서버 상태 확인
#
# 중요:
# 이 페이지에서는 DB에 접속하지 않습니다.
# Render 배포 확인용입니다.
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

    try:
        # 로그인 페이지 접속 시 DB 준비 및 관리자 생성
        sync_admin()

    except Exception as e:

        return (
            f"데이터베이스 연결 오류: {str(e)}",
            500
        )

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
# 메인 대시보드
# =========================================================

@app.route("/")
@login_required
def dashboard():

    try:
        prepare_database()

        today = datetime.now().date()

        total = Customer.query.count()

        today_count = Customer.query.filter(
            db.func.date(Customer.created_at) == str(today)
        ).count()

        recent = Customer.query.order_by(
            Customer.created_at.desc()
        ).limit(8).all()

        recent_bookings = Booking.query.order_by(
            Booking.created_at.desc()
        ).limit(5).all()

    except Exception as e:

        return (
            f"데이터베이스 오류: {str(e)}",
            500
        )

    return render_template(
        "dashboard.html",
        total=total,
        today_count=today_count,
        recent=recent,
        bookings=recent_bookings
    )


# =========================================================
# 고객 목록
# =========================================================

@app.route("/customers")
@login_required
def customers():

    prepare_database()

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

@app.route(
    "/customers/new",
    methods=["GET", "POST"]
)
@login_required
def customer_new():

    prepare_database()

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        if not name:

            flash(
                "고객 이름을 입력해주세요."
            )

            return redirect(
                url_for("customer_new")
            )

        customer = Customer(

            name=name,

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
            ).strip(),

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

    prepare_database()

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
        ).strip()

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

    prepare_database()

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

    prepare_database()

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        if not name:

            flash(
                "예약자 이름을 입력해주세요."
            )

            return redirect(
                url_for("bookings")
            )

        booking = Booking(

            name=name,

            phone=request.form.get(
                "phone",
                ""
            ).strip(),

            visit_date=request.form.get(
                "visit_date",
                ""
            ).strip(),

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

    prepare_database()

    if request.method == "POST":

        if session.get("role") != "admin":
            abort(403)

        device = request.form.get(
            "device",
            ""
        ).strip()

        carrier = request.form.get(
            "carrier",
            ""
        ).strip()

        sale_type = request.form.get(
            "sale_type",
            ""
        ).strip()

        price = request.form.get(
            "price",
            ""
        ).strip()

        if not device or not carrier or not sale_type or not price:

            flash(
                "모든 시세 정보를 입력해주세요."
            )

            return redirect(
                url_for("prices")
            )

        item = Price(

            device=device,

            carrier=carrier,

            sale_type=sale_type,

            price=price
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

    prepare_database()

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
# 403 오류
# =========================================================

@app.errorhandler(403)
def forbidden(error):

    return (
        "접근 권한이 없습니다.",
        403
    )


# =========================================================
# 로컬 개발용 실행
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
