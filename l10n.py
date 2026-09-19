#!/usr/bin/env python3
from __future__ import annotations

from string import Formatter


SUPPORTED_LANGUAGES = (
    "tr",
    "en",
    "de",
    "es",
    "ru",
)


LANGUAGE_NAMES = {
    "tr": "Türkçe",
    "en": "English",
    "de": "Deutsch",
    "es": "Español",
    "ru": "Русский",
}


STRINGS = {
    "tr": {
        "window_title":
            "Hatırlatıcı • İlk Kurulum",

        "brand":
            "HATIRLATICI",

        "wizard_label":
            "İLK KURULUM",

        "secure_local":
            "GÜVENLİ • YEREL",

        "step_profile":
            "Seni tanıyalım",

        "step_profile_sub":
            "Ad ve dil",

        "step_delivery":
            "Teslimat",

        "step_delivery_sub":
            "Nerede hatırlatalım?",

        "step_email":
            "E-posta",

        "step_email_sub":
            "Gmail veya özel SMTP",

        "step_security":
            "Güvenli bağlantı",

        "step_security_sub":
            "Uygulama Parolası rehberi",

        "step_ready":
            "Hazır",

        "step_ready_sub":
            "Son kontrol",

        "welcome_title":
            "Hatırlatıcı'ya hoş geldin",

        "welcome_sub":
            (
                "Sana ait sade ve güvenli bir hatırlatma "
                "alanını birkaç adımda hazırlayalım."
            ),

        "name":
            "Adın",

        "name_placeholder":
            "Sana nasıl hitap edelim?",

        "language":
            "Uygulama dili",

        "language_hint":
            (
                "Bu seçim ilk kurulum ekranını hemen "
                "değiştirir ve hesabına kaydedilir."
            ),

        "delivery_title":
            "Hatırlatmaları nereden almak istersin?",

        "delivery_sub":
            (
                "Daha sonra Ayarlar'dan değiştirebilirsin."
            ),

        "delivery_pc":
            "Bilgisayar",

        "delivery_pc_desc":
            (
                "Masaüstü bildirimi ile hatırlat. "
                "E-posta hesabı gerekmez."
            ),

        "delivery_email":
            "E-posta",

        "delivery_email_desc":
            (
                "Hatırlatmaları seçtiğin e-posta "
                "adresine gönder."
            ),

        "delivery_both":
            "Her ikisi",

        "delivery_both_desc":
            (
                "Masaüstü bildirimi ve e-posta birlikte."
            ),

        "email_title":
            "E-posta yöntemini seç",

        "email_sub":
            (
                "Gmail'i kolay kurulumla bağlayabilir "
                "veya kendi SMTP sunucunu kullanabilirsin."
            ),

        "gmail":
            "Gmail",

        "gmail_desc":
            (
                "Sunucu ve güvenlik ayarlarını "
                "Hatırlatıcı otomatik yapar."
            ),

        "custom":
            "Özel SMTP",

        "custom_desc":
            (
                "Kendi mail sunucusunu kullanan "
                "ileri düzey kullanıcılar için."
            ),

        "from_email":
            "Gmail adresin",

        "from_email_custom":
            "Gönderen e-posta",

        "to_email":
            "Hatırlatmaların geleceği adres",

        "smtp_username":
            "SMTP kullanıcı adı",

        "smtp_host":
            "SMTP sunucusu",

        "smtp_port":
            "SMTP portu",

        "smtp_secret":
            "Güvenli kimlik bilgisi",

        "app_password":
            "16 haneli Uygulama Parolası",

        "app_password_placeholder":
            "Google'ın oluşturduğu kodu buraya yapıştır",

        "gmail_guide_title":
            "Gmail'i güvenli şekilde bağla",

        "gmail_guide_sub":
            (
                "Normal Google şifreni Hatırlatıcı'ya "
                "girmiyorsun. Google'ın yalnız bu uygulama "
                "için oluşturduğu Uygulama Parolası kullanılır."
            ),

        "never_google_password":
            "Normal Google şifreni kullanma",

        "guide_step_1":
            "1. 2 Adımlı Doğrulamayı aç",

        "guide_step_1_desc":
            (
                "Google hesabında 2 Adımlı Doğrulama "
                "etkin olmalıdır."
            ),

        "guide_step_2":
            "2. Uygulama Parolaları sayfasını aç",

        "guide_step_2_desc":
            (
                "Google hesabında Hatırlatıcı için "
                "yeni bir uygulama parolası oluştur."
            ),

        "guide_step_3":
            "3. Google'ın verdiği 16 haneli kodu kopyala",

        "guide_step_3_desc":
            (
                "Bu kod normal hesabının şifresi değildir."
            ),

        "guide_step_4":
            "4. Kodu aşağıdaki güvenli alana yapıştır",

        "guide_step_4_desc":
            (
                "Kod Secret Portal tabanlı AES-256-GCM "
                "kasasında şifrelenir."
            ),

        "open_2sv":
            "2 Adımlı Doğrulamayı Aç",

        "open_app_passwords":
            "Uygulama Parolaları Sayfasını Aç",

        "why_missing":
            "Uygulama Parolaları görünmüyor mu?",

        "why_missing_desc":
            (
                "İş/okul hesabı, Advanced Protection "
                "veya yalnız güvenlik anahtarı kullanılan "
                "bazı hesaplarda bu seçenek bulunmayabilir."
            ),

        "custom_title":
            "Özel SMTP ayarları",

        "custom_sub":
            (
                "Bu bölüm yalnız kendi SMTP sunucusunu "
                "kullanan kullanıcılar içindir."
            ),

        "review_title":
            "Her şey hazır görünüyor",

        "review_sub":
            (
                "Kurulumdan önce seçimlerini son kez kontrol et."
            ),

        "review_profile":
            "Profil",

        "review_language":
            "Dil",

        "review_delivery":
            "Teslimat",

        "review_email":
            "E-posta",

        "review_security":
            "Güvenlik",

        "security_value":
            "Secret Portal + AES-256-GCM",

        "security_note":
            (
                "Kimlik bilgisi ayar dosyasına düz metin "
                "olarak yazılmaz."
            ),

        "finish_note":
            (
                "Kurulumu tamamladıktan sonra bu tercihleri "
                "Ayarlar bölümünden değiştirebilirsin."
            ),

        "back":
            "Geri",

        "next":
            "Devam et",

        "finish":
            "Hatırlatıcı'yı Kullanmaya Başla",

        "exit":
            "Şimdilik çık",

        "required_title":
            "Eksik bilgi",

        "name_required":
            "Devam etmek için adını gir.",

        "email_required":
            (
                "Gönderen ve alıcı e-posta adreslerini gir."
            ),

        "app_password_required":
            (
                "Google'ın oluşturduğu 16 haneli "
                "Uygulama Parolasını gir."
            ),

        "custom_required":
            (
                "Özel SMTP için sunucu, kullanıcı adı "
                "ve güvenli kimlik bilgisi gereklidir."
            ),

        "open_failed":
            "Sayfa varsayılan tarayıcıda açılamadı.",

        "privacy_footer":
            (
                "Yerel öncelikli • Reklamsız • "
                "Kimlik bilgisi şifreli"
            ),
    },


    "en": {
        "window_title":
            "Hatırlatıcı • First Setup",
        "brand":
            "HATIRLATICI",
        "wizard_label":
            "FIRST SETUP",
        "secure_local":
            "SECURE • LOCAL",
        "step_profile":
            "About you",
        "step_profile_sub":
            "Name and language",
        "step_delivery":
            "Delivery",
        "step_delivery_sub":
            "Where should we remind you?",
        "step_email":
            "Email",
        "step_email_sub":
            "Gmail or custom SMTP",
        "step_security":
            "Secure connection",
        "step_security_sub":
            "App Password guide",
        "step_ready":
            "Ready",
        "step_ready_sub":
            "Final review",

        "welcome_title":
            "Welcome to Hatırlatıcı",
        "welcome_sub":
            (
                "Let's prepare your simple and secure "
                "reminder space in a few steps."
            ),
        "name":
            "Your name",
        "name_placeholder":
            "How should we address you?",
        "language":
            "App language",
        "language_hint":
            (
                "This changes the setup language immediately "
                "and is saved to your profile."
            ),

        "delivery_title":
            "Where would you like to receive reminders?",
        "delivery_sub":
            "You can change this later in Settings.",
        "delivery_pc":
            "Computer",
        "delivery_pc_desc":
            (
                "Desktop notifications only. "
                "No email account required."
            ),
        "delivery_email":
            "Email",
        "delivery_email_desc":
            "Send reminders to an email address you choose.",
        "delivery_both":
            "Both",
        "delivery_both_desc":
            "Desktop notification and email together.",

        "email_title":
            "Choose your email method",
        "email_sub":
            (
                "Connect Gmail with guided setup or use "
                "your own SMTP server."
            ),
        "gmail":
            "Gmail",
        "gmail_desc":
            (
                "Hatırlatıcı configures server and security "
                "settings automatically."
            ),
        "custom":
            "Custom SMTP",
        "custom_desc":
            (
                "For advanced users with their own "
                "mail server."
            ),

        "from_email":
            "Your Gmail address",
        "from_email_custom":
            "Sender email",
        "to_email":
            "Reminder destination address",
        "smtp_username":
            "SMTP username",
        "smtp_host":
            "SMTP server",
        "smtp_port":
            "SMTP port",
        "smtp_secret":
            "Secure credential",
        "app_password":
            "16-digit App Password",
        "app_password_placeholder":
            "Paste the code generated by Google",

        "gmail_guide_title":
            "Connect Gmail securely",
        "gmail_guide_sub":
            (
                "Do not enter your normal Google password "
                "into Hatırlatıcı. Use the App Password "
                "generated by Google only for this app."
            ),
        "never_google_password":
            "Never use your normal Google password",

        "guide_step_1":
            "1. Enable 2-Step Verification",
        "guide_step_1_desc":
            (
                "2-Step Verification must be enabled "
                "on your Google Account."
            ),
        "guide_step_2":
            "2. Open the App Passwords page",
        "guide_step_2_desc":
            (
                "Create a new App Password for Hatırlatıcı."
            ),
        "guide_step_3":
            "3. Copy Google's 16-digit code",
        "guide_step_3_desc":
            "This is not your normal account password.",
        "guide_step_4":
            "4. Paste it into the secure field below",
        "guide_step_4_desc":
            (
                "It is encrypted in a Secret Portal-backed "
                "AES-256-GCM vault."
            ),

        "open_2sv":
            "Open 2-Step Verification",
        "open_app_passwords":
            "Open App Passwords",
        "why_missing":
            "Can't see App Passwords?",
        "why_missing_desc":
            (
                "The option may be unavailable for work or "
                "school accounts, Advanced Protection, or "
                "some security-key-only configurations."
            ),

        "custom_title":
            "Custom SMTP settings",
        "custom_sub":
            (
                "Only for users who manage their own "
                "SMTP service."
            ),

        "review_title":
            "Everything looks ready",
        "review_sub":
            "Review your choices before finishing setup.",
        "review_profile":
            "Profile",
        "review_language":
            "Language",
        "review_delivery":
            "Delivery",
        "review_email":
            "Email",
        "review_security":
            "Security",
        "security_value":
            "Secret Portal + AES-256-GCM",
        "security_note":
            (
                "Your credential is never written to "
                "settings as plain text."
            ),
        "finish_note":
            (
                "You can change these preferences later "
                "from Settings."
            ),

        "back":
            "Back",
        "next":
            "Continue",
        "finish":
            "Start Using Hatırlatıcı",
        "exit":
            "Exit for now",
        "required_title":
            "Missing information",
        "name_required":
            "Enter your name to continue.",
        "email_required":
            "Enter both sender and destination email addresses.",
        "app_password_required":
            "Enter the 16-digit App Password generated by Google.",
        "custom_required":
            (
                "Server, username and a secure credential "
                "are required for Custom SMTP."
            ),
        "open_failed":
            "The page could not be opened in your default browser.",
        "privacy_footer":
            "Local-first • Ad-free • Encrypted credential",
    },


    "de": {
        "window_title":
            "Hatırlatıcı • Ersteinrichtung",
        "brand":
            "HATIRLATICI",
        "wizard_label":
            "ERSTEINRICHTUNG",
        "secure_local":
            "SICHER • LOKAL",
        "step_profile":
            "Über dich",
        "step_profile_sub":
            "Name und Sprache",
        "step_delivery":
            "Zustellung",
        "step_delivery_sub":
            "Wo erinnern?",
        "step_email":
            "E-Mail",
        "step_email_sub":
            "Gmail oder eigenes SMTP",
        "step_security":
            "Sichere Verbindung",
        "step_security_sub":
            "App-Passwort-Anleitung",
        "step_ready":
            "Bereit",
        "step_ready_sub":
            "Letzte Prüfung",

        "welcome_title":
            "Willkommen bei Hatırlatıcı",
        "welcome_sub":
            (
                "Richten wir deinen einfachen und sicheren "
                "Erinnerungsbereich in wenigen Schritten ein."
            ),
        "name":
            "Dein Name",
        "name_placeholder":
            "Wie sollen wir dich ansprechen?",
        "language":
            "App-Sprache",
        "language_hint":
            (
                "Die Einrichtung wird sofort in dieser "
                "Sprache angezeigt."
            ),

        "delivery_title":
            "Wo möchtest du Erinnerungen erhalten?",
        "delivery_sub":
            "Du kannst dies später in den Einstellungen ändern.",
        "delivery_pc":
            "Computer",
        "delivery_pc_desc":
            (
                "Nur Desktop-Benachrichtigungen. "
                "Kein E-Mail-Konto erforderlich."
            ),
        "delivery_email":
            "E-Mail",
        "delivery_email_desc":
            "Erinnerungen an eine gewählte E-Mail-Adresse senden.",
        "delivery_both":
            "Beides",
        "delivery_both_desc":
            "Desktop-Benachrichtigung und E-Mail zusammen.",

        "email_title":
            "E-Mail-Methode auswählen",
        "email_sub":
            (
                "Gmail geführt verbinden oder einen "
                "eigenen SMTP-Server verwenden."
            ),
        "gmail":
            "Gmail",
        "gmail_desc":
            (
                "Server- und Sicherheitseinstellungen "
                "werden automatisch konfiguriert."
            ),
        "custom":
            "Eigenes SMTP",
        "custom_desc":
            "Für erfahrene Nutzer mit eigenem Mailserver.",

        "from_email":
            "Deine Gmail-Adresse",
        "from_email_custom":
            "Absenderadresse",
        "to_email":
            "Zieladresse für Erinnerungen",
        "smtp_username":
            "SMTP-Benutzername",
        "smtp_host":
            "SMTP-Server",
        "smtp_port":
            "SMTP-Port",
        "smtp_secret":
            "Sicherer Zugang",
        "app_password":
            "16-stelliges App-Passwort",
        "app_password_placeholder":
            "Von Google erzeugten Code einfügen",

        "gmail_guide_title":
            "Gmail sicher verbinden",
        "gmail_guide_sub":
            (
                "Verwende niemals dein normales Google-Passwort "
                "in Hatırlatıcı. Nutze nur das von Google "
                "erzeugte App-Passwort."
            ),
        "never_google_password":
            "Niemals das normale Google-Passwort verwenden",

        "guide_step_1":
            "1. Bestätigung in zwei Schritten aktivieren",
        "guide_step_1_desc":
            (
                "Die Bestätigung in zwei Schritten muss "
                "für dein Google-Konto aktiviert sein."
            ),
        "guide_step_2":
            "2. Seite „App-Passwörter“ öffnen",
        "guide_step_2_desc":
            "Erstelle ein neues App-Passwort für Hatırlatıcı.",
        "guide_step_3":
            "3. Googles 16-stelligen Code kopieren",
        "guide_step_3_desc":
            "Dieser Code ist nicht dein normales Kontopasswort.",
        "guide_step_4":
            "4. Code unten in das sichere Feld einfügen",
        "guide_step_4_desc":
            (
                "Er wird in einem AES-256-GCM-Tresor "
                "verschlüsselt."
            ),

        "open_2sv":
            "Bestätigung in zwei Schritten öffnen",
        "open_app_passwords":
            "App-Passwörter öffnen",
        "why_missing":
            "App-Passwörter nicht sichtbar?",
        "why_missing_desc":
            (
                "Bei Arbeits-/Schulkonten, Advanced Protection "
                "oder bestimmten Sicherheitsschlüssel-"
                "Konfigurationen kann die Option fehlen."
            ),

        "custom_title":
            "Eigene SMTP-Einstellungen",
        "custom_sub":
            "Nur für Nutzer mit eigenem SMTP-Dienst.",

        "review_title":
            "Alles sieht bereit aus",
        "review_sub":
            "Prüfe deine Auswahl vor dem Abschluss.",
        "review_profile":
            "Profil",
        "review_language":
            "Sprache",
        "review_delivery":
            "Zustellung",
        "review_email":
            "E-Mail",
        "review_security":
            "Sicherheit",
        "security_value":
            "Secret Portal + AES-256-GCM",
        "security_note":
            (
                "Zugangsdaten werden nie im Klartext "
                "in den Einstellungen gespeichert."
            ),
        "finish_note":
            (
                "Diese Einstellungen können später "
                "geändert werden."
            ),

        "back":
            "Zurück",
        "next":
            "Weiter",
        "finish":
            "Hatırlatıcı starten",
        "exit":
            "Vorerst schließen",
        "required_title":
            "Fehlende Angaben",
        "name_required":
            "Gib deinen Namen ein, um fortzufahren.",
        "email_required":
            "Gib Absender- und Zieladresse ein.",
        "app_password_required":
            "Gib das 16-stellige App-Passwort von Google ein.",
        "custom_required":
            (
                "Server, Benutzername und sicherer Zugang "
                "sind für eigenes SMTP erforderlich."
            ),
        "open_failed":
            "Die Seite konnte nicht im Browser geöffnet werden.",
        "privacy_footer":
            "Lokal zuerst • Werbefrei • Verschlüsselte Zugangsdaten",
    },


    "es": {
        "window_title":
            "Hatırlatıcı • Configuración inicial",
        "brand":
            "HATIRLATICI",
        "wizard_label":
            "CONFIGURACIÓN INICIAL",
        "secure_local":
            "SEGURO • LOCAL",
        "step_profile":
            "Sobre ti",
        "step_profile_sub":
            "Nombre e idioma",
        "step_delivery":
            "Entrega",
        "step_delivery_sub":
            "¿Dónde avisarte?",
        "step_email":
            "Correo",
        "step_email_sub":
            "Gmail o SMTP propio",
        "step_security":
            "Conexión segura",
        "step_security_sub":
            "Guía de contraseña de aplicación",
        "step_ready":
            "Listo",
        "step_ready_sub":
            "Revisión final",

        "welcome_title":
            "Bienvenido a Hatırlatıcı",
        "welcome_sub":
            (
                "Preparemos tu espacio de recordatorios "
                "simple y seguro en unos pocos pasos."
            ),
        "name":
            "Tu nombre",
        "name_placeholder":
            "¿Cómo debemos llamarte?",
        "language":
            "Idioma de la aplicación",
        "language_hint":
            (
                "La configuración cambia inmediatamente "
                "al idioma seleccionado."
            ),

        "delivery_title":
            "¿Dónde quieres recibir los recordatorios?",
        "delivery_sub":
            "Puedes cambiarlo más tarde en Ajustes.",
        "delivery_pc":
            "Ordenador",
        "delivery_pc_desc":
            (
                "Solo notificaciones de escritorio. "
                "No requiere correo."
            ),
        "delivery_email":
            "Correo",
        "delivery_email_desc":
            "Enviar recordatorios a una dirección elegida.",
        "delivery_both":
            "Ambos",
        "delivery_both_desc":
            "Notificación de escritorio y correo juntos.",

        "email_title":
            "Elige el método de correo",
        "email_sub":
            (
                "Conecta Gmail con la guía o utiliza "
                "tu propio servidor SMTP."
            ),
        "gmail":
            "Gmail",
        "gmail_desc":
            (
                "Hatırlatıcı configura automáticamente "
                "el servidor y la seguridad."
            ),
        "custom":
            "SMTP personalizado",
        "custom_desc":
            "Para usuarios avanzados con servidor propio.",

        "from_email":
            "Tu dirección de Gmail",
        "from_email_custom":
            "Correo remitente",
        "to_email":
            "Dirección que recibirá los recordatorios",
        "smtp_username":
            "Usuario SMTP",
        "smtp_host":
            "Servidor SMTP",
        "smtp_port":
            "Puerto SMTP",
        "smtp_secret":
            "Credencial segura",
        "app_password":
            "Contraseña de aplicación de 16 dígitos",
        "app_password_placeholder":
            "Pega el código generado por Google",

        "gmail_guide_title":
            "Conecta Gmail de forma segura",
        "gmail_guide_sub":
            (
                "No introduzcas tu contraseña normal de Google "
                "en Hatırlatıcı. Utiliza únicamente la contraseña "
                "de aplicación generada por Google."
            ),
        "never_google_password":
            "Nunca uses tu contraseña normal de Google",

        "guide_step_1":
            "1. Activa la verificación en dos pasos",
        "guide_step_1_desc":
            (
                "La verificación en dos pasos debe estar "
                "activada en tu cuenta de Google."
            ),
        "guide_step_2":
            "2. Abre la página Contraseñas de aplicaciones",
        "guide_step_2_desc":
            "Crea una contraseña nueva para Hatırlatıcı.",
        "guide_step_3":
            "3. Copia el código de 16 dígitos de Google",
        "guide_step_3_desc":
            "No es la contraseña normal de tu cuenta.",
        "guide_step_4":
            "4. Pégalo en el campo seguro de abajo",
        "guide_step_4_desc":
            (
                "Se cifra en una bóveda AES-256-GCM "
                "respaldada por Secret Portal."
            ),

        "open_2sv":
            "Abrir verificación en dos pasos",
        "open_app_passwords":
            "Abrir Contraseñas de aplicaciones",
        "why_missing":
            "¿No aparece Contraseñas de aplicaciones?",
        "why_missing_desc":
            (
                "Puede no estar disponible en cuentas de "
                "trabajo/escuela, Advanced Protection o "
                "algunas configuraciones con llave de seguridad."
            ),

        "custom_title":
            "Configuración SMTP personalizada",
        "custom_sub":
            "Solo para usuarios con su propio servicio SMTP.",

        "review_title":
            "Todo parece listo",
        "review_sub":
            "Revisa tus opciones antes de finalizar.",
        "review_profile":
            "Perfil",
        "review_language":
            "Idioma",
        "review_delivery":
            "Entrega",
        "review_email":
            "Correo",
        "review_security":
            "Seguridad",
        "security_value":
            "Secret Portal + AES-256-GCM",
        "security_note":
            (
                "La credencial nunca se guarda como texto "
                "sin cifrar en los ajustes."
            ),
        "finish_note":
            "Podrás cambiar estas opciones más tarde.",

        "back":
            "Atrás",
        "next":
            "Continuar",
        "finish":
            "Empezar a usar Hatırlatıcı",
        "exit":
            "Salir por ahora",
        "required_title":
            "Faltan datos",
        "name_required":
            "Introduce tu nombre para continuar.",
        "email_required":
            "Introduce el correo remitente y el destinatario.",
        "app_password_required":
            (
                "Introduce la contraseña de aplicación "
                "de 16 dígitos generada por Google."
            ),
        "custom_required":
            (
                "Servidor, usuario y credencial segura "
                "son obligatorios para SMTP personalizado."
            ),
        "open_failed":
            "No se pudo abrir la página en el navegador.",
        "privacy_footer":
            "Local primero • Sin anuncios • Credencial cifrada",
    },


    "ru": {
        "window_title":
            "Hatırlatıcı • Первоначальная настройка",
        "brand":
            "HATIRLATICI",
        "wizard_label":
            "ПЕРВОНАЧАЛЬНАЯ НАСТРОЙКА",
        "secure_local":
            "БЕЗОПАСНО • ЛОКАЛЬНО",
        "step_profile":
            "О вас",
        "step_profile_sub":
            "Имя и язык",
        "step_delivery":
            "Доставка",
        "step_delivery_sub":
            "Где напоминать?",
        "step_email":
            "Почта",
        "step_email_sub":
            "Gmail или свой SMTP",
        "step_security":
            "Безопасное подключение",
        "step_security_sub":
            "Инструкция по паролю приложения",
        "step_ready":
            "Готово",
        "step_ready_sub":
            "Последняя проверка",

        "welcome_title":
            "Добро пожаловать в Hatırlatıcı",
        "welcome_sub":
            (
                "Настроим ваше простое и безопасное "
                "пространство напоминаний за несколько шагов."
            ),
        "name":
            "Ваше имя",
        "name_placeholder":
            "Как к вам обращаться?",
        "language":
            "Язык приложения",
        "language_hint":
            (
                "Язык мастера изменится сразу "
                "и будет сохранён в профиле."
            ),

        "delivery_title":
            "Где вы хотите получать напоминания?",
        "delivery_sub":
            "Позже это можно изменить в настройках.",
        "delivery_pc":
            "Компьютер",
        "delivery_pc_desc":
            (
                "Только уведомления рабочего стола. "
                "Почта не требуется."
            ),
        "delivery_email":
            "Электронная почта",
        "delivery_email_desc":
            "Отправлять напоминания на выбранный адрес.",
        "delivery_both":
            "Оба варианта",
        "delivery_both_desc":
            "Уведомление рабочего стола и письмо вместе.",

        "email_title":
            "Выберите способ отправки почты",
        "email_sub":
            (
                "Подключите Gmail с помощью мастера "
                "или используйте собственный SMTP."
            ),
        "gmail":
            "Gmail",
        "gmail_desc":
            (
                "Hatırlatıcı автоматически настраивает "
                "сервер и параметры безопасности."
            ),
        "custom":
            "Свой SMTP",
        "custom_desc":
            "Для опытных пользователей со своим почтовым сервером.",

        "from_email":
            "Ваш адрес Gmail",
        "from_email_custom":
            "Адрес отправителя",
        "to_email":
            "Адрес для получения напоминаний",
        "smtp_username":
            "Имя пользователя SMTP",
        "smtp_host":
            "SMTP-сервер",
        "smtp_port":
            "Порт SMTP",
        "smtp_secret":
            "Безопасные данные доступа",
        "app_password":
            "16-значный пароль приложения",
        "app_password_placeholder":
            "Вставьте код, созданный Google",

        "gmail_guide_title":
            "Безопасно подключите Gmail",
        "gmail_guide_sub":
            (
                "Не вводите обычный пароль Google в Hatırlatıcı. "
                "Используйте только пароль приложения, "
                "созданный Google специально для этого приложения."
            ),
        "never_google_password":
            "Никогда не используйте обычный пароль Google",

        "guide_step_1":
            "1. Включите двухэтапную аутентификацию",
        "guide_step_1_desc":
            (
                "В аккаунте Google должна быть включена "
                "двухэтапная аутентификация."
            ),
        "guide_step_2":
            "2. Откройте страницу паролей приложений",
        "guide_step_2_desc":
            "Создайте новый пароль приложения для Hatırlatıcı.",
        "guide_step_3":
            "3. Скопируйте 16-значный код Google",
        "guide_step_3_desc":
            "Это не обычный пароль от вашего аккаунта.",
        "guide_step_4":
            "4. Вставьте код в защищённое поле ниже",
        "guide_step_4_desc":
            (
                "Он шифруется в хранилище AES-256-GCM "
                "на базе Secret Portal."
            ),

        "open_2sv":
            "Открыть двухэтапную аутентификацию",
        "open_app_passwords":
            "Открыть пароли приложений",
        "why_missing":
            "Нет пункта «Пароли приложений»?",
        "why_missing_desc":
            (
                "Он может отсутствовать для рабочих/учебных "
                "аккаунтов, Advanced Protection или некоторых "
                "конфигураций только с ключом безопасности."
            ),

        "custom_title":
            "Настройки собственного SMTP",
        "custom_sub":
            "Только для пользователей со своим SMTP-сервисом.",

        "review_title":
            "Всё готово",
        "review_sub":
            "Проверьте настройки перед завершением.",
        "review_profile":
            "Профиль",
        "review_language":
            "Язык",
        "review_delivery":
            "Доставка",
        "review_email":
            "Почта",
        "review_security":
            "Безопасность",
        "security_value":
            "Secret Portal + AES-256-GCM",
        "security_note":
            (
                "Данные доступа никогда не сохраняются "
                "в настройках открытым текстом."
            ),
        "finish_note":
            "Позже эти параметры можно изменить в настройках.",

        "back":
            "Назад",
        "next":
            "Продолжить",
        "finish":
            "Начать работу с Hatırlatıcı",
        "exit":
            "Выйти пока",
        "required_title":
            "Не хватает данных",
        "name_required":
            "Введите имя, чтобы продолжить.",
        "email_required":
            "Введите адрес отправителя и получателя.",
        "app_password_required":
            (
                "Введите 16-значный пароль приложения, "
                "созданный Google."
            ),
        "custom_required":
            (
                "Для собственного SMTP нужны сервер, "
                "имя пользователя и безопасные данные доступа."
            ),
        "open_failed":
            "Не удалось открыть страницу в браузере.",
        "privacy_footer":
            "Локально • Без рекламы • Данные доступа зашифрованы",
    },
}


