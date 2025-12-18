from flask import Flask, redirect, url_for, render_template, request, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ------------------- Config -------------------
app.secret_key = 'kapikapi123'  # Session için secret key
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Fotoğraf uzantılarının geçerli olup olmadığını kontrol eden fonksiyon
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------- Kullanıcı Bilgileri -------------------
# Bu örnekte, veritabanı kullanılmıyor ve kullanıcı bilgileri session'da saklanıyor.
users = {}

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/gonder")
def send():
    return render_template('send.html')

@app.route("/takip")
def track():
    return render_template('track.html')

@app.route("/kurye-ol")
def courier():
    return render_template('courier.html')

# ------------------- Login -------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        sifre = request.form['password']

        # Kullanıcıyı email ile bul
        user = users.get(email)

        # Eğer kullanıcı yoksa veya şifre yanlışsa
        if not user or not check_password_hash(user['password'], sifre):
            return "Email veya şifre yanlış", 400

        # Kullanıcıyı oturumda tanımla
        session['user_id'] = email
        session['user_name'] = user['fullname']
        session['email'] = email
        session['phone'] = user['phone']
        session['user_type'] = user['user_type']  # Kullanıcı tipini session'a kaydet
        session['profile_image'] = user.get('profile_image', 'static/uploads/default.jpg')  # Fotoğraf bilgisi
        
        # Giriş başarılıysa, kullanıcıyı profile sayfasına yönlendir
        return redirect(url_for('profile'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  
    return redirect(url_for('login')) 

# ------------------- Register -------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        ad = request.form['fullname']
        email = request.form['email']
        sifre = request.form['password']
        sifre_tekrar = request.form['password_repeat']
        tel = request.form['phone']
        user_type = request.form['user_type'] 
        plate = request.form.get('plate') if user_type == 'kurye' else None
    
        profile_image = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                profile_image = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(profile_image)
           
        # Eğer kullanıcı kurye ise, plaka alanını kontrol et
        if user_type == 'kurye' and not plate:
            flash('Araç plakasını girmelisiniz!', 'error')
            return redirect(url_for('register'))

        
        # Fotoğrafı kaydet (session'a)
        session['profile_image'] = profile_image or 'static/uploads/default.jpg'

        # Şifrelerin eşleşip eşleşmediğini kontrol et
        if sifre != sifre_tekrar:
            return "Şifreler eşleşmiyor", 400

        # Eğer kullanıcı daha önce kayıt olmuşsa, hata mesajı göster
        if email in users:
            return "Bu email zaten kayıtlı", 400

        # Şifreyi hash'le
        hashed_password = generate_password_hash(sifre, method='pbkdf2:sha256')

        # Yeni kullanıcıyı kaydet (veritabanı yerine sadece `users` dictionary'sine)
        users[email] = {
            'fullname': ad,
            'email': email,
            'password': hashed_password,
            'phone': tel,
            'user_type': user_type,
            'profile_image': profile_image,
            'user_plate': plate  # Plaka bilgisi
        }

        # Kullanıcı bilgilerini session'a kaydet
        session['user_id'] = email
        session['user_name'] = ad
        session['email'] = email
        session['phone'] = tel
        session['user_type'] = user_type   
        session['user_plate'] = plate if user_type == 'kurye' else None  # Kurye ise plaka bilgisi kaydedilir

        return redirect(url_for('login'))  

    return render_template('register.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Eğer giriş yapılmamışsa login sayfasına yönlendir

    # Kullanıcı bilgilerini session'dan al
    user = {
        'user_name': session.get('user_name', 'Ziyaretçi'),
        'user_email': session.get('email', 'email@domain.com'),
        'user_phone': session.get('phone', '0000000000'),
        'user_image': session.get('profile_image', 'static/uploads/default.jpg'),
        'user_plate': session.get('user_plate', ''),  # Plaka bilgisi session'dan alınıyor
    }

    # Kullanıcı tipi kontrolü
    user_type = session.get('user_type', 'customer')  # 'customer' veya 'courier' olabilir

    # Geçmiş siparişler
    past_orders = session.get('past_orders', [
        {"id": 1, "date": "2025-11-15", "status": "Teslim Edilecek"},  # Müşteri için teslim edilecek
        {"id": 2, "date": "2025-12-01", "status": "Teslim Edilecek"}   # Müşteri için teslim edilecek
    ])

    # Eğer kullanıcı kurye ise, sipariş durumunu 'Teslim Edilecek' olarak değiştir
    if user_type == 'kurye':
        for order in past_orders:
            order['status'] = "Teslimatlar"  # Kurye için teslimatlar başlığı

    return render_template('profile.html', user=user, past_orders=past_orders, user_type=user_type)

# ------------------- Edit Profile -------------------
@app.route("/edit_profile", methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        # Eğer kullanıcı giriş yapmamışsa login sayfasına yönlendir
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = {
        'fullname': session.get('user_name', 'Ziyaretçi'),
        'email': session.get('email', 'email@domain.com'),
        'phone': session.get('phone', '0000000000'),
        'profile_image': session.get('profile_image', 'static/uploads/default.jpg')  # Varsayılan profil fotoğrafı
    }  # 'user' verisi olarak session'dan alınan bilgilerle bir sözlük oluşturuyoruz

    if request.method == "POST":
        # Formdan gelen verilerle kullanıcıyı güncelle
        user['fullname'] = request.form['fullname']
        user['email'] = request.form['email']
        user['phone'] = request.form['phone']
        
        # Güncellenen bilgileri session'a kaydedin
        session['user_name'] = user['fullname']
        session['email'] = user['email']
        session['phone'] = user['phone']
        
        # Fotoğraf değiştirildiyse, yeni fotoğrafı kaydedin
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                profile_image = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(profile_image)
                user['profile_image'] = profile_image
                session['profile_image'] = profile_image  # Fotoğrafı session'a kaydedin

        return redirect(url_for('profile'))  # Profil sayfasına yönlendir

    return render_template('edit_profile.html', user=user)  # 'user' verisini şablona gönder


# ------------------- Main -------------------
if __name__ == "__main__":
    app.run(debug=True)
