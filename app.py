import os
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort
)

from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# =========================================================
# Flask 기본 설정
# =========================================================

app = Flask(__name__)


# =========================================================
# 데이터베이스 설정
# =========================================================

database_url = os.environ.get(
    "DATABASE_URL",
    "sqlite:///gomusin.db"
)

# Render PostgreSQL 주소 호환
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

# 중요
# psycopg2가 아니라 psycopg 3 사용
if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )


app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "CHANGE_THIS_SECRET_KEY"
)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


engine_options = {
    "pool_pre_ping": True
}


# PostgreSQL 연결 옵션
if database_url.startswith("postgresql+psycopg://"):

    engine_options["connect_args"] = {
        "connect_timeout": 10
    }


app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options


# =========================================================
# 세션 쿠키 설정
# =========================================================

cookie_secure = os.environ.get(
    "COOKIE_SECURE",
    "true"
).lower()

app.config["SESSION_COOKIE_SECURE"] = (
    cookie_secure == "true"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# =========================================================
# DB
# =========================================================

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
# 신규개통 모델
# =========================================================

class Sale(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # -----------------------------------------------------
    # 고객 정보
    # -----------------------------------------------------

    customer_name = db.Column(
        db.String(100),
        nullable=False
    )

    customer_phone = db.Column(
        db.String(30)
    )

    # -----------------------------------------------------
    # 개통 정보
    # -----------------------------------------------------

    opening_date = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )

    carrier = db.Column(
        db.String(30)
    )

    opening_type = db.Column(
        db.String(30)
    )

    # -----------------------------------------------------
    # 단말기 정보
    # -----------------------------------------------------

    device = db.Column(
        db.String(100)
    )

    color = db.Column(
        db.String(50)
    )

    storage = db.Column(
        db.String(50)
    )

    # -----------------------------------------------------
    # 요금제
    # -----------------------------------------------------

    plan = db.Column(
        db.String(100)
    )

    # -----------------------------------------------------
    # 계약 정보
    # -----------------------------------------------------

    contract_type = db.Column(
        db.String(50)
    )

    installment_months = db.Column(
        db.String(20)
    )

    # -----------------------------------------------------
    # 금액 정보
    # -----------------------------------------------------

    device_price = db.Column(
        db.String(50)
    )

    subsidy = db.Column(
        db.String(50)
    )

    installment_price = db.Column(
        db.String(50)
    )

    cash_price = db.Column(
        db.String(50)
    )

    monthly_payment = db.Column(
        db.String(50)
    )

    # -----------------------------------------------------
    # 개통 상태
    # -----------------------------------------------------

    status = db.Column(
        db.String(30),
        nullable=False,
        default="개통완료"
    )

    # -----------------------------------------------------
    # 메모
    # -----------------------------------------------------

    memo = db.Column(
        db.Text
    )

    # -----------------------------------------------------
    # 등록 직원
    # -----------------------------------------------------

    created_by = db.Column(
        db.String(50)
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
# 데이터베이스 준비
# =========================================================

def prepare_database():

    with app.app_context():

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
            password_hash=generate_password_hash(
                password
            ),
            role="admin"
        )

        db.session.add(user)

        db.session.commit()

    else:

        # 기존 관리자 계정도
        # Render 환경변수 비밀번호와 동기화
        if not check_password_hash(
            user.password_hash,
            password
        ):

            user.password_hash = generate_password_hash(
                password
            )

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

        return view(
            *args,
            **kwargs
        )

    return wrapped


# =========================================================
# 관리자 확인
# =========================================================

def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if session.get("role") != "admin":

            abort(403)

        return view(
            *args,
            **kwargs
        )

    return wrapped


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

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    try:

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
# 대시보드
# =========================================================

@app.route("/")
@login_required
def dashboard():

    try:

        prepare_database()

        today = date.today()

        # 전체 고객
        total = Customer.query.count()

        # 오늘 등록 고객
        #
        # PostgreSQL에서
        # date(timestamp) = varchar 문제가 생기지 않도록
        # 날짜 범위를 사용한다.
        today_start = datetime.combine(
            today,
            datetime.min.time()
        )

        tomorrow_start = datetime.combine(
            date.fromordinal(
                today.toordinal() + 1
            ),
            datetime.min.time()
        )

        today_count = Customer.query.filter(
            Customer.created_at >= today_start,
            Customer.created_at < tomorrow_start
        ).count()

        # 최근 고객
        recent = Customer.query.order_by(
            Customer.created_at.desc()
        ).limit(8).all()

        # 최근 예약
        recent_bookings = Booking.query.order_by(
            Booking.created_at.desc()
        ).limit(5).all()

        # 전체 예약
        all_bookings = Booking.query.order_by(
            Booking.created_at.asc()
        ).all()

        calendar_bookings = []

        for booking in all_bookings:

            calendar_bookings.append({

                "id": booking.id,

                "name": booking.name,

                "phone": booking.phone or "",

                "visit_date": booking.visit_date or "",

                "device": booking.device or "",

                "memo": booking.memo or ""

            })

        # 오늘 예약
        today_bookings = []

        today_string = str(today)

        for booking in all_bookings:

            visit_date = booking.visit_date or ""

            if visit_date[:10] == today_string:

                today_bookings.append(
                    booking
                )

        # 개통 통계
        total_sales = Sale.query.count()

        today_sales = Sale.query.filter(
            Sale.opening_date == today
        ).count()

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

        bookings=recent_bookings,

        today_bookings=today_bookings,

        calendar_bookings=calendar_bookings,

        total_sales=total_sales,

        today_sales=today_sales

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

        db.session.add(
            customer
        )

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

    db.session.delete(
        customer
    )

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

        db.session.add(
            booking
        )

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
# 신규개통 등록
# =========================================================

@app.route(
    "/sales/new",
    methods=["GET", "POST"]
)
@login_required
def sale_new():

    prepare_database()

    if request.method == "POST":

        customer_name = request.form.get(
            "customer_name",
            ""
        ).strip()

        if not customer_name:

            flash(
                "고객명을 입력해주세요."
            )

            return redirect(
                url_for("sale_new")
            )

        # -------------------------------------------------
        # 개통일
        # -------------------------------------------------

        opening_date_text = request.form.get(
            "opening_date",
            ""
        ).strip()

        if opening_date_text:

            try:

                opening_date = datetime.strptime(

                    opening_date_text,

                    "%Y-%m-%d"

                ).date()

            except ValueError:

                flash(
                    "개통일 형식이 올바르지 않습니다."
                )

                return redirect(
                    url_for("sale_new")
                )

        else:

            opening_date = date.today()

        # -------------------------------------------------
        # 신규개통 데이터
        # -------------------------------------------------

        sale = Sale(

            customer_name=customer_name,

            customer_phone=request.form.get(
                "customer_phone",
                ""
            ).strip(),

            opening_date=opening_date,

            carrier=request.form.get(
                "carrier",
                ""
            ).strip(),

            opening_type=request.form.get(
                "opening_type",
                ""
            ).strip(),

            device=request.form.get(
                "device",
                ""
            ).strip(),

            color=request.form.get(
                "color",
                ""
            ).strip(),

            storage=request.form.get(
                "storage",
                ""
            ).strip(),

            plan=request.form.get(
                "plan",
                ""
            ).strip(),

            contract_type=request.form.get(
                "contract_type",
                ""
            ).strip(),

            installment_months=request.form.get(
                "installment_months",
                ""
            ).strip(),

            device_price=request.form.get(
                "device_price",
                ""
            ).strip(),

            subsidy=request.form.get(
                "subsidy",
                ""
            ).strip(),

            installment_price=request.form.get(
                "installment_price",
                ""
            ).strip(),

            cash_price=request.form.get(
                "cash_price",
                ""
            ).strip(),

            monthly_payment=request.form.get(
                "monthly_payment",
                ""
            ).strip(),

            status=request.form.get(
                "status",
                "개통완료"
            ).strip(),

            memo=request.form.get(
                "memo",
                ""
            ).strip(),

            created_by=session.get(
                "username",
                ""
            )

        )

        db.session.add(
            sale
        )

        db.session.commit()

        flash(
            "신규개통 정보가 등록되었습니다."
        )

        return redirect(
            url_for("sales")
        )

    return render_template(
        "sale_form.html",
        sale=None
    )


# =========================================================
# 개통 목록
# =========================================================

@app.route("/sales")
@login_required
def sales():

    prepare_database()

    q = request.args.get(
        "q",
        ""
    ).strip()

    query = Sale.query

    if q:

        query = query.filter(

            db.or_(

                Sale.customer_name.contains(q),

                Sale.customer_phone.contains(q),

                Sale.device.contains(q),

                Sale.carrier.contains(q)

            )

        )

    sale_list = query.order_by(

        Sale.opening_date.desc(),

        Sale.created_at.desc()

    ).all()

    return render_template(

        "sales.html",

        sales=sale_list,

        q=q

    )


# =========================================================
# 개통 상세
# =========================================================

@app.route(
    "/sales/<int:sale_id>"
)
@login_required
def sale_detail(sale_id):

    prepare_database()

    sale = Sale.query.get_or_404(
        sale_id
    )

    return render_template(

        "sale_detail.html",

        sale=sale

    )


# =========================================================
# 개통 수정
# =========================================================

@app.route(
    "/sales/<int:sale_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def sale_edit(sale_id):

    prepare_database()

    sale = Sale.query.get_or_404(
        sale_id
    )

    if request.method == "POST":

        customer_name = request.form.get(
            "customer_name",
            ""
        ).strip()

        if not customer_name:

            flash(
                "고객명을 입력해주세요."
            )

            return redirect(

                url_for(
                    "sale_edit",
                    sale_id=sale_id
                )

            )

        opening_date_text = request.form.get(
            "opening_date",
            ""
        ).strip()

        if opening_date_text:

            try:

                sale.opening_date = datetime.strptime(

                    opening_date_text,

                    "%Y-%m-%d"

                ).date()

            except ValueError:

                flash(
                    "개통일 형식이 올바르지 않습니다."
                )

                return redirect(

                    url_for(
                        "sale_edit",
                        sale_id=sale_id
                    )

                )

        sale.customer_name = customer_name

        sale.customer_phone = request.form.get(
            "customer_phone",
            ""
        ).strip()

        sale.carrier = request.form.get(
            "carrier",
            ""
        ).strip()

        sale.opening_type = request.form.get(
            "opening_type",
            ""
        ).strip()

        sale.device = request.form.get(
            "device",
            ""
        ).strip()

        sale.color = request.form.get(
            "color",
            ""
        ).strip()

        sale.storage = request.form.get(
            "storage",
            ""
        ).strip()

        sale.plan = request.form.get(
            "plan",
            ""
        ).strip()

        sale.contract_type = request.form.get(
            "contract_type",
            ""
        ).strip()

        sale.installment_months = request.form.get(
            "installment_months",
            ""
        ).strip()

        sale.device_price = request.form.get(
            "device_price",
            ""
        ).strip()

        sale.subsidy = request.form.get(
            "subsidy",
            ""
        ).strip()

        sale.installment_price = request.form.get(
            "installment_price",
            ""
        ).strip()

        sale.cash_price = request.form.get(
            "cash_price",
            ""
        ).strip()

        sale.monthly_payment = request.form.get(
            "monthly_payment",
            ""
        ).strip()

        sale.status = request.form.get(
            "status",
            "개통완료"
        ).strip()

        sale.memo = request.form.get(
            "memo",
            ""
        ).strip()

        db.session.commit()

        flash(
            "개통 정보가 수정되었습니다."
        )

        return redirect(
            url_for("sales")
        )

    return render_template(

        "sale_form.html",

        sale=sale

    )


# =========================================================
# 개통 삭제
# =========================================================

@app.route(
    "/sales/<int:sale_id>/delete",
    methods=["POST"]
)
@login_required
@admin_required
def sale_delete(sale_id):

    prepare_database()

    sale = Sale.query.get_or_404(
        sale_id
    )

    db.session.delete(
        sale
    )

    db.session.commit()

    flash(
        "개통 정보가 삭제되었습니다."
    )

    return redirect(
        url_for("sales")
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

        if (
            not device
            or not carrier
            or not sale_type
            or not price
        ):

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

        db.session.add(
            item
        )

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

    db.session.delete(
        item
    )

    db.session.commit()

    flash(
        "시세가 삭제되었습니다."
    )

    return redirect(
        url_for("prices")
    )


# =========================================================
# 직원 관리
# =========================================================

@app.route(
    "/staff",
    methods=["GET", "POST"]
)
@login_required
@admin_required
def staff():

    prepare_database()

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        password_confirm = request.form.get(
            "password_confirm",
            ""
        )

        if not username:

            flash(
                "직원 아이디를 입력해주세요."
            )

            return redirect(
                url_for("staff")
            )

        if len(username) < 2:

            flash(
                "아이디는 2자 이상 입력해주세요."
            )

            return redirect(
                url_for("staff")
            )

        if len(password) < 4:

            flash(
                "비밀번호는 4자 이상 입력해주세요."
            )

            return redirect(
                url_for("staff")
            )

        if password != password_confirm:

            flash(
                "비밀번호가 서로 다릅니다."
            )

            return redirect(
                url_for("staff")
            )

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash(
                "이미 사용 중인 아이디입니다."
            )

            return redirect(
                url_for("staff")
            )

        user = User(

            username=username,

            password_hash=generate_password_hash(
                password
            ),

            role="staff"

        )

        db.session.add(
            user
        )

        db.session.commit()

        flash(
            f"{username} 직원 계정이 생성되었습니다."
        )

        return redirect(
            url_for("staff")
        )

    staff_list = User.query.order_by(

        User.created_at.asc()

    ).all()

    return render_template(

        "staff.html",

        users=staff_list

    )


# =========================================================
# 직원 삭제
# =========================================================

@app.route(
    "/staff/<int:user_id>/delete",
    methods=["POST"]
)
@login_required
@admin_required
def staff_delete(user_id):

    prepare_database()

    user = User.query.get_or_404(
        user_id
    )

    if user.role == "admin":

        flash(
            "관리자 계정은 삭제할 수 없습니다."
        )

        return redirect(
            url_for("staff")
        )

    if user.id == session.get(
        "user_id"
    ):

        flash(
            "현재 로그인한 계정은 삭제할 수 없습니다."
        )

        return redirect(
            url_for("staff")
        )

    username = user.username

    db.session.delete(
        user
    )

    db.session.commit()

    flash(
        f"{username} 직원 계정이 삭제되었습니다."
    )

    return redirect(
        url_for("staff")
    )


# =========================================================
# 직원 비밀번호 변경
# =========================================================

@app.route(
    "/staff/<int:user_id>/password",
    methods=["POST"]
)
@login_required
@admin_required
def staff_password(user_id):

    prepare_database()

    user = User.query.get_or_404(
        user_id
    )

    if user.role == "admin":

        flash(
            "관리자 계정 비밀번호는 Render 환경변수에서 관리해주세요."
        )

        return redirect(
            url_for("staff")
        )

    new_password = request.form.get(
        "new_password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    if len(new_password) < 4:

        flash(
            "비밀번호는 4자 이상 입력해주세요."
        )

        return redirect(
            url_for("staff")
        )

    if new_password != confirm_password:

        flash(
            "비밀번호가 서로 다릅니다."
        )

        return redirect(
            url_for("staff")
        )

    user.password_hash = generate_password_hash(
        new_password
    )

    db.session.commit()

    flash(
        f"{user.username} 직원의 비밀번호가 변경되었습니다."
    )

    return redirect(
        url_for("staff")
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
# 404 오류
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return (
        "페이지를 찾을 수 없습니다.",
        404
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
    
