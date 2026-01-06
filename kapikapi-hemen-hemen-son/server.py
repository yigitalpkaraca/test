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

# ------------------- Mesajlaşma -------------------
# Mesajlaşma için veri yapısı (shipment_id bazında)
# Format: {shipment_id: [{"id": uuid, "sender_id": email, "sender_name": name, "message": text, "timestamp": iso}, ...]}
messages = {}

# Kullanıcıların son okuduğu mesaj sayısı (okunmamış mesaj sayısı için)
# Format: {shipment_id: {user_id: last_read_count}}
last_read_messages = {}

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/send", methods=['GET', 'POST'])
def send():
    
    # 1. Kullanıcı giriş yapmamışsa login sayfasına yönlendir
        if 'user_id' not in session:
            return redirect(url_for('login'))

        # 2. Eğer form gönderildiyse (POST işlemi)
        if request.method == 'POST':
            # Form verilerini al (Önceki cevaptaki kodların aynısı)
            yeni_siparis = {
                "id": 1000 + len(session.get('past_orders', [])) + 1,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "status": "Hazırlanıyor",
                "details": {
                    "sender": request.form.get('sender_name'),
                    "receiver": request.form.get('receiver_name'),
                    "package": request.form.get('package_size')
                }
            }
            
            # Session'a kaydet
            current_orders = session.get('past_orders', [])
            current_orders.append(yeni_siparis)
            session['past_orders'] = current_orders
            
            

        # 3. Sayfayı görüntüle (Gerekli olan kısım burası)
        return render_template('send.html')
        # Gönderi oluştur sayfası kaldırıldı, profil sayfasına yönlendir
    
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

