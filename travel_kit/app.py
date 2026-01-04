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

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()

        if not user:
            return render_template(
                'forgot_password.html',
                error="❌ Tài khoản không tồn tại!"
            )

        session['reset_user_id'] = user.id
        return redirect(url_for('reset_password'))

    return render_template('forgot_password.html')


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_user_id' not in session:
        flash("⚠️ Phiên đặt lại mật khẩu không hợp lệ!", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm = request.form['confirm_password']

        if new_password != confirm:
            return render_template(
                'reset_password.html',
                error="❌ Mật khẩu xác nhận không khớp!"
            )

        user = User.query.get(session['reset_user_id'])
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        session.pop('reset_user_id')
        flash("✅ Đặt lại mật khẩu thành công! Hãy đăng nhập.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')



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

# Số lượng câu hỏi muốn hiển thị trên web
    NUM_QUESTIONS = 10
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
        },

        # --- 10 CÂU HỎI MỚI (Tập trung vào Hoa, Khmer, và Đa dạng VN) ---
        {
            'question': 'Điểm check-in nào sau đây là của dân tộc Hoa tại Cần Thơ?',
            'options': ['Chùa Ông', 'Chùa Pothisomron', 'Đình Bình Thủy', 'Vườn Cò Bằng Lăng'],
            'answer': 'Chùa Ông'
        },
        {
            'question': 'Dân tộc Khmer ở ĐBSCL nổi tiếng với lễ hội tôn giáo nào có phần đua thuyền truyền thống?',
            'options': ['Lễ hội Kate', 'Lễ hội Oóc Om Bóc', 'Lễ hội Cầu Ngư', 'Lễ hội Trùng Cửu'],
            'answer': 'Lễ hội Oóc Om Bóc'
        },
        {
            'question': 'Vũ điệu truyền thống nào là nét đặc trưng của dân tộc Chăm?',
            'options': ['Múa Sạp', 'Múa Xoè', 'Múa Apsara', 'Múa Quạt'],
            'answer': 'Múa Apsara'
        },
        {
            'question': 'Linh vật Naga (Rắn thần) thường được chạm khắc ở lối vào các ngôi chùa là của dân tộc nào?',
            'options': ['Dân tộc Kinh', 'Dân tộc Dao', 'Dân tộc Khmer', 'Dân tộc Thái'],
            'answer': 'Dân tộc Khmer'
        },
        {
            'question': 'Trong kiến trúc của người Hoa, màu sắc nào tượng trưng cho may mắn, tài lộc và hạnh phúc?',
            'options': ['Trắng', 'Đen', 'Đỏ', 'Xanh lam'],
            'answer': 'Đỏ'
        },
        {
            'question': 'Bộ trang phục truyền thống nào của dân tộc Kinh nổi tiếng với tà áo dài và nón lá?',
            'options': ['Áo Yếm', 'Áo Bà Ba', 'Áo Tứ Thân', 'Áo Dài'],
            'answer': 'Áo Dài'
        },
        {
            'question': 'Loại hình nghệ thuật nào của dân tộc Kinh ở miền Tây thường được biểu diễn trên ghe, xuồng?',
            'options': ['Hát Xoan', 'Hát Chèo', 'Đờn Ca Tài Tử', 'Quan Họ'],
            'answer': 'Đờn Ca Tài Tử'
        },
        {
            'question': 'Lễ hội cúng đình Thần Nguyễn Trung Trực (Rạch Giá) thể hiện nét văn hóa tâm linh của vùng nào?',
            'options': ['Tây Bắc', 'Đông Bắc', 'Đồng bằng sông Cửu Long', 'Tây Nguyên'],
            'answer': 'Đồng bằng sông Cửu Long'
        },
        {
            'question': 'Trong văn hóa Hoa, linh vật Rồng thường tượng trưng cho điều gì?',
            'options': ['Sự yên bình', 'Quyền lực và thịnh vượng', 'Sự nhẹ nhàng', 'Tính nữ'],
            'answer': 'Quyền lực và thịnh vượng'
        },
        {
            'question': 'Nhà sàn dài là kiến trúc nhà ở đặc trưng của dân tộc nào ở Tây Nguyên?',
            'options': ['Dân tộc Tày', 'Dân tộc Ê Đê', 'Dân tộc Mường', 'Dân tộc Nùng'],
            'answer': 'Dân tộc Ê Đê'
        },

        # --- 10 CÂU HỎI BỔ SUNG LẦN 2 (Mới thêm) ---
        {
            'question': 'Món ăn đặc sản nào của Cần Thơ có sự kết hợp hài hòa giữa vị béo, ngọt, mặn của thịt lợn và tôm?',
            'options': ['Bánh Xèo', 'Bánh Tét Lá Cẩm', 'Hủ Tiếu Nam Vang', 'Bún Nước Lèo'],
            'answer': 'Bánh Tét Lá Cẩm'
        },
        {
            'question': 'Vào dịp Tết Nguyên Đán, người Hoa thường treo đèn lồng màu gì để cầu mong may mắn và tài lộc?',
            'options': ['Xanh dương', 'Vàng', 'Trắng', 'Đỏ'],
            'answer': 'Đỏ'
        },
        {
            'question': 'Ngôi chùa Khmer nổi tiếng ở Cần Thơ, thường có tên gọi dựa trên loại cây mọc xung quanh là gì?',
            'options': ['Chùa Munirajabombong', 'Chùa Pothisomron (Chùa Cây Mai)', 'Chùa Khmer An Thạnh', 'Chùa Bửu Sơn'],
            'answer': 'Chùa Pothisomron (Chùa Cây Mai)'
        },
        {
            'question': 'Đặc điểm kiến trúc nào của đình Bình Thủy (Cần Thơ) thể hiện sự giao thoa văn hóa Đông – Tây?',
            'options': ['Mái lợp ngói âm dương', 'Cấu trúc nhà rường bằng gỗ', 'Mặt tiền mang kiến trúc Pháp', 'Tường xây bằng đá cuội'],
            'answer': 'Mặt tiền mang kiến trúc Pháp'
        },
        {
            'question': 'Dân tộc Khmer sử dụng nhạc cụ nào để tạo ra âm thanh chủ đạo trong các điệu múa truyền thống?',
            'options': ['Đàn Tranh', 'Cồng Chiêng', 'Dàn nhạc Ngũ âm (Pin Peat)', 'Đàn Bầu'],
            'answer': 'Dàn nhạc Ngũ âm (Pin Peat)'
        },
        {
            'question': 'Phong tục nào của người Kinh ở ĐBSCL thể hiện lòng biết ơn tổ tiên và cầu mong mùa màng bội thu?',
            'options': ['Lễ cúng ông Công ông Táo', 'Lễ hội Lồng Tồng', 'Lễ hội Nghinh Ông', 'Lễ Hạ Điền'],
            'answer': 'Lễ Hạ Điền'
        },
        {
            'question': 'Dân tộc nào ở Việt Nam có truyền thống thờ cúng Thiên Hậu Thánh Mẫu (Mazu)?',
            'options': ['Dân tộc Kinh', 'Dân tộc Hoa', 'Dân tộc Tày', 'Dân tộc Chăm'],
            'answer': 'Dân tộc Hoa'
        },
        {
            'question': 'Trong kiến trúc chùa Khmer, phần nào thường được trang trí bằng tượng chim thần Garuda và tiên nữ Apsara?',
            'options': ['Cột trụ', 'Mái vòm', 'Tường bao', 'Cổng chính và tháp'],
            'answer': 'Cổng chính và tháp'
        },
        {
            'question': 'Trang phục truyền thống của người Kinh ở miền Tây thường là loại nào, phù hợp với công việc đồng áng, sông nước?',
            'options': ['Áo dài', 'Áo the khăn xếp', 'Áo bà ba', 'Váy xòe'],
            'answer': 'Áo bà ba'
        },
        {
            'question': 'Biểu tượng "song hỷ" (囍) là nét văn hóa đặc trưng của dân tộc nào, thường dùng trong lễ cưới?',
            'options': ['Dân tộc Kinh', 'Dân tộc Hoa', 'Dân tộc Ê Đê', 'Dân tộc Mường'],
            'answer': 'Dân tộc Hoa'
        },

        # --- 20 CÂU HỎI BỔ SUNG LẦN 3 (Mới thêm) ---
        {
            'question': 'Món "Bún Nước Lèo" là đặc sản của dân tộc nào tại ĐBSCL, thường có vị mắm đặc trưng?',
            'options': ['Dân tộc Kinh', 'Dân tộc Hoa', 'Dân tộc Khmer', 'Dân tộc Chăm'],
            'answer': 'Dân tộc Khmer'
        },
        {
            'question': 'Trong nghệ thuật múa Lân - Sư - Rồng của người Hoa, vai trò của Lân chủ yếu là gì?',
            'options': ['Tượng trưng cho quyền lực', 'Tượng trưng cho sức mạnh', 'Mang lại may mắn, xua đuổi tà ma', 'Tượng trưng cho sự giàu có'],
            'answer': 'Mang lại may mắn, xua đuổi tà ma'
        },
        {
            'question': 'Làng nghề truyền thống nào ở Cần Thơ nổi tiếng với việc làm bánh hỏi, bún, và bánh tráng?',
            'options': ['Làng nghề gốm', 'Làng nghề đan lát', 'Làng nghề bánh tráng Thuận Hưng', 'Làng nghề dệt thổ cẩm'],
            'answer': 'Làng nghề bánh tráng Thuận Hưng'
        },
        {
            'question': 'Vào dịp lễ Phục sinh, người Khmer có tục lệ gì liên quan đến việc xây cồn cát ở chùa?',
            'options': ['Xây cồn cát để cầu mưa', 'Xây cồn cát để cúng thổ địa', 'Xây cồn cát để tạ lỗi với đất đai', 'Xây cồn cát để cầu phước lành, xua tan tai ương'],
            'answer': 'Xây cồn cát để cầu phước lành, xua tan tai ương'
        },
        {
            'question': 'Cổng chính của các ngôi chùa Khmer luôn quay về hướng nào?',
            'options': ['Hướng Bắc', 'Hướng Tây', 'Hướng Đông', 'Hướng Nam'],
            'answer': 'Hướng Đông'
        },
        {
            'question': 'Phong tục "Hò Xử Lý" trên sông nước miền Tây của dân tộc Kinh là loại hình nghệ thuật nào?',
            'options': ['Hát ru', 'Hát giao duyên', 'Hát đồng ca khi lao động', 'Hát tuồng'],
            'answer': 'Hát đồng ca khi lao động'
        },
        {
            'question': 'Món "Chè Trôi Nước" (thường có nhân đậu xanh) của người Hoa thường được ăn trong dịp nào?',
            'options': ['Tết Đoan Ngọ', 'Tết Nguyên Tiêu', 'Tết Thanh Minh', 'Tất cả các dịp lễ lớn'],
            'answer': 'Tết Nguyên Tiêu'
        },
        {
            'question': 'Trong kiến trúc nhà cổ Bình Thủy, họa tiết nào thường được sử dụng để trang trí gờ mái và cột nhà?',
            'options': ['Hoa sen và chim phượng', 'Rồng và cá chép', 'Cây nho và sóc', 'Tứ linh'],
            'answer': 'Cây nho và sóc'
        },
        {
            'question': 'Tác phẩm điêu khắc nào thường xuất hiện ở bậc thang lên xuống trong các chùa Khmer, tượng trưng cho sự chuyển tiếp từ trần tục lên cõi Phật?',
            'options': ['Tượng Phật', 'Tượng Apsara', 'Tượng đầu Rồng 5 hoặc 7 đầu (Naga)', 'Tượng voi 3 đầu'],
            'answer': 'Tượng đầu Rồng 5 hoặc 7 đầu (Naga)'
        },
        {
            'question': 'Điệu lý nào nổi tiếng của dân tộc Kinh ở Nam Bộ, thường được dùng để đối đáp nam nữ trên sông nước?',
            'options': ['Lý Chim Quyên', 'Lý Con Sáo', 'Lý Kéo Chài', 'Lý Tứ Đại'],
            'answer': 'Lý Con Sáo'
        },
        {
            'question': 'Loại hình kiến trúc nào của người Hoa tại Cần Thơ, thường có mái cong, trang trí rồng phụng, và thờ các vị thần Trung Quốc?',
            'options': ['Nhà sàn', 'Đình làng', 'Hội quán', 'Chùa Tháp'],
            'answer': 'Hội quán'
        },
        {
            'question': 'Lễ hội nào của người Khmer được tổ chức vào khoảng tháng 4 dương lịch, đánh dấu năm mới theo lịch cổ truyền?',
            'options': ['Tết Nguyên Đán', 'Lễ Chol Chnam Thmay', 'Lễ Vu Lan', 'Lễ Giáng Sinh'],
            'answer': 'Lễ Chol Chnam Thmay'
        },
        {
            'question': 'Đặc sản "Bánh Pía" (bánh bía) là món ăn mang đậm dấu ấn văn hóa của dân tộc nào ở miền Tây?',
            'options': ['Dân tộc Kinh', 'Dân tộc Chăm', 'Dân tộc Khmer', 'Dân tộc Hoa'],
            'answer': 'Dân tộc Hoa'
        },
        {
            'question': 'Kiểu nhà truyền thống nào của người Kinh ở Cần Thơ có kiến trúc ba gian hai chái, lợp ngói âm dương?',
            'options': ['Nhà sàn', 'Nhà rường', 'Nhà ống', 'Nhà trệt'],
            'answer': 'Nhà rường'
        },
        {
            'question': 'Trong các nghi lễ của người Khmer, vai trò của "Achar" (ông sư cả) là gì?',
            'options': ['Thợ xây chùa', 'Người quản lý tài chính', 'Người hướng dẫn nghi lễ, người truyền đạt giáo lý', 'Người trồng trọt'],
            'answer': 'Người hướng dẫn nghi lễ, người truyền đạt giáo lý'
        },
        {
            'question': 'Đặc điểm nào nổi bật trên các mái chùa của người Hoa, thể hiện quan niệm về phong thủy và tâm linh?',
            'options': ['Sử dụng mái bằng', 'Trang trí nhiều tượng thú và hoa văn gốm sứ', 'Sử dụng mái tranh', 'Lợp ngói đỏ đơn giản'],
            'answer': 'Trang trí nhiều tượng thú và hoa văn gốm sứ'
        },
        {
            'question': 'Món "Lẩu Mắm" miền Tây là sự kết hợp tinh tế của các nguyên liệu chính, trong đó mắm được chế biến từ loại cá nào?',
            'options': ['Cá rô đồng', 'Cá lóc', 'Cá sặc hoặc cá linh', 'Cá tra'],
            'answer': 'Cá sặc hoặc cá linh'
        },
        {
            'question': 'Lễ hội nào của người Kinh ở Cần Thơ thường diễn ra vào tháng Giêng âm lịch tại các đình làng để cầu an và mừng mùa màng?',
            'options': ['Lễ Tế Công', 'Lễ Thượng Điền', 'Lễ Phục Sinh', 'Lễ Vu Lan'],
            'answer': 'Lễ Thượng Điền'
        },
        {
            'question': 'Tông màu chủ đạo và nổi bật nhất trong kiến trúc chùa Khmer ở ĐBSCL là gì?',
            'options': ['Trắng và Xanh lam', 'Vàng và Đỏ/Nâu đất', 'Xanh lá và Trắng', 'Đen và Xám'],
            'answer': 'Vàng và Đỏ/Nâu đất'
        },
        {
            'question': 'Tại các chợ nổi miền Tây, vật dụng nào thường được treo trên cây sào cao (cây bẹo) để quảng cáo mặt hàng buôn bán?',
            'options': ['Lá cờ', 'Biển hiệu viết tay', 'Chính sản phẩm đó', 'Một bức tượng nhỏ'],
            'answer': 'Chính sản phẩm đó'
        },

        # --- 20 CÂU HỎI BỔ SUNG LẦN 4 (Mới thêm) ---
        {
            'question': 'Vị thần nào được thờ phụng tại Đình Bình Thủy (Cần Thơ) theo tín ngưỡng dân gian của người Kinh?',
            'options': ['Thần Nông', 'Thành Hoàng Bổn Cảnh', 'Thổ Địa', 'Quan Công'],
            'answer': 'Thành Hoàng Bổn Cảnh'
        },
        {
            'question': 'Hội quán Quảng Triệu của người Hoa ở Cần Thơ chủ yếu thờ vị thần nào?',
            'options': ['Quan Thánh Đế Quân', 'Bao Công', 'Thiên Hậu Thánh Mẫu', 'Huyền Thiên Thượng Đế'],
            'answer': 'Quan Thánh Đế Quân'
        },
        {
            'question': 'Dân tộc Khmer theo tôn giáo nào là chủ yếu, điều này chi phối kiến trúc và lễ hội của họ?',
            'options': ['Ấn Độ Giáo (Hinduism)', 'Phật giáo Đại thừa', 'Phật giáo Nguyên thủy (Theravada)', 'Thiên Chúa Giáo'],
            'answer': 'Phật giáo Nguyên thủy (Theravada)'
        },
        {
            'question': 'Hình thức ca hát nào của người Kinh ở Nam Bộ được UNESCO công nhận là Di sản văn hóa phi vật thể của nhân loại?',
            'options': ['Hát Chèo', 'Hát Xoan', 'Đờn Ca Tài Tử Nam Bộ', 'Ca Trù'],
            'answer': 'Đờn Ca Tài Tử Nam Bộ'
        },
        {
            'question': 'Trong đám cưới truyền thống của người Hoa, vật phẩm nào tượng trưng cho sự có đôi, có cặp, sum vầy?',
            'options': ['Trái cây', 'Đèn lồng, nến đỏ có hình Long Phụng', 'Hoa tươi', 'Bánh kem'],
            'answer': 'Đèn lồng, nến đỏ có hình Long Phụng'
        },
        {
            'question': 'Trong Lễ Oóc Om Bóc của người Khmer, họ thường cúng vật phẩm gì để tạ ơn Thần Mặt Trăng (Neang Khliang) đã mang lại mùa màng?',
            'options': ['Xôi đậu', 'Bánh Chưng', 'Cốm dẹp (Om Bok)', 'Trái cây nhiệt đới'],
            'answer': 'Cốm dẹp (Om Bok)'
        },
        {
            'question': 'Tác phẩm văn học dân gian nào của người Kinh ở Nam Bộ thường kể về quá trình khai phá đất đai, vật lộn với thiên nhiên?',
            'options': ['Truyện Kiều', 'Ca dao, tục ngữ về tình yêu', 'Truyện thơ Nôm', 'Các bài Vè, Hò'],
            'answer': 'Các bài Vè, Hò'
        },
        {
            'question': 'Màu sắc nào thường được người Hoa sử dụng để mặc trong tang lễ, trái ngược với màu đỏ trong lễ hội?',
            'options': ['Vàng', 'Đỏ', 'Trắng', 'Đen'],
            'answer': 'Trắng'
        },
        {
            'question': 'Đặc điểm độc đáo của nhà ở truyền thống của người Kinh ở ĐBSCL là gì, liên quan đến địa hình sông nước?',
            'options': ['Nhà sàn cao chót vót', 'Nhà có xuồng (ghe) đậu dưới hiên nhà', 'Nhà xây bằng đá', 'Nhà có nhiều tầng'],
            'answer': 'Nhà có xuồng (ghe) đậu dưới hiên nhà'
        },
        {
            'question': 'Mặt nạ Khon (Hoon) được sử dụng trong loại hình nghệ thuật nào của Khmer, mô tả các nhân vật thần thoại?',
            'options': ['Múa Apsara', 'Múa rối bóng', 'Múa mặt nạ Khon', 'Múa Sạp'],
            'answer': 'Múa mặt nạ Khon'
        },
        {
            'question': 'Cái tên "Cần Thơ" được cho là xuất phát từ tiếng Khmer có nghĩa là gì?',
            'options': ['Thành phố mới', 'Sông nước lớn', 'Dòng sông thơ', 'Cá lóc đồng'],
            'answer': 'Sông nước lớn'
        },
        {
            'question': 'Ngôi chùa cổ nào của người Hoa ở Sóc Trăng nổi tiếng với kiến trúc có nhiều tượng Phật bằng đất sét nung?',
            'options': ['Chùa Dơi', 'Chùa Đất Sét (Bửu Sơn Tự)', 'Chùa Ông', 'Chùa Khleang'],
            'answer': 'Chùa Đất Sét (Bửu Sơn Tự)'
        },
        {
            'question': 'Loại hình chợ nào đặc trưng nhất của người Kinh ở miền Tây, gắn liền với văn hóa giao thương trên sông?',
            'options': ['Chợ phiên', 'Chợ nổi', 'Chợ đêm', 'Chợ tạm'],
            'answer': 'Chợ nổi'
        },
        {
            'question': 'Trước khi có chữ Quốc ngữ, người Khmer đã sử dụng loại chữ viết nào?',
            'options': ['Chữ Hán', 'Chữ Phạn', 'Chữ Nôm', 'Chữ Khmer cổ'],
            'answer': 'Chữ Khmer cổ'
        },
        {
            'question': 'Họ tộc nào là một trong những họ tộc người Hoa lớn nhất ở Cần Thơ, có Hội quán riêng?',
            'options': ['Họ Nguyễn', 'Họ Lê', 'Họ Quảng Triệu (Quảng Đông)', 'Họ Trần'],
            'answer': 'Họ Quảng Triệu (Quảng Đông)'
        },
        {
            'question': 'Nghệ thuật đan lát (rổ, rá, chiếu) bằng các loại cây như lát, lác là nghề truyền thống của dân tộc nào ở ĐBSCL?',
            'options': ['Dân tộc Hoa', 'Dân tộc Kinh', 'Dân tộc Khmer', 'Dân tộc Chăm'],
            'answer': 'Dân tộc Kinh'
        },
        {
            'question': 'Cây cầu nào ở Cần Thơ được xem là biểu tượng kết nối hai bờ sông Hậu, hoàn thành vào năm 2010?',
            'options': ['Cầu Rạch Miễu', 'Cầu Mỹ Thuận', 'Cầu Cần Thơ', 'Cầu Hàm Luông'],
            'answer': 'Cầu Cần Thơ'
        },
        {
            'question': 'Trong Lễ hội Oóc Om Bóc, cuộc đua ghe Ngo truyền thống được tổ chức trên địa hình nào?',
            'options': ['Ao hồ', 'Sông, rạch', 'Đường bộ', 'Biển'],
            'answer': 'Sông, rạch'
        },
        {
            'question': 'Dân tộc nào có tục lệ "xin lửa" từ bếp nhà hàng xóm vào đêm Giao thừa để cầu may mắn, sung túc?',
            'options': ['Dân tộc Khmer', 'Dân tộc Tày', 'Dân tộc Kinh', 'Dân tộc Hoa'],
            'answer': 'Dân tộc Kinh'
        },
        {
            'question': 'Phương tiện giao thông nào đã trở thành biểu tượng văn hóa du lịch đặc trưng của vùng sông nước ĐBSCL?',
            'options': ['Xe đạp', 'Xe máy', 'Ghe, xuồng, tắc ráng', 'Ô tô khách'],
            'answer': 'Ghe, xuồng, tắc ráng'
        },

        # --- 30 CÂU HỎI BỔ SUNG LẦN 5 (Mới thêm) ---
        {
            'question': 'Món bánh nào của người Khmer thường được làm từ gạo nếp và dừa, có hình dáng như một chiếc lá dừa cuộn?',
            'options': ['Bánh bò', 'Bánh lá dừa', 'Bánh chuối', 'Bánh ống'],
            'answer': 'Bánh ống'
        },
        {
            'question': 'Tín ngưỡng thờ Bà Chúa Xứ gắn liền với ngọn núi nào ở An Giang, thu hút hàng triệu du khách mỗi năm?',
            'options': ['Núi Cấm', 'Núi Sam', 'Núi Bà Đen', 'Núi Dinh'],
            'answer': 'Núi Sam'
        },
        {
            'question': 'Biểu tượng vật chất nào của Cần Thơ đã từng được in trên tờ tiền 5 đồng của Việt Nam Cộng Hòa?',
            'options': ['Cầu Cần Thơ', 'Chợ nổi Cái Răng', 'Cầu Ninh Kiều', 'Tượng đài Hồ Chí Minh'],
            'answer': 'Cầu Ninh Kiều'
        },
        {
            'question': 'Hệ thống kênh rạch chằng chịt ở ĐBSCL có vai trò chủ yếu gì trong đời sống văn hóa của người dân Kinh?',
            'options': ['Chỉ dùng để nuôi trồng thủy sản', 'Là đường giao thông, thương mại, và nguồn cảm hứng nghệ thuật', 'Chỉ dùng để thoát nước lũ', 'Chỉ dùng để cung cấp nước sạch'],
            'answer': 'Là đường giao thông, thương mại, và nguồn cảm hứng nghệ thuật'
        },
        {
            'question': 'Loại trái cây nào nổi tiếng nhất Cần Thơ, gắn liền với miệt vườn Phong Điền?',
            'options': ['Sầu riêng', 'Vú sữa Lò Rèn', 'Dâu Hạ Châu', 'Thanh long'],
            'answer': 'Dâu Hạ Châu'
        },
        {
            'question': 'Trong kiến trúc Hội quán của người Hoa, "mái ngói âm dương" tượng trưng cho điều gì?',
            'options': ['Sự giàu có', 'Sự vĩnh cửu', 'Sự hài hòa âm dương', 'Sự mạnh mẽ'],
            'answer': 'Sự hài hòa âm dương'
        },
        {
            'question': 'Trang phục truyền thống của các nhà sư Khmer có màu sắc chủ đạo là gì?',
            'options': ['Trắng', 'Đỏ', 'Vàng (hoặc cam đất)', 'Xanh lam'],
            'answer': 'Vàng (hoặc cam đất)'
        },
        {
            'question': 'Võ cổ truyền nào của người Kinh ở ĐBSCL nổi tiếng với sự dũng mãnh và tính thực chiến cao?',
            'options': ['Vovinam', 'Karate', 'Bình Định Gia', 'Võ thuật cổ truyền Nam Bộ (Thất Sơn Quyền)'],
            'answer': 'Võ thuật cổ truyền Nam Bộ (Thất Sơn Quyền)'
        },
        {
            'question': 'Loại bánh ngọt truyền thống nào của người Hoa thường được làm bằng bột nếp, nhân đậu xanh và có hình tròn?',
            'options': ['Bánh chưng', 'Bánh trung thu', 'Bánh bò', 'Bánh ít'],
            'answer': 'Bánh trung thu'
        },
        {
            'question': 'Trong các điệu múa truyền thống của người Khmer, điệu múa "Robam Kandal" (Múa Tắm) tượng trưng cho điều gì?',
            'options': ['Cầu mưa', 'Sự tinh khiết, thanh cao', 'Chiến thắng', 'Lễ hội'],
            'answer': 'Sự tinh khiết, thanh cao'
        },
        {
            'question': 'Danh nhân nào được mệnh danh là "Người mở cõi" ở phương Nam, có công lớn trong việc khai phá đất Gia Định - Đồng Nai?',
            'options': ['Nguyễn Hữu Cảnh', 'Mạc Cửu', 'Nguyễn Trung Trực', 'Trịnh Hoài Đức'],
            'answer': 'Nguyễn Hữu Cảnh'
        },
        {
            'question': 'Người Hoa thường dùng loại hương (nhang) nào với kích thước lớn, màu đỏ để cúng trong các lễ lớn, đặc biệt là Tết?',
            'options': ['Hương trầm', 'Hương vòng (hương khoanh)', 'Hương cuốn', 'Hương thẻ'],
            'answer': 'Hương vòng (hương khoanh)'
        },
        {
            'question': 'Cây lúa nước, sản vật quan trọng nhất của ĐBSCL, là đối tượng thờ cúng trong tín ngưỡng nào của người Kinh?',
            'options': ['Thờ Bà Chúa Xứ', 'Thờ Thần Núi', 'Thờ Thần Nông (ông Hổ, ông Hậu)', 'Thờ Cá Ông'],
            'answer': 'Thờ Thần Nông (ông Hổ, ông Hậu)'
        },
        {
            'question': 'Lễ hội "Đua bò Bảy Núi" là hoạt động văn hóa thể thao độc đáo của dân tộc nào ở vùng An Giang?',
            'options': ['Dân tộc Kinh', 'Dân tộc Chăm', 'Dân tộc Khmer', 'Dân tộc Hoa'],
            'answer': 'Dân tộc Khmer'
        },
        {
            'question': 'Cây cầu nào ở Cần Thơ có kiến trúc hình vòng cung như cánh chim bay, là điểm nhấn nổi bật trên sông Hậu?',
            'options': ['Cầu Vàm Cống', 'Cầu Cần Thơ', 'Cầu Quang Trung', 'Cầu Hưng Lợi'],
            'answer': 'Cầu Cần Thơ'
        },
        {
            'question': 'Trong Đờn Ca Tài Tử, loại đàn nào được xem là linh hồn, thường dùng để chơi độc tấu hoặc dẫn dắt tiết tấu?',
            'options': ['Đàn Bầu', 'Đàn Kìm (Đàn Nguyệt)', 'Đàn Tranh', 'Đàn Tỳ Bà'],
            'answer': 'Đàn Kìm (Đàn Nguyệt)'
        },
        {
            'question': 'Sản vật nào của Cần Thơ được dùng để làm mứt, ngâm rượu, nổi tiếng là món quà đặc trưng của vùng này?',
            'options': ['Khóm (Dứa)', 'Củ ấu', 'Mãng cầu', 'Me'],
            'answer': 'Củ ấu'
        },
        {
            'question': 'Người Hoa thường sử dụng "phong bao lì xì" màu đỏ (hồng bao) trong dịp Tết Nguyên Đán để làm gì?',
            'options': ['Trang trí nhà cửa', 'Đựng hoa quả cúng', 'Tặng tiền mừng tuổi, cầu may mắn', 'Đựng thư từ'],
            'answer': 'Tặng tiền mừng tuổi, cầu may mắn'
        },
        {
            'question': 'Lễ hội nào của người Khmer được tổ chức vào khoảng tháng 10 âm lịch để cúng dường chư tăng và kết thúc mùa an cư kiết hạ?',
            'options': ['Lễ Dolta', 'Lễ Kathina (dâng y)', 'Lễ Chol Chnam Thmay', 'Lễ Visakha Puja'],
            'answer': 'Lễ Kathina (dâng y)'
        },
        {
            'question': 'Nét độc đáo trong việc bố trí nhà bếp của người Kinh ở miền Tây, gắn liền với việc nấu nướng trên sông nước là gì?',
            'options': ['Bếp xây bằng đá', 'Bếp đặt ở sân thượng', 'Bếp thường đặt trên ghe (xuồng)', 'Bếp sử dụng năng lượng mặt trời'],
            'answer': 'Bếp thường đặt trên ghe (xuồng)'
        },
        {
            'question': 'Chùa nào ở Sóc Trăng nổi tiếng với kiến trúc độc đáo mang phong cách kiến trúc Ấn Độ và Thái Lan, có đàn chim dơi cư ngụ?',
            'options': ['Chùa Chén Kiểu', 'Chùa Dơi (Serây Têchô Mahatúp)', 'Chùa Đất Sét', 'Chùa Pothisomron'],
            'answer': 'Chùa Dơi (Serây Têchô Mahatúp)'
        },
        {
            'question': 'Món ăn nào của người Kinh ở miền Tây được làm từ các loại lá (như lá cách, lá lốt) cuốn với thịt và mắm, mang đậm vị đồng quê?',
            'options': ['Bánh xèo', 'Gỏi cuốn', 'Lẩu mắm', 'Bánh khọt'],
            'answer': 'Gỏi cuốn'
        },
        {
            'question': 'Trong văn hóa Hoa, linh vật nào được sử dụng phổ biến trong các ngôi miếu thờ để trấn giữ và xua đuổi tà khí?',
            'options': ['Hổ', 'Sư tử đá (hay Tì Hưu)', 'Phượng hoàng', 'Rùa'],
            'answer': 'Sư tử đá (hay Tì Hưu)'
        },
        {
            'question': 'Địa danh nào ở Cần Thơ nổi tiếng với cảnh quan thiên nhiên trù phú, là nơi du khách có thể tham quan các vườn trái cây?',
            'options': ['Khu du lịch Mỹ Khánh', 'Núi Cấm', 'Hồ Xuân Hương', 'Đầm Sen'],
            'answer': 'Khu du lịch Mỹ Khánh'
        },
        {
            'question': 'Nghệ thuật sân khấu nào của người Kinh ở Nam Bộ có nguồn gốc từ tuồng, cải lương, thường được biểu diễn tại các đình làng?',
            'options': ['Múa Rối Nước', 'Hát Chèo', 'Hát Bội (Tuồng)', 'Múa rối cạn'],
            'answer': 'Hát Bội (Tuồng)'
        },
        {
            'question': 'Trong nghi lễ "cầu siêu" của người Khmer, người dân thường phóng đăng (thả đèn) trên sông để làm gì?',
            'options': ['Cầu may mắn', 'Xin Thần Sông phù hộ', 'Tưởng nhớ những người đã khuất', 'Để tìm đường đi'],
            'answer': 'Tưởng nhớ những người đã khuất'
        },
        {
            'question': 'Lễ Thượng Điền (cúng lúa mới) của người Kinh ở ĐBSCL thường được tổ chức vào thời điểm nào trong năm?',
            'options': ['Giữa mùa khô', 'Trước khi gieo sạ', 'Sau vụ mùa thu hoạch lúa', 'Đầu mùa lũ'],
            'answer': 'Sau vụ mùa thu hoạch lúa'
        },
        {
            'question': 'Bánh nào của người Hoa ở miền Tây thường được làm bằng bột mì, nhân thịt xá xíu hoặc thập cẩm, có hình tròn trắng muốt?',
            'options': ['Bánh chưng', 'Bánh bao', 'Bánh dừa', 'Bánh tiêu'],
            'answer': 'Bánh bao'
        },
        {
            'question': 'Tác phẩm điêu khắc "Apsara" trong chùa Khmer tượng trưng cho điều gì?',
            'options': ['Chiến binh', 'Nữ thần ban phước, tiên nữ', 'Quái vật', 'Người bảo vệ'],
            'answer': 'Nữ thần ban phước, tiên nữ'
        },
        {
            'question': 'Kiến trúc tôn giáo nào là trung tâm sinh hoạt văn hóa, tâm linh quan trọng nhất của cộng đồng người Khmer ở Đồng bằng sông Cửu Long, thường được xây dựng với những mái cong và chóp nhọn nhiều tầng đặc trưng?',
            'options': ['Đình làng', 'Nhà sàn truyền thống', 'Chùa Khmer (Salas)', 'Miếu Bà Chúa Xứ'],
            'answer': 'Chùa Khmer (Salas)'
        }
        
    ]

