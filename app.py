
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

database_url = os.environ.get("DATABASE_URL", "sqlite:///gomusin.db").strip()

# Render PostgreSQL + psycopg 3 호환
# 중요: postgresql:// 은 기본적으로 psycopg2를 찾을 수 있으므로
# psycopg 3를 사용할 때는 postgresql+psycopg:// 로 명시한다.
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql+psycopg://",
        1
    )
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )
elif database_url.startswith("postgresql+psycopg2://"):
    database_url = database_url.replace(
        "postgresql+psycopg2://",
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
    "pool_pre_ping": True,
}

if database_url.startswith("postgresql+psycopg://"):
    engine_options["connect_args"] = {
        "connect_timeout": 10
    }

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

cookie_secure = os.environ.get(
    "COOKIE_SECURE",
    "true"
).lower()

app.config["SESSION_COOKIE_SECURE"] = cookie_secure == "true"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db = SQLAlchemy(app)


# =========================================================
# 기존 사용자 모델
# =========================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# =========================================================
# 기존 고객 모델
# =========================================================

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30), index=True)
    device = db.Column(db.String(100))
    carrier = db.Column(db.String(30))
    status = db.Column(db.String(30), nullable=False, default="상담중")
    memo = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# =========================================================
# 기존 예약 모델
# =========================================================

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30))
    visit_date = db.Column(db.String(50))
    device = db.Column(db.String(100))
    memo = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# =========================================================
# 기존 시세표 모델
# =========================================================

class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device = db.Column(db.String(100), nullable=False)
    carrier = db.Column(db.String(30), nullable=False)
    sale_type = db.Column(db.String(30), nullable=False)
    price = db.Column(db.String(100), nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# =========================================================
# 신규 판매/개통 모델
#
# 기존 2026년 판매일보의 핵심 항목을 DB에 맞게 분리해 저장한다.
# 정산/부가세/마진은 저장 시 자동 계산한다.
# =========================================================

class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)

    # 기본
    sale_date = db.Column(db.Date, nullable=False, default=lambda: datetime.now().date())
    sale_kind = db.Column(db.String(20), nullable=False, default="휴대폰")
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(30), index=True)
    visit_type = db.Column(db.String(50))
    seller = db.Column(db.String(50))

    # 개통 정보
    carrier = db.Column(db.String(30))
    signup_type = db.Column(db.String(50))       # 신규/기변/MNP
    device = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    contract_store = db.Column(db.String(100))
    activation_number = db.Column(db.String(30))
    new_m_existing = db.Column(db.String(30))   # 신/M/보
    payment_type = db.Column(db.String(30))      # 현금/할부
    installment_months = db.Column(db.Integer)
    installment_principal = db.Column(db.Integer, default=0)
    plan = db.Column(db.String(200))

    # 부가서비스 / 인터넷
    addon_text = db.Column(db.Text)
    internet_plan = db.Column(db.Text)
    combination_text = db.Column(db.Text)

    # 판매/정산
    price_table = db.Column(db.String(200))
    rebate = db.Column(db.Integer, default=0)           # R/B
    verbal = db.Column(db.Integer, default=0)           # 구두
    deduction = db.Column(db.Integer, default=0)        # 차감
    installment_free = db.Column(db.Integer, default=0) # 할부프리
    cash_activation = db.Column(db.Integer, default=0)  # 현금개통
    usim_fee = db.Column(db.Integer, default=0)
    commission = db.Column(db.Integer, default=0)

    settlement = db.Column(db.Integer, default=0)
    vat_rate = db.Column(db.Float, default=0.133)
    vat_amount = db.Column(db.Integer, default=0)

    # 기타 비용/혜택
    penalty_payback = db.Column(db.Integer, default=0)   # 위약금대납/페이백
    used_phone_cash = db.Column(db.Integer, default=0)   # 중고폰/고객현금
    gift_cost = db.Column(db.Integer, default=0)         # 사은품 비용
    quick_cost = db.Column(db.Integer, default=0)        # 퀵비
    margin = db.Column(db.Integer, default=0)

    # 업무 메모
    policy_note = db.Column(db.Text)       # 구두내용/부가추가/차감내역
    sales_note = db.Column(db.Text)        # 판매내용
    customer_promise = db.Column(db.Text)  # 고객약속
    welfare_note = db.Column(db.Text)      # 복지확인
    used_phone_note = db.Column(db.Text)   # 중고폰

    # 사후관리 상태
    docs_status = db.Column(db.String(30), default="미확인")
    gift_status = db.Column(db.String(30), default="준비필요")
    addon_status = db.Column(db.String(30), default="확인필요")
    combination_status = db.Column(db.String(30), default="확인필요")
    aftercare_status = db.Column(db.String(30), default="관리필요")

    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# =========================================================