def normalize_language(
    value: object,
) -> str:
    candidate = str(
        value or ""
    ).strip().lower()

    if candidate in SUPPORTED_LANGUAGES:
        return candidate

    return "en"


def text(
    key: str,
    language: str = "tr",
    **values: object,
) -> str:
    language = normalize_language(
        language
    )

    table = STRINGS.get(language, STRINGS["en"])
    if key not in table:
        raise KeyError(f"Unknown localization key: {key}")
    message = table[key]

    if values:
        return message.format(**values)

    return message


def validate_catalog() -> None:
    if set(STRINGS) != set(SUPPORTED_LANGUAGES):
        raise RuntimeError("Localization locale set does not match supported languages")

    reference = set(STRINGS["en"])
    if not reference:
        raise RuntimeError("English localization catalog is empty")

    formatter = Formatter()
    english_fields = {
        key: tuple(field for _literal, field, _spec, _conversion in formatter.parse(value) if field)
        for key, value in STRINGS["en"].items()
    }

    for language in SUPPORTED_LANGUAGES:
        current = set(STRINGS[language])
        missing = reference - current
        extra = current - reference
        if missing or extra:
            raise RuntimeError(
                f"Localization key mismatch for {language}: "
                f"missing={sorted(missing)!r} extra={sorted(extra)!r}"
            )
        for key, value in STRINGS[language].items():
            fields = tuple(
                field for _literal, field, _spec, _conversion in formatter.parse(value) if field
            )
            if fields != english_fields[key]:
                raise RuntimeError(
                    f"Localization placeholder mismatch for {language}:{key}"
                )


