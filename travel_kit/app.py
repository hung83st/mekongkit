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
    # questions = base_questions.copy()
    # random.shuffle(questions)

    # Lấy ngẫu nhiên 10 câu hỏi từ danh sách tổng
    try:
        # 🎲 Chọn ngẫu nhiên 10 câu hỏi từ danh sách base_questions
        questions = random.sample(base_questions, NUM_QUESTIONS)
    except ValueError:
        # Xử lý nếu chưa có đủ 10 câu hỏi
        questions = base_questions.copy()

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
