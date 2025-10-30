# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
from io import BytesIO
import base64
import json, random
from datetime import datetime

# --- Khởi tạo Flask ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel_kit.db'
app.config['SECRET_KEY'] = 'supersecretkey'
db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    badge = db.Column(db.String(50), default=None)  # 🏅 Huy hiệu người chơi

class CheckIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    location = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# # --- Hàm tạo QR code ---
# def generate_qr(location_id):
#     # Chuyển location_id về dạng URL-friendly
#     url_map = {
#         "Ben_Ninh_Kieu": "ben-ninh-kieu",
#         "Cau_Di_Bo": "cau-di-bo",
#         "Nha_Co_Binh_Thuy": "nha-co-binh-thuy",
#         "Cho_Noi_Cai_Rang": "cho-noi-cai-rang",
#         "Den_Vua_Hung": "den-vua-hung"
#     }
#     # URL đầy đủ cho check-in
#     url = f"http://172.16.3.40:5000/{url_map.get(location_id, 'ben-ninh-kieu')}"
#     qr = qrcode.QRCode(box_size=5, border=2)
#     qr.add_data(url)
#     qr.make(fit=True)
#     img = qr.make_image(fill_color="black", back_color="white")
#     buf = BytesIO()
#     img.save(buf)
#     buf.seek(0)
#     img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
#     return f"data:image/png;base64,{img_base64}"

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash("⚠️ Tên tài khoản đã tồn tại. Vui lòng chọn tên khác.", "warning")
            return redirect(url_for('register'))
        user = User(username=username, password_hash=password)
        db.session.add(user)
        db.session.commit()

        flash("🎉 Đăng ký thành công! Bạn có thể đăng nhập ngay.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            error = "❌ Sai tên đăng nhập hoặc mật khẩu!"
            # Vẫn render lại login.html với biến error
            return render_template('login.html', error=error, username=username)
    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    
    # # Sinh QR code cho các địa điểm check-in (Kinh)
    # locations = ['Ben_Ninh_Kieu', 'Cau_Di_Bo', 'Nha_Co_Binh_Thuy', 'Cho_Noi_Cai_Rang', 'Den_Vua_Hung']
    # qr_codes = {loc: generate_qr(loc) for loc in locations}
    
    return render_template('dashboard.html', user=user)

@app.route('/checkin/<location_id>')
def checkin(location_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    
    # Kiểm tra xem đã check-in trước chưa (có thể thêm sau)
    
    ci = CheckIn(user_id=user.id, location=location_id)
    db.session.add(ci)
    user.points += 10  # cộng điểm mỗi lần check-in
    db.session.commit()
    
    return f"Check-in tại {location_id} thành công! Điểm hiện tại: {user.points} <br><a href='{url_for('dashboard')}'>Quay lại Dashboard</a>"

# @app.route('/minigame')
# def minigame():
#     if 'user_id' not in session:
#         return redirect(url_for('login'))
#     user = User.query.get(session['user_id'])
#     reward = random.choice([5, 10, 15, 20])
#     user.points += reward
#     db.session.commit()
#     return f"Bạn nhận được {reward} điểm từ mini-game! Tổng điểm: {user.points} <br><a href='{url_for('dashboard')}'>Quay lại Dashboard</a>"

@app.route('/ben-ninh-kieu')
def ben_ninh_kieu():
    return render_template('ben_ninh_kieu.html')

@app.route('/cau-di-bo')
def cau_di_bo():
    return render_template('cau_di_bo.html')

@app.route('/nha-co-binh-thuy')
def nha_co_binh_thuy():
    return render_template('nha_co_binh_thuy.html')

@app.route('/cho-noi-cai-rang')
def cho_noi_cai_rang():
    return render_template('cho_noi_cai_rang.html')

@app.route('/den-vua-hung')
def den_vua_hung():
    return render_template('den_vua_hung.html')

# --- Địa điểm của dân tộc Khmer ---
@app.route('/chua-pothisomron')
def chua_pothisomron():
    return render_template('chua_pothisomron.html')

@app.route("/chua_muniransay")
def chua_muniransay():
    return render_template("chua_muniransay.html")

@app.route("/chua_doi")
def chua_doi():
    return render_template("chua_doi.html")

@app.route("/chua_som_rong")
def chua_som_rong():
    return render_template("chua_som_rong.html")

@app.route("/chua_chen_kieu")
def chua_chen_kieu():
    return render_template("chua_chen_kieu.html")

# Địa điểm của dân tộc Hoa

@app.route("/chua_ong")
def chua_ong():
    return render_template("chua_ong.html")

@app.route("/hiep_thien_cung")
def hiep_thien_cung():
    return render_template("hiep_thien_cung.html")

@app.route("/tiem_che_huu_hoa")
def tiem_che_huu_hoa():
    return render_template("tiem_che_huu_hoa.html")

@app.route("/chua_ba_thien_hau")
def chua_ba_thien_hau():
    return render_template("chua_ba_thien_hau.html")

@app.route("/quan_thanh_de_co_mieu_quang_dong")
def quan_thanh_de_co_mieu_quang_dong():
    return render_template("quan_thanh_de_co_mieu_quang_dong.html")

@app.route('/minigame', methods=['GET', 'POST'])
def minigame():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    base_questions = [
        {
            'question': 'Người H’mông thường sinh sống ở vùng nào của Việt Nam?',
            'options': ['Đồng bằng sông Cửu Long', 'Tây Nguyên', 'Vùng núi phía Bắc', 'Duyên hải miền Trung'],
            'answer': 'Vùng núi phía Bắc'
        },
        {
            'question': 'Lễ hội đâm trâu là nét văn hóa đặc trưng của dân tộc nào?',
            'options': ['Ba Na', 'Kinh', 'Thái', 'Tày'],
            'answer': 'Ba Na'
        },
        {
            'question': 'Nhạc cụ đàn tính là của dân tộc nào?',
            'options': ['Tày – Nùng', 'Chăm', 'Khơ Me', 'Ê Đê'],
            'answer': 'Tày – Nùng'
        },
        {
            'question': 'Cần Thơ có câu ca “Cần Thơ gạo trắng nước trong, ai đi đến đó…” tiếp theo là gì?',
            'options': ['Cũng lòng không muốn về', 'Đều nhớ thương hoài', 'Muốn ở lại luôn', 'Ngại ngần không rời'],
            'answer': 'Cũng lòng không muốn về'
        },
        {
            'question': 'Bến Ninh Kiều nằm bên dòng sông nào?',
            'options': ['Sông Hậu', 'Sông Tiền', 'Sông Đồng Nai', 'Sông Ba'],
            'answer': 'Sông Hậu'
        },
        {
            'question': 'Du khách có thể trải nghiệm loại hình du lịch độc đáo nào ở chợ nổi Cái Răng?',
            'options': ['Du lịch sinh thái trên rừng', 'Tham quan bằng thuyền', 'Leo núi mạo hiểm', 'Khám phá hang động'],
            'answer': 'Tham quan bằng thuyền'
        },
        {
            'question': 'Vườn cò Bằng Lăng ở Cần Thơ là nơi nổi tiếng vì điều gì?',
            'options': ['Cánh đồng hoa hướng dương', 'Đàn cò tụ hội hàng ngàn con', 'Lễ hội đua ghe ngo', 'Khu nghỉ dưỡng suối nước nóng'],
            'answer': 'Đàn cò tụ hội hàng ngàn con'
        },
        {
            'question': 'Nhà cổ Bình Thủy nổi tiếng với điều gì?',
            'options': ['Kiến trúc Pháp cổ và bối cảnh phim', 'Lễ hội trái cây', 'Ẩm thực dân gian', 'Chùa cổ lâu đời'],
            'answer': 'Kiến trúc Pháp cổ và bối cảnh phim'
        },
        {
            'question': 'Đặc sản “Ốc nướng tiêu” phổ biến ở vùng nào?',
            'options': ['Đồng bằng sông Cửu Long', 'Tây Bắc', 'Miền Trung', 'Hà Nội'],
            'answer': 'Đồng bằng sông Cửu Long'
        },
        {
            'question': 'Cầu đi bộ Cần Thơ nổi tiếng về điều gì?',
            'options': ['Hình dáng cánh sen và đèn LED đổi màu', 'Chiều dài kỷ lục Việt Nam', 'Được xây bằng gỗ quý', 'Nối liền hai tỉnh'],
            'answer': 'Hình dáng cánh sen và đèn LED đổi màu'
        }
        
    ]

    # Xử lý khi người dùng gửi bài
    if request.method == 'POST':
        user = User.query.get(session['user_id'])
        score = 0

        # Đọc dữ liệu câu hỏi từ form
        questions_json = request.form.get('questions_json')
        questions = json.loads(questions_json)
        if isinstance(questions, str):
            questions = json.loads(questions)

        # So sánh kết quả
        for i, q in enumerate(questions):
            user_answer = request.form.get(f'question_{i}')
            if user_answer == q['answer']:
                score += 10

        # Cập nhật điểm
        user.points += score

         # 🏅 Cấp huy hiệu dựa vào điểm
        if score >= 90:
            user.badge = "🌟 Nhà nghiên cứu văn hoá Việt"
        elif score >= 80:
            user.badge = "🎖️ Chuyên gia văn hoá miền Tây"
        elif score >= 60:
            user.badge = "🥉 Am hiểu văn hoá Việt"
        else:
            user.badge = "✨ Người mới khám phá"

        db.session.commit()

        return render_template(
            'quiz_result.html',
            score=score,
            total=len(questions) * 10,
            user_points=user.points,
            badge=user.badge  # 👈 Truyền huy hiệu sang giao diện
        )

    # GET – hiển thị quiz
    questions = base_questions.copy()
    random.shuffle(questions)

    return render_template('quiz.html', questions=questions)


@app.route('/guide')
def guide():
    return render_template('guide.html')

@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return dict(current_user=user)
    return dict(current_user=None)

@app.route('/profile')
def profile():
    if not session.get('user_id'):
        flash('Vui lòng đăng nhập để xem thông tin cá nhân.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)


# --- Chạy app ---
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
