from flask import Flask, redirect, url_for, render_template, request, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid

app = Flask(__name__, template_folder='templates', static_folder='static')

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

# ------------------- Gönderiler -------------------
# Gönderiler için veri yapısı
shipments = {}
shipment_counter = 0

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/gonder")
def send():
    # Gönderi oluştur sayfası kaldırıldı, profil sayfasına yönlendir
    if 'user_id' in session:
        return redirect(url_for('profile'))
    return redirect(url_for('home'))

@app.route("/takip")
def track():
    return render_template('track.html')

@app.route("/kurye-ol")
def courier():
    # Giriş yapılmamışsa login'e yönlendir
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Kurye değilse ana sayfaya yönlendir
    if session.get('user_type') != 'kurye':
        return redirect(url_for('home'))
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
        
        # Giriş başarılıysa, kurye ise gönderi kabul ekranına, değilse profile'a yönlendir
        if user['user_type'] == 'kurye':
            return redirect(url_for('courier'))
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
    user_type = session.get('user_type', 'musteri')  # 'musteri' veya 'kurye' olabilir

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

# ------------------- API Endpoints -------------------

# Gönderi oluşturma
@app.route('/api/shipments', methods=['POST'])
def create_shipment():
    try:
        data = request.get_json()
        
        # Validasyon
        required_fields = ['sender_name', 'sender_phone', 'sender_address', 
                          'receiver_name', 'receiver_phone', 'receiver_address',
                          'package_size', 'package_weight']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} alanı zorunludur.'}), 400
        
        global shipment_counter
        shipment_counter += 1
        
        # Takip numarası oluştur
        year = datetime.now().year
        tracking_number = f'KT-{year}-{str(shipment_counter).zfill(5)}'
        
        # Ücret hesaplama
        base_price = 40
        size_multiplier = {'Küçük': 1, 'Orta': 1.5, 'Büyük': 2}
        weight_multiplier = max(1, float(data['package_weight']) * 0.1)
        estimated_price = int(base_price * size_multiplier.get(data['package_size'], 1) * weight_multiplier)
        
        # Yeni gönderi oluştur
        shipment_id = str(uuid.uuid4())
        new_shipment = {
            'id': shipment_id,
            'tracking_number': tracking_number,
            'sender_name': data['sender_name'],
            'sender_phone': data['sender_phone'],
            'sender_address': data['sender_address'],
            'receiver_name': data['receiver_name'],
            'receiver_phone': data['receiver_phone'],
            'receiver_address': data['receiver_address'],
            'package_size': data['package_size'],
            'package_weight': float(data['package_weight']),
            'notes': data.get('notes', ''),
            'price': estimated_price,
            'status': 'pending',
            'courier_id': None,
            'courier_name': None,
            'created_at': datetime.now().isoformat(),
            'accepted_at': None,
            'delivered_at': None
        }
        
        shipments[shipment_id] = new_shipment
        
        return jsonify({
            'success': True,
            'message': 'Gönderi başarıyla oluşturuldu!',
            'shipment': new_shipment
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Bekleyen gönderileri listele
@app.route('/api/shipments/pending', methods=['GET'])
def get_pending_shipments():
    try:
        pending = [s for s in shipments.values() if s['status'] == 'pending']
        return jsonify({
            'success': True,
            'shipments': pending
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Gönderiyi kabul et
@app.route('/api/shipments/<shipment_id>/accept', methods=['POST'])
def accept_shipment(shipment_id):
    try:
        # Giriş kontrolü
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Giriş yapmanız gerekiyor.'}), 401
        
        # Kurye kontrolü
        if session.get('user_type') != 'kurye':
            return jsonify({'success': False, 'message': 'Bu işlem için kurye olmanız gerekiyor.'}), 403
        
        # Gönderiyi bul
        shipment = shipments.get(shipment_id)
        if not shipment:
            return jsonify({'success': False, 'message': 'Gönderi bulunamadı.'}), 404
        
        # Gönderi durumu kontrolü
        if shipment['status'] != 'pending':
            return jsonify({'success': False, 'message': 'Bu gönderi zaten kabul edilmiş veya işlenmiş.'}), 400
        
        # Gönderiyi güncelle
        shipment['status'] = 'accepted'
        shipment['courier_id'] = session['user_id']
        shipment['courier_name'] = session['user_name']
        shipment['accepted_at'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'message': 'Gönderi başarıyla kabul edildi!',
            'shipment': shipment
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ------------------- Main -------------------
if __name__ == "__main__":
    app.run(debug=True)