@app.route("/chat/<shipment_id>")
def chat(shipment_id):
    # Giriş kontrolü
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Gönderiyi bul
    shipment = shipments.get(shipment_id)
    if not shipment:
        flash('Gönderi bulunamadı.', 'error')
        return redirect(url_for('profile'))
    
    # Yetki kontrolü - sadece gönderici veya kurye erişebilir
    user_id = session['user_id']
    user_type = session.get('user_type')
    
    # Gönderici kontrolü - müşteri her zaman kendi gönderilerine erişebilir
    is_sender = shipment.get('sender_email') == user_id
    # Kurye kontrolü - kurye pending gönderilere de erişebilir (kabul etmeden önce)
    # veya kabul ettiği gönderilere erişebilir
    is_courier = (user_type == 'kurye' and 
                  (shipment.get('status') == 'pending' or 
                   shipment.get('courier_id') == user_id))
    
    if not (is_sender or is_courier):
        flash('Bu sohbete erişim yetkiniz yok.', 'error')
        return redirect(url_for('profile'))
    
    # Karşı tarafın bilgilerini belirle
    if is_sender:
        # Müşteri ise, kurye bilgilerini göster (kurye henüz kabul etmediyse "Kurye atanmadı")
        courier_name = shipment.get('courier_name') or 'Kurye atanmadı'
        other_party = {
            'name': courier_name,
            'type': 'kurye'
        }
    else:
        # Kurye ise, gönderici bilgilerini göster
        sender_email = shipment.get('sender_email')
        sender_user = users.get(sender_email, {})
        sender_name = sender_user.get('fullname') or shipment.get('sender_name') or 'Gönderici'
        other_party = {
            'name': sender_name,
            'type': 'musteri'
        }
    
    return render_template('chat.html', 
                         shipment=shipment, 
                         shipment_id=shipment_id,
                         other_party=other_party)

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
            if file and file.filename != '' and allowed_file(file.filename):
                # Uploads klasörünün var olduğundan emin ol
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filename = secure_filename(file.filename)
                # Benzersiz dosya adı oluştur
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                profile_image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(profile_image_path)
                # Relative path olarak kaydet
                profile_image = os.path.join('uploads', unique_filename)
           
        # Eğer kullanıcı kurye ise, plaka alanını kontrol et
        if user_type == 'kurye' and not plate:
            flash('Araç plakasını girmelisiniz!', 'error')
            return redirect(url_for('register'))

        
        # Fotoğrafı kaydet (session'a)
        if profile_image:
            session['profile_image'] = profile_image
        else:
            session['profile_image'] = 'static/uploads/default.jpg'

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
    user_id = session.get('user_id')

    # Geçmiş siparişler - shipments dictionary'sinden gerçek zamanlı veri al
    past_orders = []
    
    if user_type == 'kurye':
        # Kurye için kabul ettiği gönderiler
        for shipment_id, shipment in shipments.items():
            if shipment.get('courier_id') == user_id:
                # Status'u Türkçe'ye çevir
                status_map = {
                    'pending': 'Beklemede',
                    'accepted': 'Teslim Edilecek',
                    'delivered': 'Teslim Edildi'
                }
                status = status_map.get(shipment.get('status', 'pending'), 'Beklemede')
                
                order = {
                    "id": int(shipment.get('tracking_number', '0').split('-')[-1]) if shipment.get('tracking_number') else 0,
                    "date": shipment.get('created_at', datetime.now().isoformat())[:10] if shipment.get('created_at') else datetime.now().strftime("%Y-%m-%d"),
                    "status": status,
                    "tracking_number": shipment.get('tracking_number'),
                    "price": shipment.get('price', 0),
                    "details": {
                        "sender": shipment.get('sender_name', ''),
                        "receiver": shipment.get('receiver_name', ''),
                        "package": shipment.get('package_size', ''),
                        "sender_address": shipment.get('sender_address', ''),
                        "receiver_address": shipment.get('receiver_address', '')
                    }
                }
                past_orders.append(order)
    else:
        # Müşteri için kendi gönderileri
        for shipment_id, shipment in shipments.items():
            if shipment.get('sender_email') == user_id:
                # Status'u Türkçe'ye çevir
                status_map = {
                    'pending': 'Beklemede',
                    'accepted': 'Kabul Edildi',
                    'delivered': 'Teslim Edildi'
                }
                status = status_map.get(shipment.get('status', 'pending'), 'Beklemede')
                
                order = {
                    "id": int(shipment.get('tracking_number', '0').split('-')[-1]) if shipment.get('tracking_number') else 0,
                    "date": shipment.get('created_at', datetime.now().isoformat())[:10] if shipment.get('created_at') else datetime.now().strftime("%Y-%m-%d"),
                    "status": status,
                    "tracking_number": shipment.get('tracking_number'),
                    "price": shipment.get('price', 0),
                    "details": {
                        "sender": shipment.get('sender_name', ''),
                        "receiver": shipment.get('receiver_name', ''),
                        "package": shipment.get('package_size', ''),
                        "sender_address": shipment.get('sender_address', ''),
                        "receiver_address": shipment.get('receiver_address', '')
                    }
                }
                past_orders.append(order)
    
    # Tarihe göre sırala (en yeni üstte)
    past_orders.sort(key=lambda x: x.get('date', ''), reverse=True)

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
        # Giriş kontrolü
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Giriş yapmanız gerekiyor.'}), 401
        
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
            'sender_email': session.get('user_id'),  # Gönderici email'i ekle
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
        
        # Gönderiyi global shipments dictionary'sine ekle (kurye sayfasında görünsün)
        shipments[shipment_id] = new_shipment
        
        # Session'a da ekle (profil sayfasında görünsün)
        session_order = {
            "id": int(tracking_number.split('-')[-1]),  # Takip numarasından ID al
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "Beklemede",
            "tracking_number": tracking_number,  # Takip numarası eklendi
            "price": estimated_price,  # Ücret eklendi
            "details": {
                "sender": data['sender_name'],
                "receiver": data['receiver_name'],
                "package": data['package_size'],
                "sender_address": data['sender_address'],
                "receiver_address": data['receiver_address']
            }
        }
        current_orders = session.get('past_orders', [])
        current_orders.append(session_order)
        session['past_orders'] = current_orders
        
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