# DB 준비
# =========================================================

def prepare_database():
    db.create_all()


# =========================================================
# 관리자 계정 동기화
# =========================================================

def sync_admin():
    prepare_database()

    username = os.environ.get("ADMIN_USERNAME", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "")

    if not username or not password:
        return False

    user = User.query.filter_by(username=username).first()

    if user is None:
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role="admin"
        )
        db.session.add(user)
        db.session.commit()
    else:
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
            return redirect(url_for("login"))
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
# 숫자 변환 / 자동계산
# =========================================================

def to_int(value):
    try:
        if value is None:
            return 0
        value = str(value).replace(",", "").strip()
        if not value:
            return 0
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def calculate_sale(sale):
    # 판매일보의 정산식:
    # R/B + 구두 - 차감 - 할부프리 - 현금개통 - 유심비 - 수수료
    sale.settlement = (
        sale.rebate
        + sale.verbal
        - sale.deduction
        - sale.installment_free
        - sale.cash_activation
        - sale.usim_fee
        - sale.commission
    )

    sale.vat_amount = round(sale.settlement * sale.vat_rate)

    # 판매일보의 마진식:
    # 정산 - 부가세 - 위약금/페이백 - 사은품 + 중고폰/고객현금 - 퀵비
    sale.margin = (
        sale.settlement
        - sale.vat_amount
        - sale.penalty_payback
        - sale.gift_cost
        + sale.used_phone_cash
        - sale.quick_cost
    )


def update_sale_from_form(sale):
    sale.sale_date = datetime.strptime(
        request.form.get("sale_date", ""),
        "%Y-%m-%d"
    ).date() if request.form.get("sale_date") else datetime.now().date()

    sale.sale_kind = request.form.get("sale_kind", "휴대폰").strip()
    sale.customer_name = request.form.get("customer_name", "").strip()
    sale.customer_phone = request.form.get("customer_phone", "").strip()
    sale.visit_type = request.form.get("visit_type", "").strip()
    sale.seller = request.form.get("seller", "").strip()

    sale.carrier = request.form.get("carrier", "").strip()
    sale.signup_type = request.form.get("signup_type", "").strip()
    sale.device = request.form.get("device", "").strip()
    sale.serial_number = request.form.get("serial_number", "").strip()
    sale.contract_store = request.form.get("contract_store", "").strip()
    sale.activation_number = request.form.get("activation_number", "").strip()
    sale.new_m_existing = request.form.get("new_m_existing", "").strip()
    sale.payment_type = request.form.get("payment_type", "").strip()
    sale.installment_months = to_int(request.form.get("installment_months"))
    sale.installment_principal = to_int(request.form.get("installment_principal"))
    sale.plan = request.form.get("plan", "").strip()

    sale.addon_text = request.form.get("addon_text", "").strip()
    sale.internet_plan = request.form.get("internet_plan", "").strip()
    sale.combination_text = request.form.get("combination_text", "").strip()

    sale.price_table = request.form.get("price_table", "").strip()
    sale.rebate = to_int(request.form.get("rebate"))
    sale.verbal = to_int(request.form.get("verbal"))
    sale.deduction = to_int(request.form.get("deduction"))
    sale.installment_free = to_int(request.form.get("installment_free"))
    sale.cash_activation = to_int(request.form.get("cash_activation"))
    sale.usim_fee = to_int(request.form.get("usim_fee"))
    sale.commission = to_int(request.form.get("commission"))

    sale.penalty_payback = to_int(request.form.get("penalty_payback"))
    sale.used_phone_cash = to_int(request.form.get("used_phone_cash"))
    sale.gift_cost = to_int(request.form.get("gift_cost"))
    sale.quick_cost = to_int(request.form.get("quick_cost"))

    sale.policy_note = request.form.get("policy_note", "").strip()
    sale.sales_note = request.form.get("sales_note", "").strip()
    sale.customer_promise = request.form.get("customer_promise", "").strip()
    sale.welfare_note = request.form.get("welfare_note", "").strip()
    sale.used_phone_note = request.form.get("used_phone_note", "").strip()

    sale.docs_status = request.form.get("docs_status", "미확인")
    sale.gift_status = request.form.get("gift_status", "준비필요")
    sale.addon_status = request.form.get("addon_status", "확인필요")
    sale.combination_status = request.form.get("combination_status", "확인필요")
    sale.aftercare_status = request.form.get("aftercare_status", "관리필요")

    sale.vat_rate = 0.133
    calculate_sale(sale)