# Danh sách 100 câu hỏi về dân tộc Kinh
    questions_kinh = [
    {
        'question': 'Bến Ninh Kiều nằm bên dòng sông nào?',
        'options': ['Sông Hậu', 'Sông Tiền', 'Sông Đồng Nai', 'Sông Ba'],
        'answer': 'Sông Hậu'
    },
    {
        'question': 'Loại hình nghệ thuật nào của người Kinh ở miền Tây?',
        'options': ['Quan họ', 'Hát xoan', 'Đờn ca tài tử', 'Chèo'],
        'answer': 'Đờn ca tài tử'
    },
    {
        'question': 'Trang phục truyền thống tiêu biểu của người Kinh là gì?',
        'options': ['Áo bà ba', 'Áo yếm', 'Áo dài', 'Áo tứ thân'],
        'answer': 'Áo dài'
    },
    {
        'question': 'Tết Nguyên Đán là lễ hội quan trọng nhất của dân tộc nào?',
        'options': ['Khmer', 'Hoa', 'Kinh', 'Chăm'],
        'answer': 'Kinh'
    },
    {
        'question': 'Món bánh nào thường được làm vào dịp Tết của người Kinh?',
        'options': ['Bánh pía', 'Bánh chưng', 'Bánh tét', 'Bánh dày'],
        'answer': 'Bánh chưng'
    },
    {
        'question': 'Nhạc cụ dân gian nào gắn liền với âm nhạc truyền thống người Kinh?',
        'options': ['Cồng chiêng', 'Đàn bầu', 'Khèn', 'Sáo Mông'],
        'answer': 'Đàn bầu'
    },
    {
        'question': 'Lễ hội nào sau đây là lễ hội truyền thống của người Kinh?',
        'options': ['Oóc Om Bóc', 'Chol Chnam Thmay', 'Lễ hội Lim', 'Ramưwan'],
        'answer': 'Lễ hội Lim'
    },
    {
        'question': 'Người Kinh thường sinh sống tập trung nhiều nhất ở khu vực nào?',
        'options': ['Miền núi phía Bắc', 'Tây Nguyên', 'Đồng bằng', 'Hải đảo'],
        'answer': 'Đồng bằng'
    },
    {
        'question': 'Dân tộc Kinh còn được gọi bằng tên nào khác?',
        'options': ['Việt', 'Lạc Việt', 'Âu Việt', 'Hán Việt'],
        'answer': 'Việt'
    },
    {
        'question': 'Nhà ở truyền thống của người Kinh vùng đồng bằng thường là kiểu nhà nào?',
        'options': ['Nhà sàn', 'Nhà rông', 'Nhà đất', 'Nhà ngói'],
        'answer': 'Nhà ngói'
    },
    {
        'question': 'Phong tục thờ cúng tổ tiên là nét văn hóa đặc trưng của dân tộc nào?',
        'options': ['Hoa', 'Khmer', 'Chăm', 'Kinh'],
        'answer': 'Kinh'
    },
    {
        'question': 'Loại hình sân khấu truyền thống nổi tiếng của người Kinh là gì?',
        'options': ['Tuồng', 'Rô băm', 'Dù kê', 'Lăm vông'],
        'answer': 'Tuồng'
    },
    {
        'question': 'Làng nghề truyền thống là nét sinh hoạt phổ biến của người Kinh ở đâu?',
        'options': ['Thành thị', 'Đồng bằng', 'Vùng cao', 'Biên giới'],
        'answer': 'Đồng bằng'
    },
    {
        'question': 'Người Kinh sử dụng chữ viết nào trong sinh hoạt và học tập?',
        'options': ['Chữ Nôm', 'Chữ Quốc ngữ', 'Chữ Hán', 'Chữ Thái'],
        'answer': 'Chữ Quốc ngữ'
    },
    {
        'question': 'Tín ngưỡng nào phổ biến trong đời sống tinh thần của người Kinh?',
        'options': ['Hồi giáo', 'Thiên Chúa giáo', 'Phật giáo', 'Thờ cúng tổ tiên'],
        'answer': 'Thờ cúng tổ tiên'
    },
    {
        'question': 'Chợ nổi là nét văn hóa đặc trưng của người Kinh ở khu vực nào?',
        'options': ['Miền núi', 'Miền Trung', 'Đồng bằng sông Cửu Long', 'Tây Nguyên'],
        'answer': 'Đồng bằng sông Cửu Long'
    },
    {
        'question': 'Món phở là đặc sản ẩm thực của dân tộc nào?',
        'options': ['Khmer', 'Hoa', 'Kinh', 'Chăm'],
        'answer': 'Kinh'
    },
    {
        'question': 'Lễ Vu Lan là dịp để người Kinh thể hiện điều gì?',
        'options': ['Cầu mưa', 'Tưởng nhớ tổ tiên', 'Báo hiếu cha mẹ', 'Mừng mùa màng'],
        'answer': 'Báo hiếu cha mẹ'
    },
    {
        'question': 'Âm nhạc dân gian nào sau đây thuộc về người Kinh?',
        'options': ['Ca trù', 'Cồng chiêng', 'Khèn Mông', 'Dù kê'],
        'answer': 'Ca trù'
    },
    {
        'question': 'Trong gia đình truyền thống người Kinh, ai thường được xem là trụ cột?',
        'options': ['Người mẹ', 'Người con trưởng', 'Người cha', 'Ông bà'],
        'answer': 'Người cha'
    },
        {
        'question': 'Người Kinh chiếm tỷ lệ dân số lớn nhất ở Việt Nam khoảng bao nhiêu?',
        'options': ['Khoảng 54%', 'Khoảng 65%', 'Khoảng 75%', 'Khoảng 85%'],
        'answer': 'Khoảng 85%'
    },
    {
        'question': 'Ngày Giỗ Tổ Hùng Vương diễn ra vào thời gian nào?',
        'options': ['Mùng 1 tháng Giêng', 'Mùng 5 tháng Năm', 'Mùng 10 tháng Ba âm lịch', 'Rằm tháng Bảy'],
        'answer': 'Mùng 10 tháng Ba âm lịch'
    },
    {
        'question': 'Biểu tượng thường xuất hiện trong đình làng của người Kinh là gì?',
        'options': ['Rồng', 'Voi', 'Chim công', 'Hổ'],
        'answer': 'Rồng'
    },
    {
        'question': 'Công trình kiến trúc nào là trung tâm sinh hoạt cộng đồng của làng người Kinh?',
        'options': ['Chùa', 'Đình làng', 'Nhà rông', 'Tháp'],
        'answer': 'Đình làng'
    },
    {
        'question': 'Trong phong tục cưới hỏi người Kinh, lễ nào diễn ra trước lễ cưới?',
        'options': ['Lễ vu quy', 'Lễ rước dâu', 'Lễ ăn hỏi', 'Lễ lại mặt'],
        'answer': 'Lễ ăn hỏi'
    },
    {
        'question': 'Người Kinh ở miền Tây thường di chuyển bằng phương tiện nào?',
        'options': ['Ngựa', 'Ghe xuồng', 'Xe trâu', 'Thuyền buồm'],
        'answer': 'Ghe xuồng'
    },
    {
        'question': 'Loại hình chợ nào gắn liền với đời sống sông nước của người Kinh Nam Bộ?',
        'options': ['Chợ phiên', 'Chợ đêm', 'Chợ nổi', 'Chợ trung tâm'],
        'answer': 'Chợ nổi'
    },
    {
        'question': 'Món ăn nào thường xuất hiện trong mâm cỗ truyền thống người Kinh?',
        'options': ['Cơm lam', 'Canh chua', 'Lẩu cá', 'Cơm nếp'],
        'answer': 'Canh chua'
    },
    {
        'question': 'Nghề truyền thống nào phổ biến ở làng quê người Kinh?',
        'options': ['Làm gốm', 'Đan lát', 'Trồng lúa nước', 'Chăn nuôi du mục'],
        'answer': 'Trồng lúa nước'
    },
    {
        'question': 'Trong văn hóa người Kinh, ngày rằm thường gắn với hoạt động nào?',
        'options': ['Đi săn', 'Cúng tổ tiên', 'Cầu mưa', 'Thi đấu võ thuật'],
        'answer': 'Cúng tổ tiên'
    },
    {
        'question': 'Lễ hội đua ghe ngo ở miền Tây có sự tham gia đông đảo của người Kinh vào dịp nào?',
        'options': ['Tết Nguyên Đán', 'Lễ hội mùa xuân', 'Lễ hội sông nước', 'Oóc Om Bóc'],
        'answer': 'Oóc Om Bóc'
    },
    {
        'question': 'Kiểu mái nhà truyền thống của người Kinh thường có đặc điểm gì?',
        'options': ['Mái bằng', 'Mái vòm', 'Mái ngói dốc', 'Mái tranh tròn'],
        'answer': 'Mái ngói dốc'
    },
    {
        'question': 'Trong văn hóa ứng xử, người Kinh đề cao giá trị nào?',
        'options': ['Sức mạnh', 'Tốc độ', 'Lễ nghĩa', 'Cạnh tranh'],
        'answer': 'Lễ nghĩa'
    },
    {
        'question': 'Loại cây nào thường được trồng trước sân nhà người Kinh?',
        'options': ['Tre', 'Cau', 'Thông', 'Xương rồng'],
        'answer': 'Cau'
    },
    {
        'question': 'Người Kinh thường tổ chức giỗ chạp nhằm mục đích gì?',
        'options': ['Giải trí', 'Tưởng nhớ người đã khuất', 'Cầu tài lộc', 'Giao lưu làng xóm'],
        'answer': 'Tưởng nhớ người đã khuất'
    },
    {
        'question': 'Tập quán ăn uống truyền thống của người Kinh là gì?',
        'options': ['Ăn bốc', 'Ăn bằng tay', 'Ăn bằng đũa', 'Ăn bằng thìa'],
        'answer': 'Ăn bằng đũa'
    },
    {
        'question': 'Trong lễ cưới người Kinh, vật phẩm nào không thể thiếu?',
        'options': ['Trầu cau', 'Gạo', 'Muối', 'Nến'],
        'answer': 'Trầu cau'
    },
    {
        'question': 'Âm thanh nào thường vang lên trong các lễ hội truyền thống người Kinh?',
        'options': ['Trống', 'Chiêng', 'Kèn sừng', 'Tù và'],
        'answer': 'Trống'
    },
    {
        'question': 'Nghệ thuật múa nào thuộc về dân tộc Kinh?',
        'options': ['Múa sạp', 'Múa rối nước', 'Múa Apsara', 'Múa xoè'],
        'answer': 'Múa rối nước'
    },
    {
        'question': 'Tinh thần cộng đồng của người Kinh thể hiện rõ nhất qua hoạt động nào?',
        'options': ['Hội làng', 'Buôn bán', 'Du lịch', 'Thi đấu thể thao'],
        'answer': 'Hội làng'
    },
    {
        'question': 'Người Kinh truyền thống thường thờ cúng ai trong gia đình?',
        'options': ['Thần Núi', 'Thần Sông', 'Tổ tiên', 'Thần Lúa'],
        'answer': 'Tổ tiên'
    },
    {
        'question': 'Trong bữa cơm gia đình người Kinh, ai thường ngồi vị trí trung tâm?',
        'options': ['Con trưởng', 'Khách', 'Người lớn tuổi nhất', 'Chủ nhà'],
        'answer': 'Người lớn tuổi nhất'
    },
    {
        'question': 'Phong tục “lì xì” của người Kinh thường diễn ra vào dịp nào?',
        'options': ['Trung Thu', 'Tết Nguyên Đán', 'Tết Đoan Ngọ', 'Rằm tháng Bảy'],
        'answer': 'Tết Nguyên Đán'
    },
    {
        'question': 'Người Kinh thường gói loại bánh nào vào dịp Tết cổ truyền?',
        'options': ['Bánh pía', 'Bánh chưng', 'Bánh bò', 'Bánh da lợn'],
        'answer': 'Bánh chưng'
    },
    {
        'question': 'Trong nhà truyền thống người Kinh, bàn thờ thường đặt ở đâu?',
        'options': ['Nhà bếp', 'Gian giữa', 'Sân sau', 'Phòng ngủ'],
        'answer': 'Gian giữa'
    },
    {
        'question': 'Trong ca dao người Kinh, hình ảnh con trâu thường gắn liền với điều gì?',
        'options': ['Chiến tranh', 'Nông nghiệp', 'Buôn bán', 'Lễ hội'],
        'answer': 'Nông nghiệp'
    },
    {
        'question': 'Người Kinh thường dùng câu chào nào để thể hiện sự lễ phép?',
        'options': ['Hey!', 'Xin chào', 'Chào bác/chú/cô', 'Hello'],
        'answer': 'Chào bác/chú/cô'
    },
    {
        'question': 'Trong văn hóa người Kinh, ngày mùng Một đầu tháng thường làm gì?',
        'options': ['Đi chơi xa', 'Mua sắm lớn', 'Thắp hương cầu bình an', 'Tổ chức tiệc'],
        'answer': 'Thắp hương cầu bình an'
    },
    {
        'question': 'Tập quán sinh hoạt phổ biến của người Kinh ở nông thôn là gì?',
        'options': ['Sống du mục', 'Sống quần cư theo làng', 'Sống trên núi cao', 'Sống tách biệt'],
        'answer': 'Sống quần cư theo làng'
    },
    {
        'question': 'Người Kinh thường gọi chung quê hương sinh ra mình là gì?',
        'options': ['Bản', 'Buôn', 'Phum sóc', 'Làng quê'],
        'answer': 'Làng quê'
    },
    {
        'question': 'Trong các dịp lễ lớn, người Kinh thường mặc trang phục như thế nào?',
        'options': ['Sặc sỡ nhiều màu', 'Trang phục truyền thống hoặc chỉnh tề', 'Trang phục thể thao', 'Trang phục lao động'],
        'answer': 'Trang phục truyền thống hoặc chỉnh tề'
    },
    {
        'question': 'Người Kinh quan niệm điều gì là nền tảng của gia đình?',
        'options': ['Giàu có', 'Quyền lực', 'Hiếu thảo', 'Danh tiếng'],
        'answer': 'Hiếu thảo'
    },
    {
        'question': 'Trong sinh hoạt hàng ngày, người Kinh thường ăn mấy bữa chính?',
        'options': ['1 bữa', '2 bữa', '3 bữa', '4 bữa'],
        'answer': '3 bữa'
    },
    {
        'question': 'Người Kinh thường kiêng làm gì vào ngày đầu năm mới?',
        'options': ['Nấu ăn', 'Quét nhà', 'Đi chúc Tết', 'Mặc đồ mới'],
        'answer': 'Quét nhà'
    },
    {
        'question': 'Trong văn hóa người Kinh, câu “Uống nước nhớ nguồn” mang ý nghĩa gì?',
        'options': ['Tiết kiệm nước', 'Nhớ ơn tổ tiên và người đi trước', 'Bảo vệ môi trường', 'Giữ gìn sức khỏe'],
        'answer': 'Nhớ ơn tổ tiên và người đi trước'
    },
    {
        'question': 'Người Kinh thường tổ chức lễ mừng thọ cho ai?',
        'options': ['Trẻ em', 'Thanh niên', 'Người cao tuổi', 'Khách quý'],
        'answer': 'Người cao tuổi'
    },
    {
        'question': 'Trong gia đình truyền thống người Kinh, ai thường giữ vai trò kết nối các thành viên?',
        'options': ['Cha', 'Mẹ', 'Con trai trưởng', 'Ông bà'],
        'answer': 'Mẹ'
    },
    {
        'question': 'Người Kinh thường dạy con cái điều gì đầu tiên?',
        'options': ['Giàu nhanh', 'Lễ phép', 'Cạnh tranh', 'Mạo hiểm'],
        'answer': 'Lễ phép'
    },
    {
        'question': 'Trong văn hóa người Kinh, việc thăm hỏi hàng xóm thể hiện điều gì?',
        'options': ['Tò mò', 'Gắn kết cộng đồng', 'Nghĩa vụ bắt buộc', 'Trao đổi hàng hóa'],
        'answer': 'Gắn kết cộng đồng'
    },
    {
        'question': 'Người Kinh thường coi trọng điều gì trong lời ăn tiếng nói?',
        'options': ['Nhanh gọn', 'Hài hước', 'Lịch sự và đúng mực', 'Gay gắt'],
        'answer': 'Lịch sự và đúng mực'
    },
    {
        'question': 'Người Kinh thường dùng cách xưng hô nào để thể hiện sự kính trọng?',
        'options': ['Gọi tên riêng', 'Xưng mày – tao', 'Xưng theo vai vế gia đình', 'Xưng biệt danh'],
        'answer': 'Xưng theo vai vế gia đình'
    },
    {
        'question': 'Trong giao tiếp truyền thống, người Kinh thường tránh điều gì?',
        'options': ['Nói nhỏ', 'Cười nhẹ', 'Nói trống không', 'Chào hỏi'],
        'answer': 'Nói trống không'
    },
    {
        'question': 'Người Kinh thường coi ngày nào là thời điểm thích hợp để bắt đầu việc lớn?',
        'options': ['Ngày ngẫu nhiên', 'Ngày xấu', 'Ngày được xem là tốt', 'Ban đêm'],
        'answer': 'Ngày được xem là tốt'
    },
    {
        'question': 'Tập quán “xem ngày” của người Kinh thường áp dụng cho việc gì?',
        'options': ['Nấu ăn', 'Ngủ nghỉ', 'Cưới hỏi, xây nhà', 'Học tập'],
        'answer': 'Cưới hỏi, xây nhà'
    },
    {
        'question': 'Trong văn hóa người Kinh, câu “Lời nói chẳng mất tiền mua” khuyên điều gì?',
        'options': ['Nói thật', 'Nói khéo léo', 'Nói nhanh', 'Nói to'],
        'answer': 'Nói khéo léo'
    },
    {
        'question': 'Người Kinh thường có thói quen làm gì trước khi vào nhà người khác?',
        'options': ['Ngồi chờ', 'Gõ cửa hoặc lên tiếng', 'Vào thẳng', 'Quan sát xung quanh'],
        'answer': 'Gõ cửa hoặc lên tiếng'
    },
    {
        'question': 'Trong các dịp quan trọng, người Kinh thường coi trọng yếu tố nào nhất?',
        'options': ['Hình thức', 'Sự chân thành', 'Sự đông đủ', 'Chi phí'],
        'answer': 'Sự chân thành'
    },
    {
        'question': 'Người Kinh thường gọi chung các mối quan hệ thân quen là gì?',
        'options': ['Đồng nghiệp', 'Bà con – láng giềng', 'Khách vãng lai', 'Người xa lạ'],
        'answer': 'Bà con – láng giềng'
    },
    {
        'question': 'Trong gia đình người Kinh, việc dạy con thường bắt đầu từ điều gì?',
        'options': ['Kiến thức', 'Cách cư xử', 'Tiền bạc', 'Thể thao'],
        'answer': 'Cách cư xử'
    },
    {
        'question': 'Người Kinh thường thể hiện sự biết ơn bằng hành động nào?',
        'options': ['Im lặng', 'Tặng quà và lời cảm ơn', 'Tránh né', 'Ghi nhớ trong lòng'],
        'answer': 'Tặng quà và lời cảm ơn'
    },
    {
        'question': 'Trong văn hóa người Kinh, việc “giữ thể diện” thường liên quan đến điều gì?',
        'options': ['Ngoại hình', 'Danh dự và cách ứng xử', 'Tiền bạc', 'Địa vị'],
        'answer': 'Danh dự và cách ứng xử'
    },
    {
        'question': 'Người Kinh thường tránh làm gì khi đang có khách?',
        'options': ['Nấu ăn', 'Nghe điện thoại', 'Tranh cãi to tiếng', 'Pha trà'],
        'answer': 'Tranh cãi to tiếng'
    },
    {
        'question': 'Trong văn hóa người Kinh, “ăn nói có trước có sau” mang ý nghĩa gì?',
        'options': ['Nói nhiều', 'Nói đúng thứ tự, có chừng mực', 'Nói vòng vo', 'Nói nhanh'],
        'answer': 'Nói đúng thứ tự, có chừng mực'
    },
    {
        'question': 'Người Kinh thường có thói quen gì khi gặp người lớn tuổi?',
        'options': ['Bắt tay mạnh', 'Chào hỏi lễ phép', 'Im lặng bỏ đi', 'Cười lớn'],
        'answer': 'Chào hỏi lễ phép'
    },
    {
        'question': 'Trong sinh hoạt cộng đồng, người Kinh thường đề cao điều gì?',
        'options': ['Cạnh tranh', 'Cá nhân', 'Sự hòa thuận', 'Độc lập'],
        'answer': 'Sự hòa thuận'
    },
    {
        'question': 'Người Kinh thường sử dụng ngôn ngữ như thế nào trong gia đình?',
        'options': ['Cứng nhắc', 'Thân mật và gần gũi', 'Trang trọng quá mức', 'Ít giao tiếp'],
        'answer': 'Thân mật và gần gũi'
    },
    {
        'question': 'Trong văn hóa người Kinh, việc “nhường nhịn” thường được coi là gì?',
        'options': ['Yếu đuối', 'Thiệt thòi', 'Đức tính tốt', 'Bắt buộc'],
        'answer': 'Đức tính tốt'
    },
    {
        'question': 'Người Kinh thường quan niệm thế nào về gia đình?',
        'options': ['Không quan trọng', 'Chỉ là nơi ở', 'Nền tảng của cuộc sống', 'Gánh nặng'],
        'answer': 'Nền tảng của cuộc sống'
    },
    {
        'question': 'Trong văn hóa người Kinh, việc giữ lời hứa thể hiện điều gì?',
        'options': ['Sự thông minh', 'Uy tín cá nhân', 'Sự khéo léo', 'May mắn'],
        'answer': 'Uy tín cá nhân'
    },
    {
        'question': 'Người Kinh thường đánh giá một người qua yếu tố nào trước tiên?',
        'options': ['Ngoại hình', 'Tiền bạc', 'Cách cư xử', 'Nghề nghiệp'],
        'answer': 'Cách cư xử'
    },
    {
        'question': 'Trong sinh hoạt truyền thống, người Kinh thường ăn cơm vào thời điểm nào?',
        'options': ['Bất kỳ lúc nào', 'Theo bữa cố định trong ngày', 'Chỉ buổi tối', 'Khi có khách'],
        'answer': 'Theo bữa cố định trong ngày'
    },
    {
        'question': 'Người Kinh thường gọi khu vực sinh sống lâu đời của mình là gì?',
        'options': ['Bản', 'Buôn', 'Làng', 'Phum'],
        'answer': 'Làng'
    },
    {
        'question': 'Trong làng truyền thống của người Kinh, nơi sinh hoạt chung thường là đâu?',
        'options': ['Chợ', 'Nhà riêng', 'Đình làng', 'Ruộng đồng'],
        'answer': 'Đình làng'
    },
    {
        'question': 'Người Kinh thường tổ chức họp bàn việc chung của làng ở đâu?',
        'options': ['Nhà trưởng làng', 'Chợ', 'Đình làng', 'Sân nhà'],
        'answer': 'Đình làng'
    },
    {
        'question': 'Trong văn hóa người Kinh, việc thăm hỏi hàng xóm thường diễn ra khi nào?',
        'options': ['Khi có dịp quan trọng', 'Chỉ khi cần giúp đỡ', 'Thường xuyên, thân tình', 'Rất hiếm'],
        'answer': 'Thường xuyên, thân tình'
    },
    {
        'question': 'Người Kinh thường có tập quán gì khi chuyển đến nơi ở mới?',
        'options': ['Im lặng sinh sống', 'Chào hỏi hàng xóm', 'Tránh tiếp xúc', 'Chỉ gặp chính quyền'],
        'answer': 'Chào hỏi hàng xóm'
    },
    {
        'question': 'Trong xã hội truyền thống, người Kinh thường phân chia vai trò lao động theo yếu tố nào?',
        'options': ['Tuổi tác và giới tính', 'Sở thích cá nhân', 'May mắn', 'Ngẫu nhiên'],
        'answer': 'Tuổi tác và giới tính'
    },
    {
        'question': 'Người Kinh thường coi trọng yếu tố nào trong quan hệ láng giềng?',
        'options': ['Khoảng cách', 'Sự hòa thuận', 'Sự cạnh tranh', 'Sự giàu có'],
        'answer': 'Sự hòa thuận'
    },
    {
        'question': 'Trong văn hóa người Kinh, việc giúp đỡ nhau khi gặp khó khăn được gọi là gì?',
        'options': ['Làm phúc', 'Lá lành đùm lá rách', 'Trao đổi lợi ích', 'Trả ơn'],
        'answer': 'Lá lành đùm lá rách'
    },
    {
        'question': 'Người Kinh thường có thói quen gì khi đi xa trở về quê?',
        'options': ['Im lặng', 'Thăm họ hàng', 'Ở trong nhà', 'Tránh gặp người quen'],
        'answer': 'Thăm họ hàng'
    },
    {
        'question': 'Trong đời sống truyền thống, người Kinh thường dùng phương tiện nào để đi lại ở nông thôn?',
        'options': ['Xe máy', 'Thuyền, ghe', 'Ô tô', 'Tàu hỏa'],
        'answer': 'Thuyền, ghe'
    },
    {
        'question': 'Người Kinh thường tổ chức đám cưới theo hình thức nào?',
        'options': ['Đơn giản, riêng tư', 'Có sự tham gia của họ hàng và làng xóm', 'Chỉ gia đình nhỏ', 'Không cố định'],
        'answer': 'Có sự tham gia của họ hàng và làng xóm'
    },
    {
        'question': 'Trong văn hóa người Kinh, việc mời cơm thể hiện điều gì?',
        'options': ['Thủ tục bắt buộc', 'Sự hiếu khách', 'Hình thức xã giao', 'Thói quen cá nhân'],
        'answer': 'Sự hiếu khách'
    },
    {
        'question': 'Người Kinh thường có thói quen gì trước khi bắt đầu bữa ăn?',
        'options': ['Ăn ngay', 'Mời mọi người cùng ăn', 'Ăn riêng', 'Chờ khách'],
        'answer': 'Mời mọi người cùng ăn'
    },
    {
        'question': 'Trong sinh hoạt cộng đồng, người Kinh thường giải quyết mâu thuẫn bằng cách nào?',
        'options': ['Tranh cãi gay gắt', 'Nhờ người lớn tuổi hòa giải', 'Phớt lờ', 'Dùng pháp luật ngay'],
        'answer': 'Nhờ người lớn tuổi hòa giải'
    },
    {
        'question': 'Người Kinh thường quan niệm thế nào về việc sống chung trong cộng đồng?',
        'options': ['Ai lo việc nấy', 'Gắn bó và hỗ trợ nhau', 'Ít liên hệ', 'Cạnh tranh'],
        'answer': 'Gắn bó và hỗ trợ nhau'
    },
    {
        'question': 'Trong văn hóa người Kinh, việc giữ gìn nề nếp gia đình có ý nghĩa gì?',
        'options': ['Hình thức', 'Giữ truyền thống', 'Bắt buộc', 'Không cần thiết'],
        'answer': 'Giữ truyền thống'
    },
    {
        'question': 'Người Kinh thường truyền dạy kinh nghiệm sống cho con cháu bằng cách nào?',
        'options': ['Sách vở', 'Lời dạy và tấm gương', 'Luật lệ nghiêm khắc', 'Phần thưởng'],
        'answer': 'Lời dạy và tấm gương'
    },
    {
        'question': 'Trong đời sống người Kinh, sự đoàn kết thường thể hiện rõ nhất ở đâu?',
        'options': ['Trong công việc cá nhân', 'Trong sinh hoạt làng xóm', 'Trong học tập', 'Trong kinh doanh'],
        'answer': 'Trong sinh hoạt làng xóm'
    },
    {
        'question': 'Người Kinh thường xem điều gì là nền tảng để xã hội ổn định?',
        'options': ['Tiền bạc', 'Luật pháp', 'Gia đình và cộng đồng', 'Quyền lực'],
        'answer': 'Gia đình và cộng đồng'
    }
    ]