# Takip numarasına göre gönderi sorgula
@app.route('/api/shipments/track/<tracking_number>', methods=['GET'])
def track_shipment(tracking_number):
    try:
        # Gönderiler arasında takip numarasına göre ara
        shipment = None
        for s in shipments.values():
            if s['tracking_number'] == tracking_number:
                shipment = s
                break
        
        if not shipment:
            return jsonify({
                'success': False,
                'message': 'Gönderi bulunamadı. Takip numaranızı kontrol edin.'
            }), 404
        
        return jsonify({
            'success': True,
            'shipment': shipment
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Kullanıcının gönderilerini listele
@app.route('/api/shipments/my', methods=['GET'])
def get_my_shipments():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Giriş yapmanız gerekiyor.'}), 401
        
        user_email = session['user_id']
        # Gönderici olarak oluşturduğu gönderiler
        my_shipments = [s for s in shipments.values() if s.get('sender_email') == user_email]
        
        return jsonify({
            'success': True,
            'shipments': my_shipments
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Kuryenin kabul ettiği gönderileri listele
@app.route('/api/shipments/accepted', methods=['GET'])
def get_accepted_shipments():
    try:
        # Giriş kontrolü
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Giriş yapmanız gerekiyor.'}), 401
        
        # Kurye kontrolü
        if session.get('user_type') != 'kurye':
            return jsonify({'success': False, 'message': 'Bu işlem için kurye olmanız gerekiyor.'}), 403
        
        courier_id = session['user_id']
        # Bu kuryenin kabul ettiği gönderiler
        accepted_shipments = [s for s in shipments.values() if s.get('courier_id') == courier_id and s.get('status') == 'accepted']
        
        return jsonify({
            'success': True,
            'shipments': accepted_shipments
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Gönderiyi teslim et
@app.route('/api/shipments/<shipment_id>/deliver', methods=['POST'])
def deliver_shipment(shipment_id):
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
        if shipment['status'] != 'accepted':
            return jsonify({'success': False, 'message': 'Bu gönderi henüz kabul edilmemiş veya zaten teslim edilmiş.'}), 400
        
        # Kurye kontrolü - sadece kabul eden kurye teslim edebilir
        if shipment.get('courier_id') != session['user_id']:
            return jsonify({'success': False, 'message': 'Bu gönderiyi sadece kabul eden kurye teslim edebilir.'}), 403
        
        # Gönderiyi güncelle
        shipment['status'] = 'delivered'
        shipment['delivered_at'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'message': 'Gönderi başarıyla teslim edildi!',
            'shipment': shipment
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ------------------- Chat/Mesajlaşma Endpoints -------------------

# Mesaj gönder
@app.route('/api/chat/<shipment_id>/send', methods=['POST'])
def send_message(shipment_id):
    try:
        # Giriş kontrolü
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Giriş yapmanız gerekiyor.'}), 401
        
        # Gönderiyi bul
        shipment = shipments.get(shipment_id)
        if not shipment:
            return jsonify({'success': False, 'message': 'Gönderi bulunamadı.'}), 404
        
        # Yetki kontrolü
        user_id = session['user_id']
        user_type = session.get('user_type')
        # Gönderici kontrolü - müşteri her zaman kendi gönderilerine mesaj gönderebilir
        is_sender = shipment.get('sender_email') == user_id
        # Kurye kontrolü - kurye pending gönderilere de mesaj gönderebilir (kabul etmeden önce)
        # veya kabul ettiği gönderilere mesaj gönderebilir
        is_courier = (user_type == 'kurye' and 
                      (shipment.get('status') == 'pending' or 
                       shipment.get('courier_id') == user_id))
        
        if not (is_sender or is_courier):
            return jsonify({'success': False, 'message': 'Bu sohbete mesaj gönderme yetkiniz yok.'}), 403
        
        data = request.get_json()
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return jsonify({'success': False, 'message': 'Mesaj boş olamaz.'}), 400
        
        # Mesajı oluştur
        message_id = str(uuid.uuid4())
        new_message = {
            'id': message_id,
            'sender_id': user_id,
            'sender_name': session.get('user_name', 'Kullanıcı'),
            'message': message_text,
            'timestamp': datetime.now().isoformat()
        }
        
        # Mesajları sakla
        if shipment_id not in messages:
            messages[shipment_id] = []
        messages[shipment_id].append(new_message)
        
        return jsonify({
            'success': True,
            'message': 'Mesaj gönderildi.',
            'message_data': new_message
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Mesajları getir
@app.route('/api/chat/<shipment_id>/messages', methods=['GET'])
def get_messages(shipment_id):
    try:
        # Giriş kontrolü
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Giriş yapmanız gerekiyor.'}), 401
        
        # Gönderiyi bul
        shipment = shipments.get(shipment_id)
        if not shipment:
            return jsonify({'success': False, 'message': 'Gönderi bulunamadı.'}), 404
        
        # Yetki kontrolü
        user_id = session['user_id']
        user_type = session.get('user_type')
        # Gönderici kontrolü - müşteri her zaman kendi gönderilerine erişebilir
        is_sender = shipment.get('sender_email') == user_id
        # Kurye kontrolü - kurye pending gönderilere de erişebilir (kabul etmeden önce)
        # veya kabul ettiği gönderilere erişebilir
        is_courier = (user_type == 'kurye' and 
                      (shipment.get('status') == 'pending' or 
                       shipment.get('courier_id') == user_id))
        
        if not (is_sender or is_courier):
            return jsonify({'success': False, 'message': 'Bu sohbeti görüntüleme yetkiniz yok.'}), 403
        
        # Mesajları getir
        chat_messages = messages.get(shipment_id, [])
        
        # Kullanıcının mesajları okuduğunu işaretle (okunmamış mesaj sayısı için)
        if shipment_id not in last_read_messages:
            last_read_messages[shipment_id] = {}
        last_read_messages[shipment_id][user_id] = len(chat_messages)
        
        return jsonify({
            'success': True,
            'messages': chat_messages
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Kullanıcının chat listesini getir
@app.route('/api/chat/list', methods=['GET'])
def get_chat_list():
    try:
        # Giriş kontrolü
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Giriş yapmanız gerekiyor.'}), 401
        
        user_id = session['user_id']
        user_type = session.get('user_type')
        
        chat_list = []
        
        # Kullanıcının gönderilerini bul
        for shipment_id, shipment in shipments.items():
            # Gönderici kontrolü - müşteri her zaman kendi gönderilerine erişebilir
            is_sender = shipment.get('sender_email') == user_id
            # Kurye kontrolü - kurye pending gönderilere de erişebilir (kabul etmeden önce)
            # veya kabul ettiği gönderilere erişebilir
            is_courier = (user_type == 'kurye' and 
                          (shipment.get('status') == 'pending' or 
                           shipment.get('courier_id') == user_id))
            
            if is_sender or is_courier:
                # Son mesajı bul
                chat_messages = messages.get(shipment_id, [])
                last_message = chat_messages[-1] if chat_messages else None
                
                # Karşı tarafın bilgilerini belirle
                if is_sender:
                    other_name = shipment.get('courier_name', 'Kurye atanmadı')
                else:
                    sender_email = shipment.get('sender_email')
                    sender_user = users.get(sender_email, {})
                    other_name = sender_user.get('fullname', shipment.get('sender_name', 'Gönderici'))
                
                chat_list.append({
                    'shipment_id': shipment_id,
                    'tracking_number': shipment.get('tracking_number'),
                    'other_party': other_name,
                    'last_message': last_message,
                    'status': shipment.get('status')
                })
        
        # Son mesajı olan chat'leri en üste sırala
        chat_list.sort(key=lambda x: x['last_message']['timestamp'] if x['last_message'] else '', reverse=True)
        
        return jsonify({
            'success': True,
            'chats': chat_list
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Tracking number'a göre mesaj sayısını getir
@app.route('/api/chat/count/<tracking_number>', methods=['GET'])
def get_message_count(tracking_number):
    try:
        # Giriş kontrolü
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Giriş yapmanız gerekiyor.'}), 401
        
        user_id = session['user_id']
        user_type = session.get('user_type')
        
        # Tracking number'a göre shipment'ı bul
        shipment = None
        shipment_id = None
        for sid, s in shipments.items():
            if s.get('tracking_number') == tracking_number:
                shipment = s
                shipment_id = sid
                break
        
        if not shipment:
            return jsonify({
                'success': True,
                'count': 0,
                'has_access': False
            })
        
        # Yetki kontrolü
        # Gönderici kontrolü - müşteri her zaman kendi gönderilerine erişebilir
        is_sender = shipment.get('sender_email') == user_id
        # Kurye kontrolü - kurye pending gönderilere de erişebilir (kabul etmeden önce)
        # veya kabul ettiği gönderilere erişebilir
        is_courier = (user_type == 'kurye' and 
                       (shipment.get('status') == 'pending' or 
                        shipment.get('courier_id') == user_id))
        
        if not (is_sender or is_courier):
            return jsonify({
                'success': True,
                'count': 0,
                'has_access': False
            })
        
        # Okunmamış mesaj sayısını hesapla
        chat_messages = messages.get(shipment_id, [])
        total_message_count = len(chat_messages)
        
        # Kullanıcının son okuduğu mesaj sayısını al
        last_read_count = 0
        if shipment_id in last_read_messages and user_id in last_read_messages[shipment_id]:
            last_read_count = last_read_messages[shipment_id][user_id]
        
        # Okunmamış mesaj sayısı
        unread_count = max(0, total_message_count - last_read_count)
        
        return jsonify({
            'success': True,
            'count': unread_count,
            'total_count': total_message_count,
            'has_access': True,
            'shipment_id': shipment_id
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Shipment ID'ye göre okunmamış mesaj sayısını getir
@app.route('/api/chat/unread/<shipment_id>', methods=['GET'])
def get_unread_count(shipment_id):
    try:
        # Giriş kontrolü
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Giriş yapmanız gerekiyor.'}), 401
        
        user_id = session['user_id']
        
        # Gönderiyi bul
        shipment = shipments.get(shipment_id)
        if not shipment:
            return jsonify({
                'success': True,
                'count': 0
            })
        
        # Okunmamış mesaj sayısını hesapla
        chat_messages = messages.get(shipment_id, [])
        total_message_count = len(chat_messages)
        
        # Kullanıcının son okuduğu mesaj sayısını al
        last_read_count = 0
        if shipment_id in last_read_messages and user_id in last_read_messages[shipment_id]:
            last_read_count = last_read_messages[shipment_id][user_id]
        
        # Okunmamış mesaj sayısı
        unread_count = max(0, total_message_count - last_read_count)
        
        return jsonify({
            'success': True,
            'count': unread_count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ------------------- Main -------------------
if __name__ == "__main__":
    # Uploads klasörünü oluştur
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