# =========================================================
# 서버 상태
# =========================================================

@app.route("/health")
def health():
    try:
        prepare_database()
        db.session.execute(db.text("SELECT 1"))
        return {"status": "ok", "database": "ok"}, 200
    except Exception as e:
        return {"status": "error", "database": str(e)}, 500


# =========================================================
# 로그인
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        sync_admin()
    except Exception as e:
        return f"데이터베이스 연결 오류: {str(e)}", 500

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session.clear()
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


# =========================================================
# 대시보드
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

        all_bookings = Booking.query.order_by(
            Booking.created_at.asc()
        ).all()

        calendar_bookings = [
            {
                "id": b.id,
                "name": b.name,
                "phone": b.phone or "",
                "visit_date": b.visit_date or "",
                "device": b.device or "",
                "memo": b.memo or ""
            }
            for b in all_bookings
        ]

        today_string = str(today)
        today_bookings = [
            b for b in all_bookings
            if (b.visit_date or "")[:10] == today_string
        ]

        # 신규 판매건 오늘 요약
        today_sales = Sale.query.filter_by(sale_date=today).order_by(
            Sale.created_at.desc()
        ).all()

        return render_template(
            "dashboard.html",
            total=total,
            today_count=today_count,
            bookings=recent_bookings,
            today_bookings=today_bookings,
            calendar_bookings=calendar_bookings,
            today_sales=today_sales
        )

    except Exception as e:
        return f"데이터베이스 오류: {str(e)}", 500


# =========================================================
# 고객
# =========================================================

@app.route("/customers")
@login_required
def customers():
    prepare_database()
    q = request.args.get("q", "").strip()
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


@app.route("/customers/new", methods=["GET", "POST"])
@login_required
def customer_new():
    prepare_database()

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash("고객 이름을 입력해주세요.")
            return redirect(url_for("customer_new"))

        customer = Customer(
            name=name,
            phone=request.form.get("phone", "").strip(),
            device=request.form.get("device", "").strip(),
            carrier=request.form.get("carrier", "").strip(),
            status=request.form.get("status", "상담중").strip(),
            memo=request.form.get("memo", "").strip()
        )

        db.session.add(customer)
        db.session.commit()

        flash("고객이 등록되었습니다.")
        return redirect(url_for("customers"))

    return render_template("customer_form.html", customer=None)