validate_catalog()

_FINAL_SETUP_STRINGS = {
    "tr": {
        "skipped":
            "Atlandı",
        "preview_mode":
            "Önizleme Modu",
        "preview_save_blocked":
            (
                "Bu ekran yalnız görsel kalite testi içindir. "
                "Gerçek ayarlar değiştirilmedi."
            ),
        "ok":
            "Tamam",
        "delivery_privacy_note":
            "Bilgisayar bildirimleri yereldir. Ağ yalnızca e-posta teslimatını seçtiğinde kullanılır.",
        "gmail_fixed_security":
            "smtp.gmail.com • Port 587 • Doğrulanmış STARTTLS (TLS 1.2 veya üzeri)",
        "smtp_security":
            "Bağlantı güvenliği",
        "smtp_host_placeholder":
            "smtp.sunucunuz.tld",
        "smtp_secret_placeholder":
            "SMTP parolası veya uygulama parolası",
        "tls_starttls":
            "STARTTLS (önerilen)",
        "tls_implicit":
            "Örtük TLS",
        "delete_stored_credential":
            "Artık gerekmeyen kayıtlı SMTP kimlik bilgisini sil",
        "stored_credential_placeholder":
            "Güvenli kasada kayıtlı • değiştirmek için yeni değer gir",
        "credential_save_failed":
            "Kimlik bilgisi güvenli kasaya kaydedilemedi.",
    },

    "en": {
        "skipped":
            "Skipped",
        "preview_mode":
            "Preview Mode",
        "preview_save_blocked":
            (
                "This screen is only for visual quality testing. "
                "Your real settings were not changed."
            ),
        "ok":
            "OK",
        "delivery_privacy_note":
            "Computer notifications stay local. Network access is used only when you choose email delivery.",
        "gmail_fixed_security":
            "smtp.gmail.com • Port 587 • Verified STARTTLS (TLS 1.2 or newer)",
        "smtp_security":
            "Connection security",
        "smtp_host_placeholder":
            "smtp.your-server.example",
        "smtp_secret_placeholder":
            "SMTP password or app password",
        "tls_starttls":
            "STARTTLS (recommended)",
        "tls_implicit":
            "Implicit TLS",
        "delete_stored_credential":
            "Delete the stored SMTP credential that is no longer needed",
        "stored_credential_placeholder":
            "Stored in the secure vault • enter a new value to replace it",
        "credential_save_failed":
            "The credential could not be saved to the secure vault.",
    },

    "de": {
        "skipped":
            "Übersprungen",
        "preview_mode":
            "Vorschaumodus",
        "preview_save_blocked":
            (
                "Dieser Bildschirm dient nur der visuellen Prüfung. "
                "Deine echten Einstellungen wurden nicht geändert."
            ),
        "ok":
            "OK",
        "delivery_privacy_note":
            "Computer-Benachrichtigungen bleiben lokal. Das Netzwerk wird nur für die E-Mail-Zustellung verwendet.",
        "gmail_fixed_security":
            "smtp.gmail.com • Port 587 • Geprüftes STARTTLS (TLS 1.2 oder neuer)",
        "smtp_security":
            "Verbindungssicherheit",
        "smtp_host_placeholder":
            "smtp.ihr-server.example",
        "smtp_secret_placeholder":
            "SMTP-Passwort oder App-Passwort",
        "tls_starttls":
            "STARTTLS (empfohlen)",
        "tls_implicit":
            "Implizites TLS",
        "delete_stored_credential":
            "Nicht mehr benötigte gespeicherte SMTP-Zugangsdaten löschen",
        "stored_credential_placeholder":
            "Im sicheren Tresor gespeichert • zum Ersetzen neuen Wert eingeben",
        "credential_save_failed":
            "Die Zugangsdaten konnten nicht im sicheren Tresor gespeichert werden.",
    },

    "es": {
        "skipped":
            "Omitido",
        "preview_mode":
            "Modo de vista previa",
        "preview_save_blocked":
            (
                "Esta pantalla es solo para comprobar la calidad visual. "
                "Tus ajustes reales no se modificaron."
            ),
        "ok":
            "Aceptar",
        "delivery_privacy_note":
            "Las notificaciones del ordenador permanecen locales. La red solo se usa al elegir el envío por correo.",
        "gmail_fixed_security":
            "smtp.gmail.com • Puerto 587 • STARTTLS verificado (TLS 1.2 o posterior)",
        "smtp_security":
            "Seguridad de la conexión",
        "smtp_host_placeholder":
            "smtp.su-servidor.example",
        "smtp_secret_placeholder":
            "Contraseña SMTP o contraseña de aplicación",
        "tls_starttls":
            "STARTTLS (recomendado)",
        "tls_implicit":
            "TLS implícito",
        "delete_stored_credential":
            "Eliminar la credencial SMTP guardada que ya no se necesita",
        "stored_credential_placeholder":
            "Guardada en la caja segura • introduce un valor nuevo para reemplazarla",
        "credential_save_failed":
            "No se pudo guardar la credencial en la caja segura.",
    },

    "ru": {
        "skipped":
            "Пропущено",
        "preview_mode":
            "Режим предпросмотра",
        "preview_save_blocked":
            (
                "Этот экран предназначен только для визуальной проверки. "
                "Настоящие настройки не изменялись."
            ),
        "ok":
            "ОК",
        "delivery_privacy_note":
            "Уведомления на компьютере остаются локальными. Сеть используется только для доставки по почте.",
        "gmail_fixed_security":
            "smtp.gmail.com • Порт 587 • Проверенный STARTTLS (TLS 1.2 или новее)",
        "smtp_security":
            "Защита соединения",
        "smtp_host_placeholder":
            "smtp.ваш-сервер.example",
        "smtp_secret_placeholder":
            "Пароль SMTP или пароль приложения",
        "tls_starttls":
            "STARTTLS (рекомендуется)",
        "tls_implicit":
            "Неявный TLS",
        "delete_stored_credential":
            "Удалить сохранённые данные SMTP, которые больше не нужны",
        "stored_credential_placeholder":
            "Сохранено в защищённом хранилище • введите новое значение для замены",
        "credential_save_failed":
            "Не удалось сохранить данные доступа в защищённом хранилище.",
    },
}

