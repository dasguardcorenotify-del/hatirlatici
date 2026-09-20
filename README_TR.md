# Hatırlatıcı

Hatırlatıcı, Linux için yerel öncelikli bir hatırlatma uygulamasıdır. Hatırlatmaları cihazda zamanlar; masaüstü bildirimi, isteğe bağlı e-posta veya her iki kanalla teslim edebilir. Bulut hesabı, analiz, reklam veya takip içermez.

2.0.0 sürümü İngilizce, Türkçe, Almanca, İspanyolca ve Rusça arayüzleri destekler.

> Proje durumu (2026-09-20): açık GitHub deposu ve yerel x86_64/aarch64 CI yapılandırması oluşturuldu. İki mimaride kaynak derlemesi ve dışa aktarım tamamlandı; Quality ortamının konumu ve Flatpak doğrulama oturumu düzeltildikten sonra tüm CI kontrollerinin başarılı çalışması hâlâ gereklidir. Sürüm etiketi/varlıkları ve Flathub incelemesi henüz tamamlanmadı. Yapay zekâ yardımı [AI_ASSISTANCE_DISCLOSURE.md](AI_ASSISTANCE_DISCLOSURE.md) içinde, kaynak rekonstrüksiyonu [docs/PROVENANCE.md](docs/PROVENANCE.md) içinde açıklanmıştır.

## Özellikler

- Yerel hatırlatma oluşturma, geçmiş ve otomatik yerel yedekler
- Tamamla ve ertele eylemli masaüstü bildirimleri
- İsteğe bağlı Gmail veya özel SMTP teslimatı
- Birlikte masaüstü ve e-posta teslimatı
- Masaüstü Secret portalı destekli, yerel olarak şifrelenmiş SMTP kimlik bilgisi kasası
- Tek örnekli masaüstü penceresi ve isteğe bağlı sistem tepsisi çalışması
- XDG uyumlu ve Flatpak kapsamıyla sınırlı ayar, veri ve durum dizinleri

E-posta teslimatı en iyi çaba modeliyle çalışır; SMTP sunucuları ve ağ hataları karşısında kesin olarak bir kez teslim garantisi verilemez.

## Kurulum

Hedef sürüm dosyası, projenin GitHub sürüm sayfasındaki `hatirlatici-2.0.0.flatpak` paketidir. Doğrulanmamış paket kullanmayın. Açık sürüm yayımlandığında dosyanın özetini `SHA256SUMS` ile doğrulayın ve ardından:

```bash
flatpak install --user ./hatirlatici-2.0.0.flatpak
flatpak run io.github.dasguardcorenotify_del.hatirlatici
```

Tek başına dağıtılan Flatpak paketi, ayrıca imzalı bir güncelleme deposu yapılandırılmadıkça otomatik güncelleme sağlamaz.

## E-posta yapılandırması

E-posta isteğe bağlıdır; yalnızca PC bildirimi kullanan hatırlatmalar posta hesabı gerektirmez.

Gmail için Google hesabında iki adımlı doğrulamayı etkinleştirin, Google hesap güvenliği bölümünde bir Uygulama Şifresi oluşturun ve 16 karakterli Uygulama Şifresini Hatırlatıcı kurulumuna girin. Normal Google hesap şifrenizi girmeyin. Uygulama Şifresinin kullanılabilirliği ve arayüz metinleri Google tarafından yönetilir ve hesap politikasına göre değişebilir.

Özel SMTP için sunucu adı, port, hesap adı, kimlik bilgisi ve STARTTLS ya da örtük TLS seçeneğini sağlayın. Hatırlatıcı sunucu sertifikalarını platform güven deposuyla doğrular ve TLS 1.2 veya üstünü gerektirir. E-posta teslimatına güvenmeden önce ayarları sınayın.

Kimlik bilgileri yerel olarak şifrelenir. Normal çalışmada yazdırılmaz; ancak yerel şifreleme, oturum açılmış masaüstünü zaten denetleyen bir saldırgana karşı koruma değildir.

## Kaynaktan derleme

Flatpak, `flatpak-builder` ve Flathub uzak deposunu kurduktan sonra Freedesktop 26.08 çalışma zamanını, SDK'yı ve Rust SDK uzantısını kurun. Qt 6.11.1, PyQt6 ve diğer Python bağımlılıkları, sabitlenmiş ve özetleri doğrulanan kaynak dağıtımlarından derlenir; mimariye özgü Python wheel dosyaları kullanılmaz. Ayrıntılı komutlar ve geliştirme manifesti için İngilizce [README.md](README.md) belgesine bakın.

Yerel kaynak ağacında yalnızca geliştirme amacıyla `io.github.dasguardcorenotify_del.hatirlatici.Devel.yml` kullanılır. Dağıtım manifesti, sabitlenmiş ve SHA-256 ile doğrulanan sürüm kaynak arşivini kullanır.

## Ekran görüntüleri

Sentetik verilerle çekilmiş ve onaylanmış altı 2.0.0 ekran görüntüsü [`docs/screenshots`](docs/screenshots) dizinindedir. AppStream, hareketli dal adresi yerine değişmez ve açık `f01d9a27420cb41fc7e782a8aea96f66d6a9bb28` commit'indeki dosyaları kullanır. Yayın kapısı dosya adlarını, boyutları, SHA-256 özetlerini, URL'leri ve yerelleştirilmiş başlıkları sabitler.

## Gizlilik, güvenlik ve destek

Flatpak içindeki veriler uygulamanın `~/.var/app/io.github.dasguardcorenotify_del.hatirlatici` kapsamındaki dizinlerinde tutulur. Uygulamanın ev dizininin veya ana sistemin tamamına erişim izni yoktur.

Veri işleme için [PRIVACY.md](PRIVACY.md), güvenlik bildirimleri için [SECURITY.md](SECURITY.md), yardım için [SUPPORT.md](SUPPORT.md) belgelerine bakın.

Doğrulanmış gerçek bir genel adres bulunmadığı için bağış bağlantısı yapılandırılmamıştır. Daha sonra eklenirse bağış tamamen gönüllü olacak ve hiçbir özelliğin kilidini açmayacaktır.

## Lisans

Hatırlatıcı [GPL-3.0-or-later](LICENSE) ile lisanslanır. Bağımlılık bildirimleri [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) dosyasındadır.