@app.route("/customers/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
def customer_edit(customer_id):
    prepare_database()
    customer = Customer.query.get_or_404(customer_id)

    if request.method == "POST":
        customer.name = request.form.get("name", "").strip()
        customer.phone = request.form.get("phone", "").strip()
        customer.device = request.form.get("device", "").strip()
        customer.carrier = request.form.get("carrier", "").strip()
        customer.status = request.form.get("status", "상담중").strip()
        customer.memo = request.form.get("memo", "").strip()

        db.session.commit()

        flash("고객 정보가 수정되었습니다.")
        return redirect(url_for("customers"))

    return render_template("customer_form.html", customer=customer)


@app.route("/customers/<int:customer_id>/delete", methods=["POST"])
@login_required
@admin_required
def customer_delete(customer_id):
    prepare_database()
    customer = Customer.query.get_or_404(customer_id)

    db.session.delete(customer)
    db.session.commit()

    flash("고객 정보가 삭제되었습니다.")
    return redirect(url_for("customers"))


# =========================================================
# 예약
# =========================================================

@app.route("/bookings", methods=["GET", "POST"])
@login_required
def bookings():
    prepare_database()

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash("예약자 이름을 입력해주세요.")
            return redirect(url_for("bookings"))

        booking = Booking(
            name=name,
            phone=request.form.get("phone", "").strip(),
            visit_date=request.form.get("visit_date", "").strip(),
            device=request.form.get("device", "").strip(),
            memo=request.form.get("memo", "").strip()
        )

        db.session.add(booking)
        db.session.commit()

        flash("예약이 등록되었습니다.")
        return redirect(url_for("bookings"))

    booking_list = Booking.query.order_by(
        Booking.created_at.desc()
    ).all()

    return render_template("bookings.html", bookings=booking_list)


# =========================================================
# 신규 개통 등록
# =========================================================

@app.route("/sales/new", methods=["GET", "POST"])
@login_required
def sale_new():
    prepare_database()

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()

        if not customer_name:
            flash("고객명을 입력해주세요.")
            return redirect(url_for("sale_new"))

        sale = Sale()
        update_sale_from_form(sale)
        sale.created_by = session.get("user_id")

        db.session.add(sale)

        # 고객관리에도 자동 등록/업데이트
        customer = Customer.query.filter_by(
            phone=sale.customer_phone
        ).first() if sale.customer_phone else None

        if customer is None:
            customer = Customer(
                name=sale.customer_name,
                phone=sale.customer_phone,
                device=sale.device,
                carrier=sale.carrier,
                status="개통완료",
                memo=sale.customer_promise
            )
            db.session.add(customer)
        else:
            customer.name = sale.customer_name
            customer.device = sale.device
            customer.carrier = sale.carrier
            customer.status = "개통완료"

        db.session.commit()

        flash(f"신규 개통건 #{sale.id}이 등록되었습니다.")
        return redirect(url_for("sale_detail", sale_id=sale.id))

    return render_template(
        "sale_form.html",
        sale=None,
        today=datetime.now().strftime("%Y-%m-%d"),
        users=User.query.order_by(User.username.asc()).all()
    )


@app.route("/sales")
@login_required
def sales():
    prepare_database()

    q = request.args.get("q", "").strip()
    sale_date = request.args.get("sale_date", "").strip()
    seller = request.args.get("seller", "").strip()

    query = Sale.query

    if q:
        query = query.filter(
            db.or_(
                Sale.customer_name.contains(q),
                Sale.customer_phone.contains(q),
                Sale.device.contains(q),
                Sale.activation_number.contains(q),
                Sale.serial_number.contains(q)
            )
        )

    if sale_date:
        try:
            date_value = datetime.strptime(sale_date, "%Y-%m-%d").date()
            query = query.filter(Sale.sale_date == date_value)
        except ValueError:
            pass

    if seller:
        query = query.filter(Sale.seller == seller)

    sale_list = query.order_by(
        Sale.sale_date.desc(),
        Sale.id.desc()
    ).all()

    total_settlement = sum(s.settlement or 0 for s in sale_list)
    total_margin = sum(s.margin or 0 for s in sale_list)

    return render_template(
        "sales.html",
        sales=sale_list,
        q=q,
        sale_date=sale_date,
        seller=seller,
        total_settlement=total_settlement,
        total_margin=total_margin
    )


@app.route("/sales/<int:sale_id>")
@login_required
def sale_detail(sale_id):
    prepare_database()
    sale = Sale.query.get_or_404(sale_id)
    return render_template("sale_detail.html", sale=sale)


@app.route("/sales/<int:sale_id>/edit", methods=["GET", "POST"])
@login_required
def sale_edit(sale_id):
    prepare_database()
    sale = Sale.query.get_or_404(sale_id)

    if request.method == "POST":
        if not sale.customer_name:
            flash("고객명을 입력해주세요.")
            return redirect(url_for("sale_edit", sale_id=sale.id))

        update_sale_from_form(sale)
        db.session.commit()

        flash(f"개통건 #{sale.id}이 수정되었습니다.")
        return redirect(url_for("sale_detail", sale_id=sale.id))

    return render_template(
        "sale_form.html",
        sale=sale,
        today=sale.sale_date.strftime("%Y-%m-%d"),
        users=User.query.order_by(User.username.asc()).all()
    )


@app.route("/sales/<int:sale_id>/delete", methods=["POST"])
@login_required
@admin_required
def sale_delete(sale_id):
    prepare_database()
    sale = Sale.query.get_or_404(sale_id)

    db.session.delete(sale)
    db.session.commit()

    flash("개통건이 삭제되었습니다.")
    return redirect(url_for("sales"))


# =========================================================
# 시세표
# =========================================================

@app.route("/prices", methods=["GET", "POST"])
@login_required
def prices():
    prepare_database()

    if request.method == "POST":
        if session.get("role") != "admin":
            abort(403)

        device = request.form.get("device", "").strip()
        carrier = request.form.get("carrier", "").strip()
        sale_type = request.form.get("sale_type", "").strip()
        price = request.form.get("price", "").strip()

        if not device or not carrier or not sale_type or not price:
            flash("모든 시세 정보를 입력해주세요.")
            return redirect(url_for("prices"))

        item = Price(
            device=device,
            carrier=carrier,
            sale_type=sale_type,
            price=price
        )

        db.session.add(item)
        db.session.commit()

        flash("시세가 등록되었습니다.")
        return redirect(url_for("prices"))

    price_list = Price.query.order_by(
        Price.updated_at.desc()
    ).all()

    return render_template("prices.html", prices=price_list)


@app.route("/prices/<int:price_id>/delete", methods=["POST"])
@login_required
@admin_required
def price_delete(price_id):
    prepare_database()
    item = Price.query.get_or_404(price_id)

    db.session.delete(item)
    db.session.commit()

    flash("시세가 삭제되었습니다.")
    return redirect(url_for("prices"))


# =========================================================
# 직원 관리
# =========================================================

@app.route("/staff", methods=["GET", "POST"])
@login_required
@admin_required
def staff():
    prepare_database()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        if not username:
            flash("직원 아이디를 입력해주세요.")
            return redirect(url_for("staff"))

        if len(username) < 2:
            flash("아이디는 2자 이상 입력해주세요.")
            return redirect(url_for("staff"))

        if len(password) < 4:
            flash("비밀번호는 4자 이상 입력해주세요.")
            return redirect(url_for("staff"))

        if password != password_confirm:
            flash("비밀번호가 서로 다릅니다.")
            return redirect(url_for("staff"))

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("이미 사용 중인 아이디입니다.")
            return redirect(url_for("staff"))

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role="staff"
        )

        db.session.add(user)
        db.session.commit()

        flash(f"{username} 직원 계정이 생성되었습니다.")
        return redirect(url_for("staff"))

    staff_list = User.query.order_by(User.created_at.asc()).all()

    return render_template("staff.html", users=staff_list)