# Danh sách 100 câu hỏi về dân tộc Khmer
    questions_khmer = [
    {
        'question': 'Lễ hội Oóc Om Bóc là lễ hội của dân tộc nào?',
        'options': ['Kinh', 'Hoa', 'Khmer', 'Chăm'],
        'answer': 'Khmer'
    },
    {
        'question': 'Linh vật Naga thường xuất hiện ở kiến trúc nào?',
        'options': ['Chùa Kinh', 'Đình làng', 'Chùa Khmer', 'Miếu Hoa'],
        'answer': 'Chùa Khmer'
    },
    {
        'question': 'Chùa Pothisomron còn gọi là gì?',
        'options': ['Chùa Dơi', 'Chùa Cây Mai', 'Chùa Ông', 'Chùa Bà'],
        'answer': 'Chùa Cây Mai'
    },
    {
        'question': 'Dân tộc Khmer ở Việt Nam tập trung sinh sống nhiều nhất ở khu vực nào?',
        'options': ['Tây Nguyên', 'Đồng bằng sông Cửu Long', 'Đông Bắc', 'Duyên hải miền Trung'],
        'answer': 'Đồng bằng sông Cửu Long'
    },
    {
        'question': 'Ngôn ngữ truyền thống của người Khmer thuộc hệ ngôn ngữ nào?',
        'options': ['Hán – Tạng', 'Nam Đảo', 'Môn – Khmer', 'Thái – Kadai'],
        'answer': 'Môn – Khmer'
    },
    {
        'question': 'Người Khmer thường theo tôn giáo nào?',
        'options': ['Thiên Chúa giáo', 'Hồi giáo', 'Phật giáo Nam tông', 'Phật giáo Bắc tông'],
        'answer': 'Phật giáo Nam tông'
    },
    {
        'question': 'Ngôi chùa giữ vai trò quan trọng nhất trong đời sống tinh thần người Khmer là gì?',
        'options': ['Chùa làng', 'Đình làng', 'Nhà thờ', 'Miếu thờ'],
        'answer': 'Chùa làng'
    },
    {
        'question': 'Lễ hội nào của người Khmer mang ý nghĩa mừng năm mới?',
        'options': ['Oóc Om Bóc', 'Chôl Chnăm Thmây', 'Lễ hội Kate', 'Lễ Vu Lan'],
        'answer': 'Chôl Chnăm Thmây'
    },
    {
        'question': 'Trong lễ Chôl Chnăm Thmây, người Khmer thường làm gì?',
        'options': ['Cúng tổ tiên tại đình', 'Dâng cơm cho sư sãi', 'Đua ghe ngo', 'Hát quan họ'],
        'answer': 'Dâng cơm cho sư sãi'
    },
    {
        'question': 'Trang phục truyền thống của phụ nữ Khmer thường có đặc điểm gì?',
        'options': ['Màu đen đơn giản', 'Sặc sỡ, nhiều hoa văn', 'Chủ yếu màu trắng', 'Không có họa tiết'],
        'answer': 'Sặc sỡ, nhiều hoa văn'
    },
    {
        'question': 'Khăn truyền thống thường được người Khmer sử dụng gọi là gì?',
        'options': ['Khăn rằn', 'Khăn piêu', 'Khăn choàng lụa', 'Khăn xếp'],
        'answer': 'Khăn rằn'
    },
    {
        'question': 'Người Khmer thường tổ chức lễ hội đua thuyền vào dịp nào?',
        'options': ['Mùa khô', 'Mùa mưa kết thúc', 'Đầu năm mới', 'Giữa mùa hè'],
        'answer': 'Mùa mưa kết thúc'
    },
    {
        'question': 'Ghe ngo là loại thuyền truyền thống gắn liền với dân tộc nào?',
        'options': ['Kinh', 'Hoa', 'Khmer', 'Chăm'],
        'answer': 'Khmer'
    },
    {
        'question': 'Trong kiến trúc chùa Khmer, mái chùa thường có đặc điểm gì?',
        'options': ['Đơn giản, ít tầng', 'Cong vút, nhiều tầng', 'Mái bằng', 'Mái tranh'],
        'answer': 'Cong vút, nhiều tầng'
    },
    {
        'question': 'Người Khmer thường coi việc vào chùa tu tập của nam giới trẻ là gì?',
        'options': ['Không cần thiết', 'Truyền thống quan trọng', 'Chỉ dành cho người già', 'Hiếm gặp'],
        'answer': 'Truyền thống quan trọng'
    },
    {
        'question': 'Trong đời sống cộng đồng, ai là người có uy tín cao trong phum sóc Khmer?',
        'options': ['Thương nhân', 'Sư sãi', 'Quan chức', 'Người giàu'],
        'answer': 'Sư sãi'
    },
    {
        'question': 'Người Khmer thường gọi đơn vị cư trú truyền thống của mình là gì?',
        'options': ['Làng', 'Bản', 'Buôn', 'Phum sóc'],
        'answer': 'Phum sóc'
    },
    {
        'question': 'Âm nhạc truyền thống của người Khmer thường được biểu diễn trong dịp nào?',
        'options': ['Tang lễ và lễ hội', 'Chỉ trong gia đình', 'Hội chợ thương mại', 'Trường học'],
        'answer': 'Tang lễ và lễ hội'
    },
    {
        'question': 'Múa truyền thống của người Khmer thường mang ý nghĩa gì?',
        'options': ['Giải trí đơn thuần', 'Tôn giáo và tín ngưỡng', 'Thể thao', 'Thi đấu'],
        'answer': 'Tôn giáo và tín ngưỡng'
    },
    {
        'question': 'Người Khmer thường xem chùa là nơi nào trong đời sống cộng đồng?',
        'options': ['Chỉ để tham quan', 'Trung tâm văn hóa – tinh thần', 'Nơi kinh doanh', 'Nơi giải trí'],
        'answer': 'Trung tâm văn hóa – tinh thần'
    },
    
    {
        'question': 'Người Khmer thường dùng nhạc cụ nào trong sinh hoạt văn hóa?',
        'options': ['Đàn tranh', 'Trống truyền thống', 'Sáo trúc', 'Đàn bầu'],
        'answer': 'Trống truyền thống'
    },
    {
        'question': 'Trong nghệ thuật biểu diễn Khmer, múa thường kết hợp với yếu tố nào?',
        'options': ['Âm nhạc và trang phục', 'Kịch nói', 'Thơ ca', 'Hội họa'],
        'answer': 'Âm nhạc và trang phục'
    },
    {
        'question': 'Người Khmer thường ăn mừng những sự kiện quan trọng cùng ai?',
        'options': ['Gia đình và cộng đồng', 'Chỉ gia đình', 'Bạn bè xa', 'Khách du lịch'],
        'answer': 'Gia đình và cộng đồng'
    },
    {
        'question': 'Trong đời sống thường ngày, người Khmer coi trọng điều gì nhất?',
        'options': ['Tiền bạc', 'Danh vọng', 'Sự hòa thuận', 'Quyền lực'],
        'answer': 'Sự hòa thuận'
    },
    {
        'question': 'Người Khmer thường thể hiện sự tôn trọng người lớn tuổi bằng cách nào?',
        'options': ['Tránh tiếp xúc', 'Lắng nghe và làm theo lời khuyên', 'Im lặng hoàn toàn', 'Không tranh luận'],
        'answer': 'Lắng nghe và làm theo lời khuyên'
    },
    {
        'question': 'Trong sinh hoạt cộng đồng Khmer, việc giúp đỡ nhau thường diễn ra khi nào?',
        'options': ['Chỉ khi có lợi ích', 'Khi gặp khó khăn', 'Rất hiếm', 'Theo yêu cầu'],
        'answer': 'Khi gặp khó khăn'
    },
    {
        'question': 'Người Khmer thường tổ chức sinh hoạt cộng đồng ở đâu?',
        'options': ['Nhà riêng', 'Chùa hoặc sân chung', 'Trường học', 'Chợ'],
        'answer': 'Chùa hoặc sân chung'
    },
    {
        'question': 'Trong văn hóa Khmer, trẻ em thường được dạy điều gì đầu tiên?',
        'options': ['Kiếm tiền', 'Lễ phép và kính trọng', 'Cạnh tranh', 'Tự do tuyệt đối'],
        'answer': 'Lễ phép và kính trọng'
    },
    {
        'question': 'Người Khmer thường xem lao động là gì?',
        'options': ['Gánh nặng', 'Bổn phận và giá trị sống', 'Việc phụ', 'Không quan trọng'],
        'answer': 'Bổn phận và giá trị sống'
    },
    {
        'question': 'Trong cộng đồng Khmer, sự đoàn kết thường thể hiện rõ nhất khi nào?',
        'options': ['Trong lễ hội và khó khăn', 'Trong kinh doanh', 'Trong học tập', 'Trong thi đấu'],
        'answer': 'Trong lễ hội và khó khăn'
    },
    {
        'question': 'Người Khmer thường truyền lại văn hóa cho thế hệ sau bằng cách nào?',
        'options': ['Sách giáo khoa', 'Sinh hoạt cộng đồng và lễ hội', 'Mạng xã hội', 'Trường học hiện đại'],
        'answer': 'Sinh hoạt cộng đồng và lễ hội'
    },
    {
        'question': 'Trong đời sống Khmer, giá trị tinh thần thường được đặt ở vị trí nào?',
        'options': ['Sau kinh tế', 'Quan trọng hơn vật chất', 'Không đáng kể', 'Phụ thuộc hoàn cảnh'],
        'answer': 'Quan trọng hơn vật chất'
    },
    {
        'question': 'Món ăn nào sau đây là món truyền thống nổi tiếng của người Khmer Nam Bộ?',
        'options': ['Bún bò', 'Canh chua', 'Bún nước lèo', 'Phở'],
        'answer': 'Bún nước lèo'
    },
    {
        'question': 'Gia vị nào thường được sử dụng nhiều trong ẩm thực Khmer?',
        'options': ['Ớt bột', 'Mắm bò hóc', 'Nước tương', 'Giấm'],
        'answer': 'Mắm bò hóc'
    },
    {
        'question': 'Trang phục truyền thống của phụ nữ Khmer thường có đặc điểm gì?',
        'options': ['Màu tối, đơn giản', 'Nhiều hoa văn sặc sỡ', 'Chủ yếu màu trắng', 'Ít trang trí'],
        'answer': 'Nhiều hoa văn sặc sỡ'
    },
    {
        'question': 'Loại váy truyền thống phổ biến của phụ nữ Khmer được gọi là gì?',
        'options': ['Áo dài', 'Xà rông', 'Yếm', 'Áo tứ thân'],
        'answer': 'Xà rông'
    },
    {
        'question': 'Người Khmer thường dùng lịch nào trong sinh hoạt lễ truyền thống?',
        'options': ['Dương lịch', 'Âm lịch', 'Lịch Phật giáo', 'Lịch Hồi giáo'],
        'answer': 'Lịch Phật giáo'
    },
    {
        'question': 'Ngôn ngữ của người Khmer thuộc hệ ngôn ngữ nào?',
        'options': ['Hán – Tạng', 'Nam Đảo', 'Môn – Khmer', 'Ấn – Âu'],
        'answer': 'Môn – Khmer'
    },
    {
        'question': 'Nhạc cụ nào sau đây thuộc dàn nhạc truyền thống của người Khmer?',
        'options': ['Đàn bầu', 'Roneat', 'Đàn nguyệt', 'Kèn bầu'],
        'answer': 'Roneat'
    },
    {
        'question': 'Trong các buổi biểu diễn truyền thống, người Khmer thường mặc gì?',
        'options': ['Trang phục thường ngày', 'Trang phục nghi lễ truyền thống', 'Đồng phục hiện đại', 'Áo dài'],
        'answer': 'Trang phục nghi lễ truyền thống'
    },
    {
        'question': 'Nhà ở truyền thống của người Khmer thường được xây theo kiểu nào?',
        'options': ['Nhà sàn thấp', 'Nhà tầng cao', 'Nhà hang', 'Nhà mái bằng'],
        'answer': 'Nhà sàn thấp'
    },
    {
        'question': 'Vật liệu nào thường được dùng để làm nhà truyền thống của người Khmer?',
        'options': ['Bê tông', 'Gạch đá', 'Gỗ và tre', 'Kim loại'],
        'answer': 'Gỗ và tre'
    },
    {
        'question': 'Trong gia đình Khmer truyền thống, bữa ăn thường diễn ra như thế nào?',
        'options': ['Ăn riêng từng người', 'Ăn chung quây quần', 'Ăn ngoài quán', 'Không cố định'],
        'answer': 'Ăn chung quây quần'
    },
    {
        'question': 'Người Khmer thường tổ chức lễ cúng tổ tiên vào dịp nào?',
        'options': ['Cuối năm', 'Đầu năm mới', 'Khi có việc trọng đại', 'Hàng tháng'],
        'answer': 'Khi có việc trọng đại'
    },
    {
        'question': 'Trong sinh hoạt thường ngày, người Khmer thường đi lại bằng phương tiện nào?',
        'options': ['Ngựa', 'Xe điện', 'Ghe, xuồng', 'Máy bay'],
        'answer': 'Ghe, xuồng'
    },
    {
        'question': 'Nghề truyền thống nào phổ biến trong cộng đồng người Khmer?',
        'options': ['Đúc đồng', 'Dệt vải', 'Làm gốm Bát Tràng', 'Làm giấy'],
        'answer': 'Dệt vải'
    },
    {
        'question': 'Hoa văn trên trang phục Khmer thường mang ý nghĩa gì?',
        'options': ['Trang trí ngẫu nhiên', 'Biểu tượng tín ngưỡng và thiên nhiên', 'Chỉ để làm đẹp', 'Không có ý nghĩa'],
        'answer': 'Biểu tượng tín ngưỡng và thiên nhiên'
    },
    {
        'question': 'Người Khmer thường tổ chức sinh hoạt văn nghệ vào dịp nào?',
        'options': ['Ngày thường', 'Lễ hội và cưới hỏi', 'Chỉ trong trường học', 'Không bao giờ'],
        'answer': 'Lễ hội và cưới hỏi'
    },
    {
        'question': 'Trong gia đình Khmer, con cái thường được dạy điều gì khi còn nhỏ?',
        'options': ['Tự lập sớm', 'Tôn trọng gia đình', 'Cạnh tranh hơn thua', 'Chỉ học chữ'],
        'answer': 'Tôn trọng gia đình'
    },
    {
        'question': 'Người Khmer thường thể hiện sự hiếu khách như thế nào?',
        'options': ['Giữ khoảng cách', 'Mời ăn uống và trò chuyện', 'Chỉ chào hỏi', 'Không tiếp xúc'],
        'answer': 'Mời ăn uống và trò chuyện'
    },
    {
        'question': 'Trong đời sống Khmer, âm nhạc thường gắn liền với hoạt động nào?',
        'options': ['Lao động sản xuất', 'Lễ hội và nghi lễ', 'Học tập', 'Buôn bán'],
        'answer': 'Lễ hội và nghi lễ'
    },
    {
        'question': 'Giá trị nào được người Khmer coi trọng trong quan hệ gia đình?',
        'options': ['Quyền lực', 'Thứ bậc tuổi tác', 'Tự do cá nhân tuyệt đối', 'Vật chất'],
        'answer': 'Thứ bậc tuổi tác'
    },
        {
        'question': 'Người Khmer thường tổ chức lễ cưới trong thời gian nào?',
        'options': ['Mùa mưa', 'Mùa khô', 'Bất kỳ thời gian nào', 'Mùa lũ'],
        'answer': 'Mùa khô'
    },
    {
        'question': 'Trong lễ cưới Khmer, nghi thức nào mang ý nghĩa chúc phúc?',
        'options': ['Buộc chỉ cổ tay', 'Rải gạo', 'Đập chum', 'Uống rượu cần'],
        'answer': 'Buộc chỉ cổ tay'
    },
    {
        'question': 'Người Khmer thường làm lễ cúng gì khi xây nhà mới?',
        'options': ['Cúng Thổ địa', 'Cúng thần Mặt Trời', 'Cúng tổ tiên', 'Cúng Long Vương'],
        'answer': 'Cúng Thổ địa'
    },
    {
        'question': 'Trong cộng đồng Khmer, ai thường đóng vai trò hòa giải mâu thuẫn?',
        'options': ['Trưởng phum, sóc', 'Người lớn tuổi nhất', 'Công an', 'Giáo viên'],
        'answer': 'Trưởng phum, sóc'
    },
    {
        'question': 'Trò chơi dân gian nào thường xuất hiện trong lễ hội Khmer?',
        'options': ['Đánh đu', 'Kéo co', 'Bắn nỏ', 'Đua thuyền'],
        'answer': 'Kéo co'
    },
    {
        'question': 'Người Khmer thường trồng loại cây nào gắn với đời sống hàng ngày?',
        'options': ['Cây cà phê', 'Cây lúa', 'Cây chè', 'Cây cao su'],
        'answer': 'Cây lúa'
    },
    {
        'question': 'Trong lao động truyền thống, người Khmer thường gắn bó với nghề nào?',
        'options': ['Đánh bắt thủy sản', 'Khai thác mỏ', 'Luyện kim', 'Làm muối'],
        'answer': 'Đánh bắt thủy sản'
    },
    {
        'question': 'Nghệ thuật múa nào mang tính kể chuyện của người Khmer?',
        'options': ['Múa dân gian', 'Múa Lâm Thôn', 'Múa rối nước', 'Múa quạt'],
        'answer': 'Múa Lâm Thôn'
    },
    {
        'question': 'Trong biểu diễn sân khấu Khmer, nội dung thường xoay quanh chủ đề gì?',
        'options': ['Cuộc sống hiện đại', 'Truyện cổ và sử thi', 'Chiến tranh hiện đại', 'Khoa học'],
        'answer': 'Truyện cổ và sử thi'
    },
    {
        'question': 'Người Khmer thường dạy con cái điều gì thông qua truyện kể dân gian?',
        'options': ['Mưu mẹo', 'Đạo đức và nhân quả', 'Chiến thắng kẻ thù', 'Làm giàu nhanh'],
        'answer': 'Đạo đức và nhân quả'
    },
    {
        'question': 'Trong sinh hoạt cộng đồng, người Khmer thường tụ họp ở đâu?',
        'options': ['Chợ', 'Nhà riêng', 'Sân chung của phum sóc', 'Trường học'],
        'answer': 'Sân chung của phum sóc'
    },
    {
        'question': 'Người Khmer thường tổ chức lễ mừng tuổi cho ai?',
        'options': ['Trẻ nhỏ', 'Người cao tuổi', 'Tất cả mọi người', 'Chỉ nam giới'],
        'answer': 'Người cao tuổi'
    },
    {
        'question': 'Trong gia đình Khmer, ai thường giữ vai trò truyền dạy phong tục?',
        'options': ['Cha mẹ', 'Ông bà', 'Anh chị', 'Thầy giáo'],
        'answer': 'Ông bà'
    },
    {
        'question': 'Người Khmer thường thể hiện sự kính trọng bằng cách nào?',
        'options': ['Bắt tay', 'Cúi đầu nhẹ', 'Vỗ vai', 'Khoanh tay'],
        'answer': 'Khoanh tay'
    },
    {
        'question': 'Trong các buổi lễ quan trọng, người Khmer thường sử dụng vật gì để dâng cúng?',
        'options': ['Hoa và trái cây', 'Tiền giấy', 'Vàng bạc', 'Trang sức'],
        'answer': 'Hoa và trái cây'
    },
    {
        'question': 'Tín ngưỡng dân gian Khmer thường gắn với yếu tố nào?',
        'options': ['Thiên nhiên', 'Công nghệ', 'Kinh tế', 'Thể thao'],
        'answer': 'Thiên nhiên'
    },
    {
        'question': 'Người Khmer thường giữ gìn phong tục bằng cách nào?',
        'options': ['Ghi chép sách vở', 'Truyền miệng qua các thế hệ', 'Học ở trường', 'Qua mạng xã hội'],
        'answer': 'Truyền miệng qua các thế hệ'
    },
    {
        'question': 'Trong đời sống Khmer, lễ nghi thường gắn với yếu tố nào?',
        'options': ['Thời tiết', 'Chu kỳ mùa vụ', 'Lịch công tác', 'Ngày nghỉ'],
        'answer': 'Chu kỳ mùa vụ'
    },
    {
        'question': 'Người Khmer thường khuyên con cháu điều gì khi trưởng thành?',
        'options': ['Giàu có là quan trọng nhất', 'Sống hiền hòa và tôn trọng cộng đồng', 'Chỉ lo cho bản thân', 'Luôn hơn thua'],
        'answer': 'Sống hiền hòa và tôn trọng cộng đồng'
    },
    {
        'question': 'Giá trị nổi bật trong văn hóa Khmer là gì?',
        'options': ['Cạnh tranh', 'Đoàn kết cộng đồng', 'Cá nhân hóa', 'Thực dụng'],
        'answer': 'Đoàn kết cộng đồng'
    },
    {
        'question': 'Người Khmer thường dạy trẻ em kỹ năng sống đầu tiên là gì?',
        'options': ['Lao động', 'Lễ nghi', 'Học chữ', 'Giao tiếp'],
        'answer': 'Lễ nghi'
    },
    {
        'question': 'Trong gia đình Khmer, bữa ăn thường mang ý nghĩa gì?',
        'options': ['Ăn nhanh', 'Sum họp và gắn kết', 'Phân chia công việc', 'Thể hiện địa vị'],
        'answer': 'Sum họp và gắn kết'
    },
    {
        'question': 'Người Khmer thường tránh điều gì khi giao tiếp với người lớn tuổi?',
        'options': ['Nói to', 'Nhìn thẳng', 'Cười lớn', 'Ngồi cao hơn'],
        'answer': 'Ngồi cao hơn'
    },
    {
        'question': 'Trong đời sống Khmer, ngày đầu năm mới thường dành để làm gì?',
        'options': ['Lao động', 'Thăm hỏi người thân', 'Buôn bán', 'Đi xa'],
        'answer': 'Thăm hỏi người thân'
    },
    {
        'question': 'Người Khmer quan niệm thế nào về việc giúp đỡ hàng xóm?',
        'options': ['Không cần thiết', 'Là trách nhiệm cộng đồng', 'Chỉ giúp người quen', 'Phải có điều kiện'],
        'answer': 'Là trách nhiệm cộng đồng'
    },
    {
        'question': 'Nghề thủ công truyền thống nào gắn với phụ nữ Khmer?',
        'options': ['Đúc đồng', 'Dệt vải thủ công', 'Chạm khắc đá', 'Đóng thuyền'],
        'answer': 'Dệt vải thủ công'
    },
    {
        'question': 'Người Khmer thường lưu giữ lịch truyền thống bằng cách nào?',
        'options': ['Sách in', 'Truyền miệng', 'Qua chùa', 'Qua mạng'],
        'answer': 'Qua chùa'
    },
    {
        'question': 'Trong cộng đồng Khmer, việc nuôi dạy con cái là trách nhiệm của ai?',
        'options': ['Cha mẹ', 'Gia đình mở rộng', 'Nhà trường', 'Chính quyền'],
        'answer': 'Gia đình mở rộng'
    },
    {
        'question': 'Người Khmer thường chọn thời điểm nào để tổ chức việc lớn?',
        'options': ['Theo lịch cá nhân', 'Theo mùa vụ', 'Theo ngày lễ quốc gia', 'Theo thời tiết lạnh'],
        'answer': 'Theo mùa vụ'
    },
    {
        'question': 'Trong sinh hoạt thường ngày, người Khmer coi trọng điều gì nhất?',
        'options': ['Tiền bạc', 'Sự hòa thuận', 'Danh vọng', 'Cạnh tranh'],
        'answer': 'Sự hòa thuận'
    },
    {
        'question': 'Người Khmer thường truyền lại kiến thức dân gian bằng hình thức nào?',
        'options': ['Viết sách', 'Kể chuyện', 'Hội thảo', 'Giảng dạy chính thức'],
        'answer': 'Kể chuyện'
    },
    {
        'question': 'Trong văn hóa Khmer, việc giữ lời hứa được xem là gì?',
        'options': ['Bình thường', 'Danh dự cá nhân', 'Không quan trọng', 'Tùy hoàn cảnh'],
        'answer': 'Danh dự cá nhân'
    },
    {
        'question': 'Người Khmer thường làm gì để giáo dục con cái về đạo đức?',
        'options': ['Kỷ luật nghiêm khắc', 'Làm gương', 'Phạt nặng', 'So sánh'],
        'answer': 'Làm gương'
    },
    {
        'question': 'Trong quan niệm Khmer, sống ích kỷ sẽ dẫn đến điều gì?',
        'options': ['Thành công', 'Bị cộng đồng xa lánh', 'Giàu có', 'Không ảnh hưởng'],
        'answer': 'Bị cộng đồng xa lánh'
    },
    {
        'question': 'Người Khmer thường tránh làm gì trong các dịp lễ?',
        'options': ['Cãi vã', 'Ăn uống', 'Ca hát', 'Thăm hỏi'],
        'answer': 'Cãi vã'
    },
    {
        'question': 'Trong gia đình Khmer, ai thường là người kể chuyện cho trẻ nhỏ?',
        'options': ['Cha mẹ', 'Ông bà', 'Anh chị', 'Thầy giáo'],
        'answer': 'Ông bà'
    },
    {
        'question': 'Người Khmer coi việc giữ gìn truyền thống là trách nhiệm của ai?',
        'options': ['Người già', 'Toàn cộng đồng', 'Chính quyền', 'Nhà chùa'],
        'answer': 'Toàn cộng đồng'
    },
    {
        'question': 'Trong đời sống Khmer, sự chia sẻ thể hiện rõ nhất ở đâu?',
        'options': ['Trong gia đình', 'Trong lễ hội', 'Trong lao động chung', 'Tất cả các đáp án'],
        'answer': 'Tất cả các đáp án'
    },
    {
        'question': 'Người Khmer thường đánh giá một người tốt dựa trên điều gì?',
        'options': ['Giàu có', 'Học vấn', 'Cách đối xử với mọi người', 'Địa vị'],
        'answer': 'Cách đối xử với mọi người'
    },
    {
        'question': 'Giá trị cốt lõi trong văn hóa ứng xử của người Khmer là gì?',
        'options': ['Khoan dung', 'Tham vọng', 'Cạnh tranh', 'Cá nhân'],
        'answer': 'Khoan dung'
    }
    ]