for _language, _values in _FINAL_SETUP_STRINGS.items():
    STRINGS[_language].update(
        _values
    )


# Main-window catalog.  Each row is ordered exactly like
# SUPPORTED_LANGUAGES: Turkish, English, German, Spanish, Russian.
# Keeping the product UI here prevents translated labels from becoming
# application state and gives every desktop surface one localization API.
_MAIN_APP_ROWS = {
    "app_name": (
        "Hatırlatıcı", "Hatırlatıcı", "Hatırlatıcı", "Hatırlatıcı", "Hatırlatıcı",
    ),
    "default_profile_name": (
        "Kullanıcı", "User", "Benutzer", "Usuario", "Пользователь",
    ),
    "profile_state": (
        "Yerel ve Güvenli", "Local & Secure", "Lokal & sicher", "Local y seguro", "Локально и безопасно",
    ),
    "window_close": (
        "Kapat", "Close", "Schließen", "Cerrar", "Закрыть",
    ),
    "window_minimize": (
        "Küçült", "Minimize", "Minimieren", "Minimizar", "Свернуть",
    ),
    "window_maximize_restore": (
        "Büyüt / Geri yükle", "Maximize / Restore", "Maximieren / Wiederherstellen", "Maximizar / Restaurar", "Развернуть / Восстановить",
    ),
    "nav_today": (
        "Bugün", "Today", "Heute", "Hoy", "Сегодня",
    ),
    "nav_reminders": (
        "Hatırlatmalar", "Reminders", "Erinnerungen", "Recordatorios", "Напоминания",
    ),
    "nav_history": (
        "Geçmiş", "History", "Verlauf", "Historial", "История",
    ),
    "nav_settings": (
        "Ayarlar", "Settings", "Einstellungen", "Ajustes", "Настройки",
    ),
    "greeting": (
        "Merhaba, {name}", "Hello, {name}", "Hallo, {name}", "Hola, {name}", "Здравствуйте, {name}",
    ),
    "today_count_one": (
        "Bugün {count} hatırlatıcın var", "You have {count} reminder today", "Du hast heute {count} Erinnerung", "Tienes {count} recordatorio hoy", "На сегодня у вас {count} напоминание",
    ),
    "today_count_few": (
        "Bugün {count} hatırlatıcın var", "You have {count} reminders today", "Du hast heute {count} Erinnerungen", "Tienes {count} recordatorios hoy", "На сегодня у вас {count} напоминания",
    ),
    "today_count_many": (
        "Bugün {count} hatırlatıcın var", "You have {count} reminders today", "Du hast heute {count} Erinnerungen", "Tienes {count} recordatorios hoy", "На сегодня у вас {count} напоминаний",
    ),
    "today_none": (
        "Bugün planlı hatırlatman yok", "You have no reminders scheduled today", "Für heute sind keine Erinnerungen geplant", "No tienes recordatorios programados para hoy", "На сегодня напоминаний нет",
    ),
    "new_reminder": (
        "Yeni Hatırlatma", "New Reminder", "Neue Erinnerung", "Nuevo recordatorio", "Новое напоминание",
    ),
    "subject_label": (
        "Ne hatırlatayım?", "What should I remind you about?", "Woran soll ich dich erinnern?", "¿Qué quieres recordar?", "О чём напомнить?",
    ),
    "subject_placeholder": (
        "Örn. Elektrik faturasını öde", "For example, pay the electricity bill", "Zum Beispiel: Stromrechnung bezahlen", "Por ejemplo, pagar la factura de la luz", "Например, оплатить счёт за электричество",
    ),
    "date": (
        "Tarih", "Date", "Datum", "Fecha", "Дата",
    ),
    "time": (
        "Saat", "Time", "Uhrzeit", "Hora", "Время",
    ),
    "repeat": (
        "Tekrar", "Repeat", "Wiederholung", "Repetición", "Повтор",
    ),
    "reminder_method": (
        "Hatırlatma yöntemi", "Reminder method", "Erinnerungsmethode", "Método de aviso", "Способ напоминания",
    ),
    "note": (
        "Not", "Note", "Notiz", "Nota", "Заметка",
    ),
    "note_placeholder": (
        "Hatırlatmayla ilgili kısa bir not yazın…", "Add a short note about this reminder…", "Füge eine kurze Notiz zur Erinnerung hinzu…", "Añade una nota breve sobre el recordatorio…", "Добавьте короткую заметку к напоминанию…",
    ),
    "save_reminder": (
        "Hatırlatmayı Kaydet", "Save Reminder", "Erinnerung speichern", "Guardar recordatorio", "Сохранить напоминание",
    ),
    "system_summary": (
        "Sistem özeti", "System summary", "Systemübersicht", "Resumen del sistema", "Сводка системы",
    ),
    "system_status": (
        "SİSTEM DURUMU", "SYSTEM STATUS", "SYSTEMSTATUS", "ESTADO DEL SISTEMA", "СОСТОЯНИЕ СИСТЕМЫ",
    ),
    "stat_active": (
        "Aktif", "Active", "Aktiv", "Activos", "Активно",
    ),
    "stat_deliveries": (
        "Gönderim", "Deliveries", "Zustellungen", "Envíos", "Доставки",
    ),
    "stat_last_delivery": (
        "Son gönderim", "Last delivery", "Letzte Zustellung", "Último envío", "Последняя доставка",
    ),
    "none_yet": (
        "Henüz yok", "None yet", "Noch keine", "Aún no hay", "Пока нет",
    ),
    "view_all": (
        "Tümünü Gör", "View All", "Alle anzeigen", "Ver todos", "Показать все",
    ),
    "today_no_more": (
        "Bugün için başka aktif hatırlatma yok", "No other active reminders today", "Keine weiteren aktiven Erinnerungen heute", "No hay más recordatorios activos hoy", "Других активных напоминаний на сегодня нет",
    ),
    "today_no_active": (
        "Bugün için aktif hatırlatma yok", "No active reminders today", "Heute gibt es keine aktiven Erinnerungen", "No hay recordatorios activos hoy", "На сегодня нет активных напоминаний",
    ),
    "reminders_appear_here": (
        "Yeni hatırlatmalar burada görünecek.", "New reminders will appear here.", "Neue Erinnerungen werden hier angezeigt.", "Los recordatorios nuevos aparecerán aquí.", "Новые напоминания появятся здесь.",
    ),
    "empty_calm": (
        "Şimdilik her şey sakin", "Everything is quiet for now", "Im Moment ist alles ruhig", "Todo está tranquilo por ahora", "Пока всё спокойно",
    ),
    "active_appear_here": (
        "Aktif bir hatırlatma eklediğinizde burada görünecek.", "Active reminders will appear here after you add them.", "Aktive Erinnerungen erscheinen hier, sobald du sie hinzufügst.", "Los recordatorios activos aparecerán aquí cuando los añadas.", "Активные напоминания появятся здесь после добавления.",
    ),
    "channels_independent": (
        "E-posta ve masaüstü bildirim kanalları bağımsız çalışır.", "Email and desktop notification channels work independently.", "E-Mail- und Desktop-Benachrichtigungen arbeiten unabhängig voneinander.", "Los canales de correo y notificaciones de escritorio funcionan de forma independiente.", "Почта и уведомления на компьютере работают независимо.",
    ),
    "info_email_title": (
        "E-posta ile hatırlatma", "Email reminders", "E-Mail-Erinnerungen", "Recordatorios por correo", "Напоминания по почте",
    ),
    "info_email_detail": (
        "Güvenli e-posta teslimat kanalı.", "Secure email delivery channel.", "Sicherer E-Mail-Zustellkanal.", "Canal seguro de envío por correo.", "Защищённая доставка по почте.",
    ),
    "info_desktop_title": (
        "Masaüstü bildirimi", "Desktop notifications", "Desktop-Benachrichtigungen", "Notificaciones de escritorio", "Уведомления на компьютере",
    ),
    "info_desktop_detail": (
        "Bu bilgisayardaki yerel bildirimler.", "Local notifications on this computer.", "Lokale Benachrichtigungen auf diesem Computer.", "Notificaciones locales en este ordenador.", "Локальные уведомления на этом компьютере.",
    ),
    "info_local_title": (
        "Yerel veri", "Local data", "Lokale Daten", "Datos locales", "Локальные данные",
    ),
    "info_local_detail": (
        "Hatırlatma kayıtları bu bilgisayarda tutulur.", "Reminder records are stored on this computer.", "Erinnerungsdaten werden auf diesem Computer gespeichert.", "Los recordatorios se guardan en este ordenador.", "Данные напоминаний хранятся на этом компьютере.",
    ),
    "no_schedule": (
        "Zaman planı yok", "No time scheduled", "Keine Zeit geplant", "Sin hora programada", "Время не задано",
    ),
    "untitled_reminder": (
        "Başlıksız hatırlatma", "Untitled reminder", "Unbenannte Erinnerung", "Recordatorio sin título", "Напоминание без названия",
    ),
    "reminder_fallback": (
        "Hatırlatma", "Reminder", "Erinnerung", "Recordatorio", "Напоминание",
    ),
    "state_active": (
        "Aktif", "Active", "Aktiv", "Activo", "Активно",
    ),
    "state_paused": (
        "Duraklatıldı", "Paused", "Pausiert", "En pausa", "Приостановлено",
    ),
    "edit": (
        "Düzenle", "Edit", "Bearbeiten", "Editar", "Изменить",
    ),
    "pause": (
        "Duraklat", "Pause", "Pausieren", "Pausar", "Приостановить",
    ),
    "enable": (
        "Etkinleştir", "Enable", "Aktivieren", "Activar", "Включить",
    ),
    "delete": (
        "Sil", "Delete", "Löschen", "Eliminar", "Удалить",
    ),
    "duplicate": (
        "Çoğalt", "Duplicate", "Duplizieren", "Duplicar", "Дублировать",
    ),
    "duplicate_subject_suffix": (
        "Kopya", "Copy", "Kopie", "Copia", "Копия",
    ),
    "snooze_ten": (
        "10 dk ertele", "Snooze 10 min", "10 Min. später", "Posponer 10 min", "Отложить на 10 мин",
    ),
    "complete": (
        "Tamamlandı", "Complete", "Erledigen", "Completar", "Завершить",
    ),
    "edit_reminder": (
        "Hatırlatmayı Düzenle", "Edit Reminder", "Erinnerung bearbeiten", "Editar recordatorio", "Изменить напоминание",
    ),
    "cancel": (
        "Vazgeç", "Cancel", "Abbrechen", "Cancelar", "Отмена",
    ),
    "save_changes": (
        "Değişiklikleri Kaydet", "Save Changes", "Änderungen speichern", "Guardar cambios", "Сохранить изменения",
    ),
    "category": (
        "Kategori", "Category", "Kategorie", "Categoría", "Категория",
    ),
    "repeat_once": (
        "Tek seferlik", "Once", "Einmal", "Una vez", "Один раз",
    ),
    "repeat_daily": (
        "Her gün", "Every day", "Täglich", "Cada día", "Каждый день",
    ),
    "repeat_weekly": (
        "Her hafta", "Every week", "Wöchentlich", "Cada semana", "Каждую неделю",
    ),
    "repeat_monthly": (
        "Her ay", "Every month", "Monatlich", "Cada mes", "Каждый месяц",
    ),
    "repeat_every_15m": (
        "Her 15 dakika", "Every 15 minutes", "Alle 15 Minuten", "Cada 15 minutos", "Каждые 15 минут",
    ),
    "repeat_every_30m": (
        "Her 30 dakika", "Every 30 minutes", "Alle 30 Minuten", "Cada 30 minutos", "Каждые 30 минут",
    ),
    "repeat_every_1h": (
        "Her 1 saat", "Every hour", "Stündlich", "Cada hora", "Каждый час",
    ),
    "repeat_every_2h": (
        "Her 2 saat", "Every 2 hours", "Alle 2 Stunden", "Cada 2 horas", "Каждые 2 часа",
    ),
    "category_general": (
        "Genel", "General", "Allgemein", "General", "Общее",
    ),
    "category_personal": (
        "Kişisel", "Personal", "Persönlich", "Personal", "Личное",
    ),
    "category_work": (
        "İş", "Work", "Arbeit", "Trabajo", "Работа",
    ),
    "category_payment": (
        "Ödeme", "Payment", "Zahlung", "Pago", "Платёж",
    ),
    "category_health": (
        "Sağlık", "Health", "Gesundheit", "Salud", "Здоровье",
    ),
    "category_shopping": (
        "Alışveriş", "Shopping", "Einkaufen", "Compras", "Покупки",
    ),
    "category_other": (
        "Diğer", "Other", "Sonstiges", "Otros", "Другое",
    ),
    "quick_title": (
        "Hızlı Hatırlatma", "Quick Reminder", "Schnellerinnerung", "Recordatorio rápido", "Быстрое напоминание",
    ),
    "quick_hint": (
        "Örn: yarın 9'da Ahmet'i ara", "For example: call Alex tomorrow at 9", "Zum Beispiel: Alex morgen um 9 anrufen", "Por ejemplo: llamar a Alex mañana a las 9", "Например: позвонить Алексу завтра в 9",
    ),
    "quick_placeholder": (
        "30 dakika sonra çayı kontrol et…", "Check the tea in 30 minutes…", "In 30 Minuten nach dem Tee sehen…", "Comprobar el té dentro de 30 minutos…", "Проверить чай через 30 минут…",
    ),
    "quick_apply": (
        "Forma Aktar", "Fill Form", "Formular ausfüllen", "Rellenar formulario", "Заполнить форму",
    ),
    "quick_save": (
        "Hızlı Kaydet", "Quick Save", "Schnell speichern", "Guardado rápido", "Быстро сохранить",
    ),
    "quick_plus_minutes": (
        "+{minutes} dk", "+{minutes} min", "+{minutes} Min.", "+{minutes} min", "+{minutes} мин",
    ),
    "quick_plus_hours": (
        "+{hours} saat", "+{hours} hr", "+{hours} Std.", "+{hours} h", "+{hours} ч",
    ),
    "quick_tomorrow": (
        "Yarın 09:00", "Tomorrow 09:00", "Morgen 09:00", "Mañana 09:00", "Завтра 09:00",
    ),
    "quick_parse_failed": (
        "İfadeyi anlayamadım. Tarih ve saati formdan seçebilirsin.", "I couldn't understand that phrase. You can choose the date and time in the form.", "Ich konnte den Ausdruck nicht verstehen. Datum und Uhrzeit kannst du im Formular wählen.", "No pude entender la frase. Puedes elegir la fecha y la hora en el formulario.", "Не удалось распознать фразу. Выберите дату и время в форме.",
    ),
    "quick_parsed": (
        "Hızlı ifade çözümlendi.", "Quick phrase parsed.", "Schnellausdruck erkannt.", "Frase rápida interpretada.", "Быстрая фраза распознана.",
    ),
    "quick_saved": (
        "Hızlı hatırlatma kaydedildi.", "Quick reminder saved.", "Schnellerinnerung gespeichert.", "Recordatorio rápido guardado.", "Быстрое напоминание сохранено.",
    ),
    "title_required": (
        "Başlık gerekli.", "A title is required.", "Ein Titel ist erforderlich.", "Se necesita un título.", "Нужно указать название.",
    ),
    "invalid_repeat": (
        "Geçersiz tekrar seçeneği.", "Invalid repeat option.", "Ungültige Wiederholungsoption.", "Opción de repetición no válida.", "Недопустимый вариант повтора.",
    ),
    "save_failed": (
        "Kaydedilemedi: {error}", "Could not save: {error}", "Speichern fehlgeschlagen: {error}", "No se pudo guardar: {error}", "Не удалось сохранить: {error}",
    ),
    "setup_save_failed": (
        "Kurulum kaydedilemedi. Girdiğiniz bilgileri koruduk; depolama alanını ve izinleri kontrol edip yeniden deneyin. Parolayı yeniden girmeniz gerekebilir.",
        "Setup could not be saved. Your form entries were kept; check storage space and permissions, then try again. You may need to enter the password again.",
        "Die Einrichtung konnte nicht gespeichert werden. Deine Formulareingaben bleiben erhalten. Prüfe Speicherplatz und Zugriffsrechte und versuche es erneut. Gib das Passwort bei Bedarf erneut ein.",
        "No se pudo guardar la configuración. Se conservaron los datos del formulario; comprueba el espacio y los permisos e inténtalo de nuevo. Es posible que debas volver a introducir la contraseña.",
        "Не удалось сохранить настройки. Данные формы сохранены; проверьте свободное место и права доступа и повторите попытку. Возможно, потребуется снова ввести пароль.",
    ),
    "setup_restore_failed": (
        "Kurulum kaydedilemedi ve önceki dosyalar tamamen geri yüklenemedi. Şifreli dosyaları silmeyin. Yeniden denemeden önce depolama alanını ve izinleri kontrol edin.",
        "Setup could not be saved and the previous files could not be fully restored. Do not delete encrypted files. Check storage space and permissions before retrying.",
        "Die Einrichtung konnte nicht gespeichert werden. Die vorherigen Dateien wurden nicht vollständig wiederhergestellt. Lösche keine verschlüsselten Dateien. Prüfe vor einem erneuten Versuch Speicherplatz und Zugriffsrechte.",
        "No se pudo guardar la configuración ni restaurar todos los archivos anteriores. No borres los archivos cifrados. Comprueba el espacio y los permisos antes de reintentar.",
        "Не удалось сохранить настройки и полностью восстановить прежние файлы. Не удаляйте зашифрованные файлы. Перед повторной попыткой проверьте свободное место и права доступа.",
    ),
    "operation_failed_detail": (
        "Lütfen ayarları kontrol edip yeniden deneyin.", "Check the settings and try again.", "Prüfe die Einstellungen und versuche es erneut.", "Comprueba los ajustes e inténtalo de nuevo.", "Проверьте настройки и повторите попытку.",
    ),
    "reminder_saved": (
        "Hatırlatma kaydedildi • {channel}", "Reminder saved • {channel}", "Erinnerung gespeichert • {channel}", "Recordatorio guardado • {channel}", "Напоминание сохранено • {channel}",
    ),
    "channel_selected": (
        "{channel} seçildi.", "{channel} selected.", "{channel} ausgewählt.", "Se ha seleccionado {channel}.", "Выбрано: {channel}.",
    ),
    "reminders_subtitle": (
        "Ara, filtrele ve tüm hatırlatmalarını yönet.", "Search, filter, and manage all your reminders.", "Durchsuche, filtere und verwalte alle Erinnerungen.", "Busca, filtra y gestiona todos tus recordatorios.", "Ищите, фильтруйте и управляйте всеми напоминаниями.",
    ),
    "search_reminders": (
        "Hatırlatmalarda ara…", "Search reminders…", "Erinnerungen durchsuchen…", "Buscar recordatorios…", "Поиск напоминаний…",
    ),
    "all_channels": (
        "Tüm kanallar", "All channels", "Alle Kanäle", "Todos los canales", "Все каналы",
    ),
    "all_categories": (
        "Tüm kategoriler", "All categories", "Alle Kategorien", "Todas las categorías", "Все категории",
    ),
    "all_states": (
        "Tüm durumlar", "All states", "Alle Status", "Todos los estados", "Все состояния",
    ),
    "filter_show": (
        "Göster:", "Show:", "Anzeigen:", "Mostrar:", "Показать:",
    ),
    "filter_all": (
        "Tümü", "All", "Alle", "Todos", "Все",
    ),
    "refresh": (
        "Yenile", "Refresh", "Aktualisieren", "Actualizar", "Обновить",
    ),
    "no_filter_match": (
        "Bu filtrelerle eşleşen hatırlatma yok.", "No reminders match these filters.", "Keine Erinnerungen entsprechen diesen Filtern.", "Ningún recordatorio coincide con estos filtros.", "Нет напоминаний, подходящих под фильтры.",
    ),
    "reminder_updated": (
        "Hatırlatma güncellendi.", "Reminder updated.", "Erinnerung aktualisiert.", "Recordatorio actualizado.", "Напоминание обновлено.",
    ),
    "update_failed": (
        "Güncellenemedi: {error}", "Could not update: {error}", "Aktualisierung fehlgeschlagen: {error}", "No se pudo actualizar: {error}", "Не удалось обновить: {error}",
    ),
    "reminder_duplicated": (
        "Hatırlatma çoğaltıldı.", "Reminder duplicated.", "Erinnerung dupliziert.", "Recordatorio duplicado.", "Напоминание продублировано.",
    ),
    "duplicate_failed": (
        "Çoğaltılamadı: {error}", "Could not duplicate: {error}", "Duplizieren fehlgeschlagen: {error}", "No se pudo duplicar: {error}", "Не удалось продублировать: {error}",
    ),
    "reminder_snoozed": (
        "{minutes} dakika ertelendi.", "Snoozed for {minutes} minutes.", "Um {minutes} Minuten verschoben.", "Pospuesto {minutes} minutos.", "Отложено на {minutes} минут.",
    ),
    "snooze_failed": (
        "Ertelenemedi: {error}", "Could not snooze: {error}", "Verschieben fehlgeschlagen: {error}", "No se pudo posponer: {error}", "Не удалось отложить: {error}",
    ),
    "reminder_completed": (
        "Tamamlandı.", "Completed.", "Erledigt.", "Completado.", "Завершено.",
    ),
    "complete_failed": (
        "Tamamlanamadı: {error}", "Could not complete: {error}", "Abschließen fehlgeschlagen: {error}", "No se pudo completar: {error}", "Не удалось завершить: {error}",
    ),
    "delete_reminder": (
        "Hatırlatmayı Sil", "Delete Reminder", "Erinnerung löschen", "Eliminar recordatorio", "Удалить напоминание",
    ),
    "delete_confirm": (
        "“{subject}” kalıcı olarak silinsin mi?", "Permanently delete “{subject}”?", "„{subject}“ dauerhaft löschen?", "¿Eliminar “{subject}” de forma permanente?", "Удалить «{subject}» навсегда?",
    ),
    "delete_failed": (
        "Silinemedi: {error}", "Could not delete: {error}", "Löschen fehlgeschlagen: {error}", "No se pudo eliminar: {error}", "Не удалось удалить: {error}",
    ),
    "reminder_deleted": (
        "Hatırlatma silindi.", "Reminder deleted.", "Erinnerung gelöscht.", "Recordatorio eliminado.", "Напоминание удалено.",
    ),
    "history_subtitle": (
        "Gerçek gönderim olayları burada tutulur.", "Actual delivery events are recorded here.", "Tatsächliche Zustellereignisse werden hier erfasst.", "Aquí se registran los eventos de envío reales.", "Здесь записываются реальные события доставки.",
    ),
    "history_counts_title": (
        "Kayıtlı gönderim özeti", "Recorded delivery summary", "Übersicht erfasster Zustellungen", "Resumen de envíos registrados", "Сводка записанных доставок",
    ),
    "history_counts": (
        "Toplam gönderim: {count}", "Total deliveries: {count}", "Zustellungen insgesamt: {count}", "Envíos totales: {count}", "Всего доставок: {count}",
    ),
    "history_counts_last": (
        "Toplam gönderim: {count} • Son gönderim: {last}", "Total deliveries: {count} • Last delivery: {last}", "Zustellungen insgesamt: {count} • Letzte Zustellung: {last}", "Envíos totales: {count} • Último envío: {last}", "Всего доставок: {count} • Последняя доставка: {last}",
    ),
    "history_truth_note": (
        "Önceki toplamlar sayaç olarak korunur; bunlardan yapay geçmiş olayları üretilmez.", "Earlier totals remain aggregate counts; no synthetic history events are created from them.", "Frühere Summen bleiben Zähler; daraus werden keine künstlichen Verlaufsereignisse erzeugt.", "Los totales anteriores se conservan como contadores; no se crean eventos de historial ficticios.", "Предыдущие итоги сохранены как счётчики; искусственные события истории не создаются.",
    ),
    "history_empty": (
        "Henüz kayıtlı bir gönderim olayı yok.", "No delivery events have been recorded yet.", "Noch wurden keine Zustellereignisse erfasst.", "Aún no se han registrado eventos de envío.", "Событий доставки пока нет.",
    ),
    "settings_subtitle": (
        "Hatırlatıcı davranışını ve teslimat kanallarını yönet.", "Manage reminder behavior and delivery channels.", "Verwalte Verhalten und Zustellkanäle.", "Gestiona el comportamiento y los canales de envío.", "Настройте поведение и каналы доставки.",
    ),
    "delivery_engines": (
        "Teslimat motorları", "Delivery engines", "Zustelldienste", "Motores de envío", "Службы доставки",
    ),
    "delivery_engine_status": (
        "E-posta: {email} • Bilgisayar: {computer}", "Email: {email} • Computer: {computer}", "E-Mail: {email} • Computer: {computer}", "Correo: {email} • Ordenador: {computer}", "Почта: {email} • Компьютер: {computer}",
    ),
    "running": (
        "Çalışıyor", "Running", "Aktiv", "En ejecución", "Работает",
    ),
    "stopped": (
        "Durduruldu", "Stopped", "Gestoppt", "Detenido", "Остановлено",
    ),
    "healthy": (
        "SAĞLIKLI", "HEALTHY", "BEREIT", "CORRECTO", "ИСПРАВНО",
    ),
    "check_status": (
        "KONTROL ET", "CHECK", "PRÜFEN", "REVISAR", "ПРОВЕРИТЬ",
    ),
    "default_method_title": (
        "Varsayılan hatırlatma yöntemi", "Default reminder method", "Standard-Erinnerungsmethode", "Método de aviso predeterminado", "Способ напоминания по умолчанию",
    ),
    "default_method_detail": (
        "Yeni hatırlatmalarda otomatik seçilecek teslimat kanalı.", "The delivery channel selected automatically for new reminders.", "Der für neue Erinnerungen automatisch ausgewählte Zustellkanal.", "El canal que se selecciona automáticamente en recordatorios nuevos.", "Канал доставки, автоматически выбранный для новых напоминаний.",
    ),
    "save": (
        "Kaydet", "Save", "Speichern", "Guardar", "Сохранить",
    ),
    "default_method_saved": (
        "Varsayılan yöntem kaydedildi.", "Default method saved.", "Standardmethode gespeichert.", "Método predeterminado guardado.", "Способ по умолчанию сохранён.",
    ),
    "notification_test_title": (
        "Masaüstü bildirimi testi", "Desktop notification test", "Desktop-Benachrichtigung testen", "Prueba de notificación de escritorio", "Проверка уведомлений",
    ),
    "notification_test_detail": (
        "Bildirim Portalı üzerinden gerçek bir test bildirimi gönderir.", "Sends a real test notification through the Notification Portal.", "Sendet eine echte Testbenachrichtigung über das Benachrichtigungsportal.", "Envía una notificación de prueba real mediante el portal de notificaciones.", "Отправляет настоящее тестовое уведомление через портал уведомлений.",
    ),
    "notification_test_send": (
        "Test bildirimi gönder", "Send Test Notification", "Testbenachrichtigung senden", "Enviar notificación de prueba", "Отправить тестовое уведомление",
    ),
    "notification_test_heading": (
        "Hatırlatıcı • Bildirim Testi", "Hatırlatıcı • Notification Test", "Hatırlatıcı • Benachrichtigungstest", "Hatırlatıcı • Prueba de notificación", "Hatırlatıcı • Проверка уведомлений",
    ),
    "notification_test_body": (
        "Bu bildirim XDG Notification Portal üzerinden gönderildi.", "This notification was sent through the XDG Notification Portal.", "Diese Benachrichtigung wurde über das XDG Notification Portal gesendet.", "Esta notificación se envió mediante el portal de notificaciones XDG.", "Это уведомление отправлено через XDG Notification Portal.",
    ),
    "notification_test_failed": (
        "Bildirim testi başarısız", "Notification Test Failed", "Benachrichtigungstest fehlgeschlagen", "Error en la prueba de notificación", "Проверка уведомлений не удалась",
    ),
    "notification_test_failed_detail": (
        "Bildirim Portalı test bildirimini gönderemedi. Masaüstü bildirim izinlerini kontrol edin.", "The Notification Portal could not send the test notification. Check desktop notification permissions.", "Das Benachrichtigungsportal konnte die Testbenachrichtigung nicht senden. Prüfe die Desktop-Berechtigungen.", "El portal de notificaciones no pudo enviar la prueba. Comprueba los permisos de notificaciones del escritorio.", "Портал уведомлений не смог отправить тест. Проверьте разрешения на уведомления.",
    ),
    "notification_test_ok": (
        "Bildirim testi", "Notification Test", "Benachrichtigungstest", "Prueba de notificación", "Проверка уведомлений",
    ),
    "notification_test_sent": (
        "Test bildirimi Bildirim Portalı'na gönderildi.", "The test notification was sent to the Notification Portal.", "Die Testbenachrichtigung wurde an das Benachrichtigungsportal gesendet.", "La notificación de prueba se envió al portal de notificaciones.", "Тестовое уведомление отправлено в портал уведомлений.",
    ),
    "autostart_title": (
        "Bilgisayarla birlikte başlat", "Start with the computer", "Beim Anmelden starten", "Iniciar con el ordenador", "Запускать при входе",
    ),
    "autostart_detail": (
        "Hatırlatıcı'yı oturum açıldığında otomatik başlat.", "Start Hatırlatıcı automatically when you sign in.", "Hatırlatıcı bei der Anmeldung automatisch starten.", "Inicia Hatırlatıcı automáticamente al entrar en la sesión.", "Автоматически запускать Hatırlatıcı при входе в систему.",
    ),
    "background_on_autostart_on": (
        "Arka plan: Açık • Otomatik başlat: Açık", "Background: On • Autostart: On", "Hintergrund: An • Autostart: An", "Segundo plano: Sí • Inicio automático: Sí", "Фоновая работа: вкл. • Автозапуск: вкл.",
    ),
    "background_on": (
        "Arka plan: Açık", "Background: On", "Hintergrund: An", "Segundo plano: Sí", "Фоновая работа: вкл.",
    ),
    "background_request": (
        "Arka plan izni ve otomatik başlatma", "Background Permission & Autostart", "Hintergrundberechtigung & Autostart", "Permiso en segundo plano e inicio automático", "Фоновая работа и автозапуск",
    ),
    "background_permission_title": (
        "Flatpak arka plan izni", "Flatpak Background Permission", "Flatpak-Hintergrundberechtigung", "Permiso en segundo plano de Flatpak", "Фоновое разрешение Flatpak",
    ),
    "background_development_note": (
        "Gerçek arka plan ve otomatik başlatma izni kurulu Flatpak içinden istenir. Geliştirme kopyası sistem ayarlarını değiştirmez.", "Background and autostart permission is requested from the installed Flatpak. The development copy does not change system settings.", "Hintergrund- und Autostartberechtigungen werden aus dem installierten Flatpak angefordert. Die Entwicklungskopie ändert keine Systemeinstellungen.", "El permiso de segundo plano e inicio automático se solicita desde el Flatpak instalado. La copia de desarrollo no cambia los ajustes del sistema.", "Разрешение на фоновую работу и автозапуск запрашивается из установленного Flatpak. Копия для разработки не меняет системные настройки.",
    ),
    "background_reason": (
        "Hatırlatmaların zamanında çalışması ve oturum açılışında hazır olması için.", "So reminders run on time and are ready after sign-in.", "Damit Erinnerungen pünktlich ausgeführt werden und nach der Anmeldung bereitstehen.", "Para que los recordatorios se ejecuten a tiempo y estén listos al iniciar sesión.", "Чтобы напоминания срабатывали вовремя и были готовы после входа.",
    ),
    "background_denied": (
        "Masaüstü arka planda çalışma izni vermedi.", "The desktop did not grant background permission.", "Die Desktop-Umgebung hat keine Hintergrundberechtigung erteilt.", "El escritorio no concedió permiso para funcionar en segundo plano.", "Рабочая среда не разрешила фоновую работу.",
    ),
    "background_request_failed": (
        "Arka plan izni istenemedi. Flatpak portal ayarlarını kontrol edip yeniden deneyin.", "Background permission could not be requested. Check the Flatpak portal settings and try again.", "Die Hintergrundberechtigung konnte nicht angefordert werden. Prüfe die Flatpak-Portal-Einstellungen und versuche es erneut.", "No se pudo solicitar el permiso en segundo plano. Comprueba el portal de Flatpak e inténtalo de nuevo.", "Не удалось запросить разрешение на фоновую работу. Проверьте настройки портала Flatpak и повторите попытку.",
    ),
    "quiet_hours_title": (
        "Sessiz saatler", "Quiet hours", "Ruhezeiten", "Horas silenciosas", "Тихие часы",
    ),
    "quiet_hours_detail": (
        "Bu saatlerde bilgisayar bildirimleri gösterilmez; e-posta teslimatı devam eder.", "Desktop notifications are hidden during these hours; email delivery continues.", "Während dieser Zeiten werden keine Desktop-Benachrichtigungen angezeigt; E-Mails werden weiter zugestellt.", "Durante estas horas no se muestran notificaciones de escritorio; el correo sigue enviándose.", "В эти часы уведомления на компьютере не показываются; доставка по почте продолжается.",
    ),
    "enabled": (
        "Etkin", "Enabled", "Aktiviert", "Activado", "Включено",
    ),
    "quiet_hours_saved": (
        "Sessiz saatler kaydedildi.", "Quiet hours saved.", "Ruhezeiten gespeichert.", "Horas silenciosas guardadas.", "Тихие часы сохранены.",
    ),
    "default_category_title": (
        "Varsayılan kategori", "Default category", "Standardkategorie", "Categoría predeterminada", "Категория по умолчанию",
    ),
    "default_category_detail": (
        "Yeni ve hızlı hatırlatmalarda kullanılacak kategori.", "The category used for new and quick reminders.", "Die Kategorie für neue und schnelle Erinnerungen.", "La categoría usada en recordatorios nuevos y rápidos.", "Категория для новых и быстрых напоминаний.",
    ),
    "default_category_saved": (
        "Varsayılan kategori kaydedildi.", "Default category saved.", "Standardkategorie gespeichert.", "Categoría predeterminada guardada.", "Категория по умолчанию сохранена.",
    ),
    "tray_behavior_title": (
        "Kapatınca sistem tepsisinde çalış", "Keep Running in the Tray on Close", "Beim Schließen im Infobereich weiterlaufen", "Seguir en la bandeja al cerrar", "Продолжать работу в трее после закрытия",
    ),
    "tray_behavior_detail": (
        "Açıkken × düğmesi pencereyi tepsiye gizler; hatırlatma motoru uygulama içinde çalışmaya devam eder.", "When enabled, the × button hides the window in the tray while the reminder engine keeps running in the app.", "Wenn aktiviert, verbirgt × das Fenster im Infobereich, während die Erinnerungsfunktion weiterläuft.", "Al activarlo, × oculta la ventana en la bandeja mientras el motor de recordatorios sigue funcionando.", "Если включено, кнопка × скрывает окно в трей, а механизм напоминаний продолжает работать.",
    ),
    "tray_behavior_saved": (
        "Sistem tepsisi davranışı kaydedildi.", "Tray behavior saved.", "Infobereich-Verhalten gespeichert.", "Comportamiento de la bandeja guardado.", "Поведение в трее сохранено.",
    ),
    "about_title": (
        "Hatırlatıcı Hakkında", "About Hatırlatıcı", "Über Hatırlatıcı", "Acerca de Hatırlatıcı", "О приложении Hatırlatıcı",
    ),
    "about_detail": (
        "Sürüm {version} • yerel veri • güvenli teslimat • otomatik yedekleme • tek uygulama örneği.", "Version {version} • local data • secure delivery • automatic backups • single application instance.", "Version {version} • lokale Daten • sichere Zustellung • automatische Sicherungen • eine Anwendungsinstanz.", "Versión {version} • datos locales • envío seguro • copias automáticas • una sola instancia de la aplicación.", "Версия {version} • локальные данные • защищённая доставка • автоматические резервные копии • один экземпляр приложения.",
    ),
    "support_detail": (
        "Reklamsız ve yerel öncelikli. Kimlik bilgileri güvenli kasada şifrelenir.", "Ad-free and local-first. Credentials are encrypted in the secure vault.", "Werbefrei und lokal ausgerichtet. Zugangsdaten werden im sicheren Tresor verschlüsselt.", "Sin anuncios y con prioridad local. Las credenciales se cifran en la caja segura.", "Без рекламы, с приоритетом локальной работы. Учётные данные зашифрованы в защищённом хранилище.",
    ),
    "tray_open": (
        "Hatırlatıcı'yı Aç", "Open Hatırlatıcı", "Hatırlatıcı öffnen", "Abrir Hatırlatıcı", "Открыть Hatırlatıcı",
    ),
    "tray_quick": (
        "Hızlı Hatırlatma", "Quick Reminder", "Schnellerinnerung", "Recordatorio rápido", "Быстрое напоминание",
    ),
    "quit": (
        "Çıkış", "Quit", "Beenden", "Salir", "Выйти",
    ),
    "tray_continues": (
        "Hatırlatıcı sistem tepsisinde çalışmaya devam ediyor.", "Hatırlatıcı is still running in the system tray.", "Hatırlatıcı läuft im Infobereich weiter.", "Hatırlatıcı sigue funcionando en la bandeja del sistema.", "Hatırlatıcı продолжает работать в системном трее.",
    ),
    "notification_complete": (
        "Tamamla", "Complete", "Erledigen", "Completar", "Завершить",
    ),
    "notification_snooze_minutes": (
        "{minutes} dk ertele", "Snooze {minutes} min", "{minutes} Min. später", "Posponer {minutes} min", "Отложить на {minutes} мин",
    ),
    "reminder_default_title": (
        "Hatırlatma", "Reminder", "Erinnerung", "Recordatorio", "Напоминание",
    ),
    "scheduler_status_monitoring": (
        "Hatırlatmalar izleniyor", "Monitoring reminders", "Erinnerungen werden überwacht", "Supervisando recordatorios", "Отслеживание напоминаний",
    ),
    "notification_delivery_failed": (
        "Bilgisayar bildirimi teslim edilemedi.", "The desktop notification could not be delivered.", "Die Desktop-Benachrichtigung konnte nicht zugestellt werden.", "No se pudo entregar la notificación de escritorio.", "Не удалось доставить уведомление на компьютер.",
    ),
    "portal_test_title": (
        "Hatırlatıcı", "Hatırlatıcı", "Hatırlatıcı", "Hatırlatıcı", "Hatırlatıcı",
    ),
    "portal_test_message": (
        "Bildirim bağlantısı çalışıyor.", "The notification connection is working.", "Die Benachrichtigungsverbindung funktioniert.", "La conexión de notificaciones funciona.", "Подключение уведомлений работает.",
    ),
    "portal_action_test_title": (
        "Hatırlatıcı • Bildirim Eylemi Testi", "Hatırlatıcı • Notification Action Test", "Hatırlatıcı • Benachrichtigungsaktionstest", "Hatırlatıcı • Prueba de acción de notificación", "Hatırlatıcı • Проверка действий уведомления",
    ),
    "portal_action_test_message": (
        "Bu bildirim Bildirim Portalı üzerinden geldi. Bir eylem seçin.", "This notification was delivered through the Notification Portal. Choose an action.", "Diese Benachrichtigung wurde über das Benachrichtigungsportal zugestellt. Wähle eine Aktion.", "Esta notificación se entregó mediante el portal de notificaciones. Elige una acción.", "Это уведомление доставлено через портал уведомлений. Выберите действие.",
    ),
    "scheduler_test_title": (
        "Hatırlatıcı • Zamanlayıcı Testi", "Hatırlatıcı • Scheduler Test", "Hatırlatıcı • Zeitplanertest", "Hatırlatıcı • Prueba del programador", "Hatırlatıcı • Проверка планировщика",
    ),
    "scheduler_test_message": (
        "Bu bildirim uygulama içi zamanlayıcı tarafından tetiklendi.", "This notification was triggered by the in-app scheduler.", "Diese Benachrichtigung wurde vom app-internen Zeitplaner ausgelöst.", "Esta notificación fue activada por el programador de la aplicación.", "Это уведомление запущено встроенным планировщиком приложения.",
    ),
    "source_repository": (
        "Kaynak kodu", "Source repository", "Quellcode", "Código fuente", "Исходный код",
    ),
    "privacy_policy": (
        "Gizlilik", "Privacy", "Datenschutz", "Privacidad", "Конфиденциальность",
    ),
    "report_issue": (
        "Sorun bildir", "Report an issue", "Problem melden", "Informar de un problema", "Сообщить о проблеме",
    ),
    "support_help": (
        "Yardım ve destek", "Help and support", "Hilfe und Support", "Ayuda y soporte", "Помощь и поддержка",
    ),
    "external_link_failed": (
        "Bağlantı varsayılan tarayıcıda açılamadı.", "The link could not be opened in the default browser.", "Der Link konnte nicht im Standardbrowser geöffnet werden.", "No se pudo abrir el enlace en el navegador predeterminado.", "Не удалось открыть ссылку в браузере по умолчанию.",
    ),
    "settings_language_title": (
        "Uygulama dili", "Application language", "Anwendungssprache", "Idioma de la aplicación", "Язык приложения",
    ),
    "settings_language_detail": (
        "Seçimin tüm uygulamaya hemen uygulanır ve kaydedilir.", "Your choice is applied to the entire application immediately and saved.", "Deine Auswahl wird sofort auf die gesamte Anwendung angewendet und gespeichert.", "Tu elección se aplica inmediatamente a toda la aplicación y se guarda.", "Выбранный язык сразу применяется ко всему приложению и сохраняется.",
    ),
    "language_changed": (
        "Uygulama dili değiştirildi.", "Application language changed.", "Anwendungssprache geändert.", "Se cambió el idioma de la aplicación.", "Язык приложения изменён.",
    ),
    "smtp_error_dns": (
        "E-posta sunucusunun adresi bulunamadı. Sunucu adını ve ağ bağlantısını kontrol edin.", "The email server address could not be found. Check the server name and network connection.", "Die Adresse des E-Mail-Servers wurde nicht gefunden. Prüfe Servernamen und Netzwerkverbindung.", "No se encontró la dirección del servidor de correo. Comprueba el nombre del servidor y la conexión de red.", "Адрес почтового сервера не найден. Проверьте имя сервера и подключение к сети.",
    ),
    "smtp_error_timeout": (
        "E-posta sunucusu zamanında yanıt vermedi. Bağlantıyı kontrol edip yeniden deneyin.", "The email server did not respond in time. Check the connection and try again.", "Der E-Mail-Server hat nicht rechtzeitig geantwortet. Prüfe die Verbindung und versuche es erneut.", "El servidor de correo no respondió a tiempo. Comprueba la conexión e inténtalo de nuevo.", "Почтовый сервер не ответил вовремя. Проверьте подключение и повторите попытку.",
    ),
    "smtp_error_tls": (
        "E-posta sunucusuyla güvenli bağlantı kurulamadı. Sertifika veya TLS ayarlarını kontrol edin.", "A secure connection to the email server could not be established. Check its certificate or TLS settings.", "Es konnte keine sichere Verbindung zum E-Mail-Server hergestellt werden. Prüfe Zertifikat oder TLS-Einstellungen.", "No se pudo establecer una conexión segura con el servidor de correo. Comprueba el certificado o la configuración TLS.", "Не удалось установить защищённое соединение с почтовым сервером. Проверьте сертификат или настройки TLS.",
    ),
    "smtp_error_auth": (
        "E-posta sunucusu kimlik bilgilerini kabul etmedi. Adresi ve uygulama parolasını kontrol edin.", "The email server did not accept the credentials. Check the address and app password.", "Der E-Mail-Server hat die Zugangsdaten abgelehnt. Prüfe Adresse und App-Passwort.", "El servidor de correo rechazó las credenciales. Comprueba la dirección y la contraseña de aplicación.", "Почтовый сервер отклонил учётные данные. Проверьте адрес и пароль приложения.",
    ),
    "smtp_error_invalid_sender": (
        "Gönderen adresi e-posta sunucusu tarafından kabul edilmedi.", "The sender address was not accepted by the email server.", "Die Absenderadresse wurde vom E-Mail-Server nicht akzeptiert.", "El servidor de correo no aceptó la dirección del remitente.", "Почтовый сервер не принял адрес отправителя.",
    ),
    "smtp_error_recipient_refused": (
        "Alıcı adresi e-posta sunucusu tarafından kabul edilmedi.", "The recipient address was not accepted by the email server.", "Die Empfängeradresse wurde vom E-Mail-Server nicht akzeptiert.", "El servidor de correo no aceptó la dirección del destinatario.", "Почтовый сервер не принял адрес получателя.",
    ),
    "smtp_error_offline": (
        "Ağ bağlantısı kullanılamıyor. İnternete bağlandıktan sonra yeniden deneyin.", "The network is unavailable. Try again after reconnecting to the internet.", "Das Netzwerk ist nicht verfügbar. Versuche es nach dem Wiederherstellen der Internetverbindung erneut.", "La red no está disponible. Inténtalo de nuevo cuando recuperes la conexión a Internet.", "Сеть недоступна. Повторите попытку после подключения к интернету.",
    ),
    "smtp_error_generic": (
        "E-posta gönderilemedi. Sunucu ayarlarını kontrol edip yeniden deneyin.", "The email could not be sent. Check the server settings and try again.", "Die E-Mail konnte nicht gesendet werden. Prüfe die Servereinstellungen und versuche es erneut.", "No se pudo enviar el correo. Comprueba la configuración del servidor e inténtalo de nuevo.", "Не удалось отправить письмо. Проверьте настройки сервера и повторите попытку.",
    ),
}

for _key, _translations in _MAIN_APP_ROWS.items():
    if len(_translations) != len(SUPPORTED_LANGUAGES):
        raise RuntimeError(
            f"Localization row has the wrong size: {_key}"
        )

    for _language, _value in zip(
        SUPPORTED_LANGUAGES,
        _translations,
    ):
        STRINGS[_language][_key] = _value


validate_catalog()
