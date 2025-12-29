# Kapı Kapı - Test Kılavuzu

## Sunucuyu Başlatma

### Windows PowerShell'de:
```powershell
cd "c:\Users\umut\Desktop\cursor proje"
python server.py
```

### Windows CMD'de:
```cmd
cd "c:\Users\umut\Desktop\cursor proje"
python server.py
```

## Sunucu Başladıktan Sonra

Tarayıcıda şu adresi aç:
```
http://localhost:5000
```

veya

```
http://127.0.0.1:5000
```

## Test Senaryosu

### 1. Kurye Olarak Test Et

1. **Kayıt Ol:**
   - `http://localhost:5000/register` adresine git
   - Kullanıcı tipi: **"Kurye"** seç
   - Araç plakası gir (örn: 34ABC123)
   - Formu doldur ve kayıt ol

2. **Giriş Yap:**
   - `http://localhost:5000/login` adresine git
   - Kurye hesabınla giriş yap
   - **Otomatik olarak gönderi kabul ekranına yönlendirilmelisin**

3. **Gönderi Kabul:**
   - Gönderi kabul ekranında bekleyen gönderileri görüntüle
   - Gönderi yoksa, normal kullanıcı ile gönderi oluştur

### 2. Normal Kullanıcı Olarak Test Et

1. **Kayıt Ol:**
   - `http://localhost:5000/register` adresine git
   - Kullanıcı tipi: **"Müşteri"** seç
   - Formu doldur ve kayıt ol

2. **Gönderi Oluştur:**
   - `http://localhost:5000/gonder` adresine git
   - Gönderi formunu doldur
   - Gönderiyi oluştur

3. **Kurye ile Kontrol Et:**
   - Kurye hesabıyla giriş yap
   - Oluşturduğun gönderiyi gönderi kabul ekranında gör
   - Gönderiyi kabul et

## Sorun Giderme

### Sunucu Başlamıyorsa:

1. **Python kurulu mu kontrol et:**
   ```powershell
   python --version
   ```

2. **Flask kurulu mu kontrol et:**
   ```powershell
   pip list | findstr Flask
   ```

3. **Flask kur:**
   ```powershell
   pip install flask werkzeug
   ```

### Port Kullanımda Hatası:

Eğer port 5000 kullanımda ise, `server.py` dosyasının son satırını değiştir:
```python
app.run(debug=True, port=5001)
```

### Hata Mesajları:

- **ModuleNotFoundError**: Gerekli paketleri kur: `pip install flask werkzeug`
- **Port already in use**: Farklı bir port kullan veya çalışan sunucuyu durdur
- **Template not found**: `templates` klasörünün doğru yerde olduğundan emin ol

## Hızlı Test İçin

1. İki tarayıcı sekmesi aç:
   - Sekme 1: Normal kullanıcı (gönderi oluştur)
   - Sekme 2: Kurye (gönderi kabul et)

2. Gönderi oluştur:
   - Normal kullanıcı ile gönderi oluştur
   - Kurye sekmesinde "🔄 Yenile" butonuna tıkla
   - Gönderiyi gör ve kabul et

## Kontrol Listesi

- ✅ Kurye girişi → Gönderi kabul ekranına yönlendirme
- ✅ Normal kullanıcı → Gönderi oluştur sayfasına erişim
- ✅ Kurye "Gönderi Oluştur"a gittiğinde → Gönderi kabul ekranına yönlendirme
- ✅ Gönderi listeleme → Bekleyen gönderiler görünüyor mu?
- ✅ Gönderi kabul → Gönderi başarıyla kabul ediliyor mu?
- ✅ Navbar → "Kurye Ol" linkleri kaldırılmış mı?
- ✅ Kurye için → "Gönderi Kabul" linki görünüyor mu?