@app.route("/staff/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def staff_delete(user_id):
    prepare_database()
    user = User.query.get_or_404(user_id)

    if user.role == "admin":
        flash("관리자 계정은 삭제할 수 없습니다.")
        return redirect(url_for("staff"))

    if user.id == session.get("user_id"):
        flash("현재 로그인한 계정은 삭제할 수 없습니다.")
        return redirect(url_for("staff"))

    username = user.username

    db.session.delete(user)
    db.session.commit()

    flash(f"{username} 직원 계정이 삭제되었습니다.")
    return redirect(url_for("staff"))


@app.route("/staff/<int:user_id>/password", methods=["POST"])
@login_required
@admin_required
def staff_password(user_id):
    prepare_database()
    user = User.query.get_or_404(user_id)

    if user.role == "admin":
        flash("관리자 계정 비밀번호는 Render 환경변수에서 관리해주세요.")
        return redirect(url_for("staff"))

    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if len(new_password) < 4:
        flash("비밀번호는 4자 이상 입력해주세요.")
        return redirect(url_for("staff"))

    if new_password != confirm_password:
        flash("비밀번호가 서로 다릅니다.")
        return redirect(url_for("staff"))

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    flash(f"{user.username} 직원의 비밀번호가 변경되었습니다.")
    return redirect(url_for("staff"))


# =========================================================
# 403
# =========================================================

@app.errorhandler(403)
def forbidden(error):
    return "접근 권한이 없습니다.", 403


# =========================================================
# 실행
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000"))
    )