# Danh sách 100 câu hỏi về dân tộc Hoa
    questions_hoa = [
    {
        'question': 'Điểm check-in tiêu biểu của người Hoa ở Cần Thơ là?',
        'options': ['Chùa Ông', 'Chùa Dơi', 'Nhà cổ Bình Thủy', 'Đình Thần'],
        'answer': 'Chùa Ông'
    },
    {
        'question': 'Màu sắc tượng trưng cho may mắn trong văn hóa Hoa?',
        'options': ['Trắng', 'Đen', 'Đỏ', 'Xanh'],
        'answer': 'Đỏ'
    },
    {
        'question': 'Linh vật Rồng trong văn hóa Hoa tượng trưng cho?',
        'options': ['Sự yên bình', 'Quyền lực và thịnh vượng', 'Tình yêu', 'Sự mềm mại'],
        'answer': 'Quyền lực và thịnh vượng'
    },
        {
        'question': 'Người Hoa thường tổ chức Tết lớn nhất trong năm vào dịp nào?',
        'options': ['Tết Trung Thu', 'Tết Nguyên Đán', 'Tết Đoan Ngọ', 'Tết Thanh Minh'],
        'answer': 'Tết Nguyên Đán'
    },
    {
        'question': 'Trong Tết của người Hoa, món ăn nào tượng trưng cho sự sung túc?',
        'options': ['Bánh chưng', 'Bánh bao', 'Sủi cảo', 'Bánh tét'],
        'answer': 'Sủi cảo'
    },
    {
        'question': 'Người Hoa thường dùng ngôn ngữ nào trong sinh hoạt truyền thống?',
        'options': ['Tiếng Việt', 'Tiếng Quan Thoại', 'Tiếng Quảng Đông', 'Tiếng Anh'],
        'answer': 'Tiếng Quảng Đông'
    },
    {
        'question': 'Phong tục nào thể hiện sự hiếu kính tổ tiên của người Hoa?',
        'options': ['Cúng đình', 'Thờ cúng gia tiên', 'Cúng cô hồn', 'Cúng đất'],
        'answer': 'Thờ cúng gia tiên'
    },
    {
        'question': 'Người Hoa thường treo câu đối đỏ vào dịp nào?',
        'options': ['Lễ Vu Lan', 'Tết Nguyên Đán', 'Tết Trung Thu', 'Rằm tháng Bảy'],
        'answer': 'Tết Nguyên Đán'
    },
    {
        'question': 'Trong văn hóa Hoa, số nào được xem là may mắn?',
        'options': ['Số 4', 'Số 7', 'Số 8', 'Số 13'],
        'answer': 'Số 8'
    },
    {
        'question': 'Nghề truyền thống phổ biến của cộng đồng người Hoa ở Nam Bộ là gì?',
        'options': ['Đánh cá', 'Buôn bán', 'Làm ruộng', 'Khai thác gỗ'],
        'answer': 'Buôn bán'
    },
    {
        'question': 'Lễ hội nào của người Hoa gắn liền với trăng tròn?',
        'options': ['Tết Trung Thu', 'Tết Nguyên Đán', 'Tết Đoan Ngọ', 'Lễ Thanh Minh'],
        'answer': 'Tết Trung Thu'
    },
    {
        'question': 'Trong đám cưới người Hoa, màu sắc chủ đạo thường là gì?',
        'options': ['Trắng', 'Đỏ', 'Xanh', 'Đen'],
        'answer': 'Đỏ'
    },
    {
        'question': 'Người Hoa quan niệm điều gì quan trọng nhất trong gia đình?',
        'options': ['Tiền bạc', 'Danh vọng', 'Sự hòa thuận', 'Quyền lực'],
        'answer': 'Sự hòa thuận'
    },
    {
        'question': 'Tập quán nào giúp gắn kết cộng đồng người Hoa?',
        'options': ['Họp chợ', 'Hội quán', 'Làm lễ riêng lẻ', 'Du lịch'],
        'answer': 'Hội quán'
    },
    {
        'question': 'Người Hoa thường kiêng điều gì trong ngày đầu năm mới?',
        'options': ['Ăn uống', 'Quét nhà', 'Chúc Tết', 'Mặc đồ mới'],
        'answer': 'Quét nhà'
    },
    {
        'question': 'Trong văn hóa Hoa, đèn lồng thường tượng trưng cho điều gì?',
        'options': ['Tang tóc', 'Ánh sáng và may mắn', 'Chiến tranh', 'Sự cô đơn'],
        'answer': 'Ánh sáng và may mắn'
    },
    {
        'question': 'Món ăn nào thường xuất hiện trong mâm cúng của người Hoa?',
        'options': ['Bún bò', 'Hủ tiếu', 'Bánh xèo', 'Cơm lam'],
        'answer': 'Hủ tiếu'
    },
    {
        'question': 'Trong gia đình người Hoa, ai thường giữ vai trò quyết định?',
        'options': ['Con út', 'Người lớn tuổi', 'Hàng xóm', 'Con trưởng'],
        'answer': 'Người lớn tuổi'
    },
    {
        'question': 'Người Hoa thường dạy con cháu điều gì quan trọng nhất?',
        'options': ['Kiếm tiền', 'Giữ chữ tín', 'Học võ', 'Đi xa'],
        'answer': 'Giữ chữ tín'
    },
    {
        'question': 'Giá trị đạo đức nổi bật trong văn hóa người Hoa là gì?',
        'options': ['Cạnh tranh', 'Tham vọng', 'Chữ tín', 'Cá nhân'],
        'answer': 'Chữ tín'
    },
        {
        'question': 'Người Hoa thường thờ vị thần nào để cầu buôn may bán đắt?',
        'options': ['Thần Tài', 'Thần Nông', 'Thổ Địa', 'Táo Quân'],
        'answer': 'Thần Tài'
    },
    {
        'question': 'Trong văn hóa Hoa, mèo thần Maneki Neko tượng trưng cho điều gì?',
        'options': ['Xua đuổi tà ma', 'Bảo vệ gia đình', 'Thu hút tài lộc', 'Cầu sức khỏe'],
        'answer': 'Thu hút tài lộc'
    },
    {
        'question': 'Người Hoa thường treo gương bát quái với mục đích gì?',
        'options': ['Trang trí nhà cửa', 'Xua đuổi tà khí', 'Thể hiện giàu có', 'Ghi nhớ tổ tiên'],
        'answer': 'Xua đuổi tà khí'
    },
    {
        'question': 'Trong phong tục Hoa, con số nào bị xem là không may?',
        'options': ['Số 1', 'Số 4', 'Số 6', 'Số 9'],
        'answer': 'Số 4'
    },
    {
        'question': 'Ngày Thanh Minh của người Hoa gắn liền với hoạt động nào?',
        'options': ['Đua thuyền', 'Tảo mộ', 'Cầu mưa', 'Rước đèn'],
        'answer': 'Tảo mộ'
    },
    {
        'question': 'Người Hoa thường tránh tặng món quà nào vì mang ý nghĩa chia ly?',
        'options': ['Trái cây', 'Đồng hồ', 'Trà', 'Bánh'],
        'answer': 'Đồng hồ'
    },
    {
        'question': 'Trong văn hóa Hoa, chim Phượng Hoàng tượng trưng cho điều gì?',
        'options': ['Chiến tranh', 'Sự tái sinh và cao quý', 'Sự cô đơn', 'Tai họa'],
        'answer': 'Sự tái sinh và cao quý'
    },
    {
        'question': 'Trang phục truyền thống của phụ nữ Hoa thường được gọi là gì?',
        'options': ['Áo dài', 'Sườn xám', 'Áo bà ba', 'Áo tứ thân'],
        'answer': 'Sườn xám'
    },
    {
        'question': 'Người Hoa thường tổ chức lễ mừng thọ cho người cao tuổi vào độ tuổi nào?',
        'options': ['50 tuổi', '60 tuổi', '70 tuổi', '80 tuổi'],
        'answer': '60 tuổi'
    },
    {
        'question': 'Trong văn hóa Hoa, việc đặt tên cho con thường tránh điều gì?',
        'options': ['Tên ngắn', 'Tên giống người lớn tuổi', 'Tên tiếng Anh', 'Tên có dấu'],
        'answer': 'Tên giống người lớn tuổi'
    },
    {
        'question': 'Người Hoa tin rằng hướng nhà ảnh hưởng đến yếu tố nào?',
        'options': ['Sức khỏe và tài lộc', 'Chiều cao', 'Tuổi thọ', 'Giới tính con cái'],
        'answer': 'Sức khỏe và tài lộc'
    },
    {
        'question': 'Trong các dịp lễ lớn, người Hoa thường đốt gì để cầu bình an?',
        'options': ['Nhang và vàng mã', 'Nến thơm', 'Gỗ trầm', 'Lá bưởi'],
        'answer': 'Nhang và vàng mã'
    },
    {
        'question': 'Người Hoa quan niệm ăn cá trong lễ quan trọng mang ý nghĩa gì?',
        'options': ['No đủ quanh năm', 'Xua đuổi xui xẻo', 'Gia đình đông con', 'Trường thọ'],
        'answer': 'No đủ quanh năm'
    },
    {
        'question': 'Trong đám cưới người Hoa, trà thường được dùng để làm gì?',
        'options': ['Giải khát', 'Cúng thần', 'Ra mắt và kính lễ gia đình', 'Trang trí'],
        'answer': 'Ra mắt và kính lễ gia đình'
    },
    {
        'question': 'Người Hoa thường tránh làm gì trong ngày cưới?',
        'options': ['Mặc đồ sặc sỡ', 'Khóc', 'Ăn uống', 'Chụp ảnh'],
        'answer': 'Khóc'
    },
    {
        'question': 'Lễ Đoan Ngọ trong văn hóa Hoa thường diễn ra vào tháng nào âm lịch?',
        'options': ['Tháng 3', 'Tháng 5', 'Tháng 7', 'Tháng 9'],
        'answer': 'Tháng 5'
    },
    {
        'question': 'Người Hoa thường dùng bánh nào trong lễ Đoan Ngọ?',
        'options': ['Bánh tro', 'Bánh dày', 'Bánh chưng', 'Bánh ít'],
        'answer': 'Bánh tro'
    },
    {
        'question': 'Trong văn hóa Hoa, treo chữ “Phúc” ngược mang ý nghĩa gì?',
        'options': ['Sai sót', 'Phúc đã đến nhà', 'Xui xẻo', 'Trang trí'],
        'answer': 'Phúc đã đến nhà'
    },
    {
        'question': 'Người Hoa rất coi trọng điều gì trong quan hệ làm ăn?',
        'options': ['Hình thức', 'Quan hệ lâu dài', 'Cạnh tranh', 'May rủi'],
        'answer': 'Quan hệ lâu dài'
    },
    {
        'question': 'Tín ngưỡng nào ảnh hưởng mạnh đến đời sống tinh thần của người Hoa?',
        'options': ['Nho giáo', 'Hồi giáo', 'Thiên Chúa giáo', 'Ấn Độ giáo'],
        'answer': 'Nho giáo'
    },
    {
        'question': 'Người Hoa tại Việt Nam thường sử dụng ngôn ngữ nào trong sinh hoạt cộng đồng?',
        'options': ['Tiếng Quảng Đông', 'Tiếng Thái', 'Tiếng Lào', 'Tiếng Khmer'],
        'answer': 'Tiếng Quảng Đông'
    },
    {
        'question': 'Người Hoa thường lập hội quán với mục đích chính là gì?',
        'options': ['Giải trí', 'Hỗ trợ đồng hương', 'Buôn bán', 'Thờ cúng riêng'],
        'answer': 'Hỗ trợ đồng hương'
    },
    {
        'question': 'Trong gia đình người Hoa, ai thường được xem là trụ cột tinh thần?',
        'options': ['Con trai út', 'Người lớn tuổi nhất', 'Con gái cả', 'Người giàu nhất'],
        'answer': 'Người lớn tuổi nhất'
    },
    {
        'question': 'Người Hoa thường dạy con cháu điều gì quan trọng nhất?',
        'options': ['Giàu nhanh', 'Hiếu thảo với cha mẹ', 'Cạnh tranh mạnh mẽ', 'Sống tự do'],
        'answer': 'Hiếu thảo với cha mẹ'
    },
    {
        'question': 'Trong văn hóa Hoa, bữa cơm gia đình mang ý nghĩa gì?',
        'options': ['Ăn cho no', 'Thể hiện địa vị', 'Gắn kết các thế hệ', 'Nghi thức tôn giáo'],
        'answer': 'Gắn kết các thế hệ'
    },
    {
        'question': 'Người Hoa thường treo câu đối trước cửa nhà vào dịp nào?',
        'options': ['Lễ Vu Lan', 'Tết Nguyên Đán', 'Rằm tháng Bảy', 'Lễ Trung Thu'],
        'answer': 'Tết Nguyên Đán'
    },
    {
        'question': 'Trong văn hóa Hoa, việc thờ cúng tổ tiên thường diễn ra ở đâu?',
        'options': ['Ngoài sân', 'Gian giữa ngôi nhà', 'Nhà bếp', 'Phòng ngủ'],
        'answer': 'Gian giữa ngôi nhà'
    },
    {
        'question': 'Người Hoa quan niệm thế nào về việc giữ chữ tín?',
        'options': ['Không quan trọng', 'Chỉ cần với người thân', 'Rất quan trọng', 'Tùy hoàn cảnh'],
        'answer': 'Rất quan trọng'
    },
    {
        'question': 'Trong sinh hoạt cộng đồng, người Hoa thường đề cao yếu tố nào?',
        'options': ['Cá nhân', 'Gia đình', 'Cộng đồng', 'Danh tiếng cá nhân'],
        'answer': 'Cộng đồng'
    },
    {
        'question': 'Người Hoa thường chọn nghề nào khi mới lập nghiệp tại Việt Nam?',
        'options': ['Nông nghiệp', 'Buôn bán nhỏ', 'Khai thác mỏ', 'Đánh cá'],
        'answer': 'Buôn bán nhỏ'
    },
    {
        'question': 'Trong văn hóa Hoa, việc đặt bàn thờ tổ tiên thể hiện điều gì?',
        'options': ['Sự giàu có', 'Lòng biết ơn nguồn cội', 'Tín ngưỡng mê tín', 'Trang trí nhà cửa'],
        'answer': 'Lòng biết ơn nguồn cội'
    },
    {
        'question': 'Người Hoa thường dạy con cháu cách ứng xử như thế nào với hàng xóm?',
        'options': ['Giữ khoảng cách', 'Hòa nhã và tôn trọng', 'Chỉ giao tiếp khi cần', 'Tránh tiếp xúc'],
        'answer': 'Hòa nhã và tôn trọng'
    },
    {
        'question': 'Trong các dịp quan trọng, người Hoa thường ưu tiên điều gì?',
        'options': ['Hình thức', 'Sự đoàn tụ gia đình', 'Quà cáp đắt tiền', 'Trang trí cầu kỳ'],
        'answer': 'Sự đoàn tụ gia đình'
    },
    {
        'question': 'Người Hoa quan niệm thế nào về việc làm ăn lâu dài?',
        'options': ['Chỉ cần lợi nhuận nhanh', 'Cạnh tranh quyết liệt', 'Bền vững và uy tín', 'Không cần kế hoạch'],
        'answer': 'Bền vững và uy tín'
    },
    {
        'question': 'Trong văn hóa Hoa, vai trò của người mẹ trong gia đình là gì?',
        'options': ['Chăm sóc con cái', 'Quản lý tài chính', 'Giữ gìn nếp nhà', 'Tất cả đều đúng'],
        'answer': 'Tất cả đều đúng'
    },
    {
        'question': 'Người Hoa thường tổ chức các hoạt động cộng đồng vào dịp nào?',
        'options': ['Ngày thường', 'Dịp lễ truyền thống', 'Cuối tuần', 'Mùa mưa'],
        'answer': 'Dịp lễ truyền thống'
    },
    {
        'question': 'Trong văn hóa Hoa, việc kính trọng thầy cô bắt nguồn từ tư tưởng nào?',
        'options': ['Phật giáo', 'Nho giáo', 'Đạo giáo', 'Tín ngưỡng dân gian'],
        'answer': 'Nho giáo'
    },
    {
        'question': 'Người Hoa thường khuyên con cháu sống theo nguyên tắc nào?',
        'options': ['Ích kỷ', 'Thực dụng', 'Nhân – Lễ – Nghĩa', 'Tự do tuyệt đối'],
        'answer': 'Nhân – Lễ – Nghĩa'
    },
    {
        'question': 'Trong đời sống người Hoa, việc giữ truyền thống có ý nghĩa gì?',
        'options': ['Lạc hậu', 'Gắn kết các thế hệ', 'Cản trở phát triển', 'Không cần thiết'],
        'answer': 'Gắn kết các thế hệ'
    },
    {
        'question': 'Người Hoa tại Việt Nam thường sinh sống tập trung ở đâu?',
        'options': ['Vùng núi', 'Khu ven biển', 'Khu đô thị và buôn bán', 'Vùng sâu vùng xa'],
        'answer': 'Khu đô thị và buôn bán'
    },
    {
        'question': 'Người Hoa thường sử dụng loại lịch nào để xem ngày tốt – xấu?',
        'options': ['Dương lịch', 'Âm lịch', 'Lịch Phật giáo', 'Lịch nông nghiệp'],
        'answer': 'Âm lịch'
    },
    {
        'question': 'Trong bữa tiệc của người Hoa, món ăn thường được bày theo hình gì để tượng trưng cho sự trọn vẹn?',
        'options': ['Hình vuông', 'Hình tròn', 'Hình tam giác', 'Hình chữ nhật'],
        'answer': 'Hình tròn'
    },
    {
        'question': 'Người Hoa thường tránh làm việc lớn vào thời điểm nào?',
        'options': ['Ngày mưa', 'Ngày trăng tròn', 'Ngày bị xem là xấu', 'Ngày cuối tuần'],
        'answer': 'Ngày bị xem là xấu'
    },
    {
        'question': 'Trong văn hóa Hoa, việc mời trà thể hiện điều gì?',
        'options': ['Sự hiếu khách', 'Sự giàu có', 'Nghi lễ tôn giáo', 'Thói quen hằng ngày'],
        'answer': 'Sự hiếu khách'
    },
    {
        'question': 'Người Hoa thường kiêng điều gì trong ngày đầu năm?',
        'options': ['Ăn uống', 'Quét nhà', 'Thăm họ hàng', 'Mặc đồ mới'],
        'answer': 'Quét nhà'
    },
    {
        'question': 'Trong kiến trúc nhà ở truyền thống của người Hoa, sân trong có tác dụng gì?',
        'options': ['Trang trí', 'Lấy ánh sáng và thông gió', 'Nuôi gia súc', 'Chứa nước'],
        'answer': 'Lấy ánh sáng và thông gió'
    },
    {
        'question': 'Người Hoa thường dùng loại nhang nào khi cúng lễ?',
        'options': ['Nhang vòng', 'Nhang trầm', 'Nhang điện tử', 'Nhang thảo mộc'],
        'answer': 'Nhang trầm'
    },
    {
        'question': 'Trong văn hóa Hoa, số lượng món ăn trong mâm cỗ thường mang ý nghĩa gì?',
        'options': ['Ngẫu nhiên', 'Tượng trưng cho may mắn', 'Theo mùa', 'Theo sở thích'],
        'answer': 'Tượng trưng cho may mắn'
    },
    {
        'question': 'Người Hoa thường treo gương bát quái với mục đích gì?',
        'options': ['Trang trí', 'Xua đuổi tà khí', 'Làm đẹp nhà', 'Thể hiện địa vị'],
        'answer': 'Xua đuổi tà khí'
    },
    {
        'question': 'Trong bữa ăn truyền thống của người Hoa, thứ tự mời ăn thể hiện điều gì?',
        'options': ['Tuổi tác và vai vế', 'Giới tính', 'Nghề nghiệp', 'Sự giàu nghèo'],
        'answer': 'Tuổi tác và vai vế'
    },
    {
        'question': 'Người Hoa thường chọn hướng nhà dựa trên yếu tố nào?',
        'options': ['Phong thủy', 'Gần chợ', 'Gần sông', 'Theo sở thích'],
        'answer': 'Phong thủy'
    },
    {
        'question': 'Trong văn hóa Hoa, việc treo tranh chữ mang ý nghĩa gì?',
        'options': ['Trang trí', 'Nhắc nhở đạo lý sống', 'Thể hiện giàu có', 'Làm quà tặng'],
        'answer': 'Nhắc nhở đạo lý sống'
    },
    {
        'question': 'Người Hoa thường tổ chức mừng thọ cho ai?',
        'options': ['Trẻ em', 'Người trung niên', 'Người cao tuổi', 'Bạn bè'],
        'answer': 'Người cao tuổi'
    },
    {
        'question': 'Trong văn hóa Hoa, việc chọn tên cho con thường dựa vào yếu tố nào?',
        'options': ['Phong thủy và ý nghĩa chữ', 'Xu hướng hiện đại', 'Tên người nổi tiếng', 'Sở thích cá nhân'],
        'answer': 'Phong thủy và ý nghĩa chữ'
    },
    {
        'question': 'Người Hoa thường tránh nói điều gì trong dịp lễ?',
        'options': ['Lời chúc', 'Chuyện buồn, xui xẻo', 'Chuyện làm ăn', 'Chuyện gia đình'],
        'answer': 'Chuyện buồn, xui xẻo'
    },
    {
        'question': 'Trong sinh hoạt thường ngày, người Hoa coi trọng điều gì nhất?',
        'options': ['Tiết kiệm', 'Ăn ngon', 'Ăn mặc', 'Giải trí'],
        'answer': 'Tiết kiệm'
    },
    {
        'question': 'Người Hoa thường dạy con cháu cách quản lý tiền bạc như thế nào?',
        'options': ['Chi tiêu thoải mái', 'Tiết kiệm và tính toán', 'Không cần quan tâm', 'Phụ thuộc gia đình'],
        'answer': 'Tiết kiệm và tính toán'
    },
    {
        'question': 'Trong văn hóa Hoa, việc mời khách ở lại ăn cơm thể hiện điều gì?',
        'options': ['Xã giao', 'Sự thân tình', 'Nghĩa vụ', 'Hình thức'],
        'answer': 'Sự thân tình'
    },
    {
        'question': 'Người Hoa thường chuẩn bị gì trước khi khai trương cửa hàng?',
        'options': ['Trang trí đơn giản', 'Xem ngày giờ tốt', 'Giảm giá', 'Mời ca sĩ'],
        'answer': 'Xem ngày giờ tốt'
    },
    {
        'question': 'Trong văn hóa Hoa, việc giữ lời hứa có ý nghĩa gì?',
        'options': ['Không quan trọng', 'Thể hiện nhân cách', 'Chỉ mang tính xã giao', 'Tùy đối tượng'],
        'answer': 'Thể hiện nhân cách'
    },
        {
        'question': 'Người Hoa thường sinh sống tập trung ở khu vực nào tại các đô thị?',
        'options': ['Khu chợ', 'Khu công nghiệp', 'Vùng ven biển', 'Vùng núi'],
        'answer': 'Khu chợ'
    },
    {
        'question': 'Tết quan trọng nhất của người Hoa là dịp nào?',
        'options': ['Tết Trung thu', 'Tết Nguyên Đán', 'Tết Thanh minh', 'Tết Đoan ngọ'],
        'answer': 'Tết Nguyên Đán'
    },
    {
        'question': 'Người Hoa thường treo câu đối vào dịp nào?',
        'options': ['Đám cưới', 'Tết', 'Đám tang', 'Lễ hội mùa màng'],
        'answer': 'Tết'
    },
    {
        'question': 'Ngôn ngữ truyền thống của người Hoa tại Việt Nam thuộc nhóm nào?',
        'options': ['Hán – Tạng', 'Nam Á', 'Thái – Kadai', 'Nam Đảo'],
        'answer': 'Hán – Tạng'
    },
    {
        'question': 'Món ăn nào thường xuất hiện trong các dịp lễ của người Hoa?',
        'options': ['Bánh chưng', 'Bánh bao', 'Bánh tét', 'Bánh ít'],
        'answer': 'Bánh bao'
    },
    {
        'question': 'Họ phổ biến của người Hoa tại Việt Nam là?',
        'options': ['Nguyễn', 'Trần', 'Lý', 'Trương'],
        'answer': 'Trương'
    },
    {
        'question': 'Người Hoa thường thờ cúng ai trong gia đình?',
        'options': ['Thổ địa', 'Gia tiên', 'Thành hoàng', 'Sơn thần'],
        'answer': 'Gia tiên'
    },
    {
        'question': 'Tết Trung thu của người Hoa gắn liền với hình ảnh nào?',
        'options': ['Bánh chưng', 'Bánh trung thu', 'Bánh giầy', 'Bánh tét'],
        'answer': 'Bánh trung thu'
    },
    {
        'question': 'Trang trí lồng đèn có ý nghĩa gì trong văn hóa Hoa?',
        'options': ['Trang trí nhà cửa', 'Xua đuổi tà ma', 'Cầu mong đoàn viên', 'Trang trí mùa vụ'],
        'answer': 'Cầu mong đoàn viên'
    },
    {
        'question': 'Hoạt động múa nào thường thấy trong lễ hội của người Hoa?',
        'options': ['Múa sạp', 'Múa lân', 'Múa xoè', 'Múa trống'],
        'answer': 'Múa lân'
    },
    {
        'question': 'Người Hoa thường kinh doanh mạnh trong lĩnh vực nào?',
        'options': ['Nông nghiệp', 'Buôn bán', 'Lâm nghiệp', 'Ngư nghiệp'],
        'answer': 'Buôn bán'
    },
    {
        'question': 'Phong tục mừng tuổi đầu năm của người Hoa gọi là gì?',
        'options': ['Lì xì', 'Mừng thọ', 'Phát lộc', 'Cầu phúc'],
        'answer': 'Lì xì'
    },
    {
        'question': 'Con số nào được xem là mang ý nghĩa tốt trong văn hóa Hoa?',
        'options': ['4', '7', '8', '13'],
        'answer': '8'
    },
    {
        'question': 'Trang phục truyền thống của người Hoa thường là?',
        'options': ['Áo dài', 'Sườn xám', 'Áo bà ba', 'Áo tứ thân'],
        'answer': 'Sườn xám'
    },
    {
        'question': 'Người Hoa thường tránh con số nào vì mang ý nghĩa xấu?',
        'options': ['3', '4', '6', '9'],
        'answer': '4'
    },
    {
        'question': 'Trong gia đình người Hoa, ai thường được coi trọng nhất?',
        'options': ['Con út', 'Con trưởng', 'Con gái', 'Con nuôi'],
        'answer': 'Con trưởng'
    },
    {
        'question': 'Lễ Thanh minh của người Hoa mang ý nghĩa gì?',
        'options': ['Cầu mùa', 'Tảo mộ', 'Mừng năm mới', 'Cầu duyên'],
        'answer': 'Tảo mộ'
    },
    {
        'question': 'Ẩm thực người Hoa nổi bật với đặc điểm nào?',
        'options': ['Ít gia vị', 'Nhiều dầu mỡ', 'Vị chua cay', 'Ăn sống'],
        'answer': 'Nhiều dầu mỡ'
    },
    {
        'question': 'Người Hoa thường treo gì trước cửa nhà để cầu bình an?',
        'options': ['Chuông gió', 'Câu đối', 'Gương bát quái', 'Đèn dầu'],
        'answer': 'Gương bát quái'
    },
    {
        'question': 'Văn hóa người Hoa chịu ảnh hưởng mạnh từ tư tưởng nào?',
        'options': ['Phật giáo', 'Nho giáo', 'Thiên chúa giáo', 'Hồi giáo'],
        'answer': 'Nho giáo'
    }
    ]


    # Xử lý khi người dùng gửi bài
    if request.method == 'POST':
        user = User.query.get(session['user_id'])
        score = 0

        # Đọc dữ liệu câu hỏi từ form

        questions = json.loads(request.form['questions_json'])
        # So sánh kết quả
        for i, q in enumerate(questions):
            # user_answer = request.form.get(f'question_{i}')
            if request.form.get(f'question_{i}') == q['answer']:
            # if user_answer == q['answer']:
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
    # questions = base_questions.copy()
    # random.shuffle(questions)

    # Lấy ngẫu nhiên 10 câu hỏi từ danh sách tổng

        # ====== XỬ LÝ HIỂN THỊ QUIZ (GET) ======
    quiz_type = request.args.get('type', 'general')

    if quiz_type == 'kinh':
        pool = questions_kinh
    elif quiz_type == 'khmer':
        pool = questions_khmer
    elif quiz_type == 'hoa':
        pool = questions_hoa
    else:
        pool = base_questions

    try:
        questions = random.sample(pool, min(NUM_QUESTIONS, len(pool)))
    except ValueError:
        questions = pool.copy()

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

@app.route("/rewards")
def rewards():
    return render_template("rewards.html")

# @app.route("/lucky_wheel")
# def lucky_wheel():
#     return render_template("lucky_wheel.html")


# --- Chạy app ---
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
