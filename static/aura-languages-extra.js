(function () {
  const base = {
    profile: "Profile", settings: "Settings", account: "Account", logout: "Logout",
    activeCompany: "Active Company", aiModels: "AI models",
    chooseAiModels: "Choose AI models", language: "Language",
    languageVoice: "Language & voice", colorTheme: "Color theme",
    customizeWorkspace: "Customize your workspace", themeSettings: "Theme settings",
    billing: "Billing", subscriptionBilling: "MB Future Tech AI Subscription & Billing",
    billingDescription: "Plan, usage and payments", openBilling: "Open billing",
    conversationHistory: "Conversation history", apply: "Apply", reset: "Reset",
    selectAllAvailable: "Select all available", askAura: "Ask MB Future Tech AI anything...",
    send: "Send", connected: "Connected", disconnected: "Disconnected",
    connect: "Connect", disconnect: "Disconnect", online: "is online",
    offline: "is offline", morning: "Good morning", afternoon: "Good afternoon",
    evening: "Good evening", late: "Working late?", welcome: "Welcome back.",
    close: "Close", search: "Search...", refresh: "Refresh"
  };
  const translations = {
    spanish: {
      profile:"Perfil",settings:"Configuración",account:"Cuenta",logout:"Cerrar sesión",
      activeCompany:"Empresa activa",aiModels:"Modelos de IA",chooseAiModels:"Elegir modelos de IA",
      language:"Idioma",languageVoice:"Idioma y voz",colorTheme:"Tema de color",
      customizeWorkspace:"Personaliza tu espacio",themeSettings:"Configuración del tema",
      conversationHistory:"Historial de conversaciones",apply:"Aplicar",reset:"Restablecer",
      selectAllAvailable:"Seleccionar todos los disponibles",askAura:"Pregunta a MB Future Tech AI...",
      send:"Enviar",connected:"Conectado",disconnected:"Desconectado",connect:"Conectar",
      disconnect:"Desconectar",online:"está en línea",offline:"está sin conexión",
      morning:"Buenos días",afternoon:"Buenas tardes",evening:"Buenas noches",
      late:"¿Trabajando tarde?",welcome:"Bienvenido de nuevo.",close:"Cerrar",search:"Buscar...",refresh:"Actualizar"
    },
    french: {
      profile:"Profil",settings:"Paramètres",account:"Compte",logout:"Déconnexion",
      activeCompany:"Entreprise active",aiModels:"Modèles IA",chooseAiModels:"Choisir les modèles IA",
      language:"Langue",languageVoice:"Langue et voix",colorTheme:"Thème de couleur",
      customizeWorkspace:"Personnaliser l’espace",themeSettings:"Paramètres du thème",
      conversationHistory:"Historique des conversations",apply:"Appliquer",reset:"Réinitialiser",
      selectAllAvailable:"Tout sélectionner",askAura:"Demandez à MB Future Tech AI...",send:"Envoyer",
      connected:"Connecté",disconnected:"Déconnecté",connect:"Connecter",disconnect:"Déconnecter",
      online:"est en ligne",offline:"est hors ligne",morning:"Bonjour",afternoon:"Bon après-midi",
      evening:"Bonsoir",late:"Vous travaillez tard ?",welcome:"Bon retour.",close:"Fermer",search:"Rechercher...",refresh:"Actualiser",
      underMaintenance:"En maintenance",businessIntelligence:"Intelligence d’entreprise",analyticsReports:"Analyses et rapports",analyticsDescription:"Messages, clients, canaux et recommandations de ce tableau de bord",openAnalytics:"Ouvrir les analyses et rapports",
      socialConnections:"Connexions sociales",channels:"Canaux",socialConnectionsHelp:"Connectez ce tableau de bord aux comptes de messagerie de vos clients.",loginRequiredConnect:"Connexion requise pour établir la liaison.",login:"Se connecter",notConnected:"Non connecté",continueFacebook:"Continuer avec Facebook",advancedManualSetup:"Configuration manuelle avancée",directMessages:"Messages directs",businessMessaging:"Messagerie professionnelle",botMessages:"Messages du bot",comingSoon:"Bientôt disponible",
      dashboard:"Tableau de bord",companyProfileManager:"Gestionnaire du profil d’entreprise",discardChanges:"Annuler les modifications",profileEditor:"Éditeur de profil",profileEditorHelp:"Collez, modifiez et vérifiez ici le profil d’entreprise organisé par l’IA.",companyProfile:"Profil d’entreprise",searchWord:"Rechercher un mot…",clearAll:"Tout effacer",pasteWebsiteLink:"Coller le lien public du site…",import:"Importer",saveAutoEdit:"Enregistrer et modifier automatiquement",
      aiAssistant:"Assistant IA",aiAssistantHelp:"Les suggestions et avertissements apparaissent ici. Le brouillon modifié par l’IA reste dans l’éditeur.",pasteThenAutoEdit:"Collez ou modifiez un profil, puis choisissez Enregistrer et modifier automatiquement.",testAndHistory:"Tester votre IA et historique du profil",testYourAi:"Tester votre IA",customizeResponses:"Personnaliser les réponses",testAiHelp:"Testez une question client avec le profil proposé. Les messages de test ne sont pas ajoutés à l’historique client.",trySampleQuestion:"Essayer une question",askPreview:"Posez une question pour prévisualiser la réponse de votre IA.",sampleQuestionPlaceholder:"Poser une question client d’exemple…",profileVersionHistory:"Historique des versions du profil",versionHistoryHelp:"Revenez à un ancien profil ou supprimez définitivement une sauvegarde.",
      systemGuide:"Guide du système MB",systemGuideWelcome:"Bonjour ! Demandez-moi comment utiliser une fonction du système MB Future Tech AI Chatbot.",askSystemGuide:"Demander comment utiliser le système…",saveName:"Enregistrer le nom",useThisVersion:"Utiliser cette version",delete:"Supprimer",previousProfile:"Profil précédent",noPreviousVersions:"Aucune version précédente.",loginRequired:"Connexion requise",loginConnectFacebook:"Se connecter pour relier Facebook",manageFacebook:"Gérer Facebook",connectionUnavailable:"Connexion indisponible",checkServer:"Vérifier le serveur",manageDashboards:"Gérer les tableaux de bord",manageDashboardsHelp:"Ajouter, renommer ou changer d’espace de travail",saved:"Enregistré",waiting:"En attente",connecting:"Connexion…",aiArrangingProfile:"L’IA organise votre profil d’entreprise…",aiCheckingProfile:"Vérification des doublons, conflits, informations manquantes et ordre des sections.",chooseAiModel:"Choisir un modèle IA",noAiModelAvailable:"Aucun modèle IA disponible",aiModelsOffline:"Les modèles IA sont hors ligne",manage:"Gérer",systemKey:"Clé système",apiKeyRequired:"Clé API requise",previewOnly:"Aperçu uniquement — connectez une clé API {provider} pour utiliser ce modèle.",loginAiProviders:"Connectez-vous pour relier vos fournisseurs IA.",couldNotLoadProviders:"Impossible de charger les fournisseurs IA.",providerUnavailable:"Fournisseur indisponible",aiConnectionUnavailable:"Connexion IA indisponible"
    },
    german: {
      profile:"Profil",settings:"Einstellungen",account:"Konto",logout:"Abmelden",
      activeCompany:"Aktives Unternehmen",aiModels:"KI-Modelle",chooseAiModels:"KI-Modelle auswählen",
      language:"Sprache",languageVoice:"Sprache und Stimme",colorTheme:"Farbthema",
      customizeWorkspace:"Arbeitsbereich anpassen",themeSettings:"Theme-Einstellungen",
      conversationHistory:"Gesprächsverlauf",apply:"Anwenden",reset:"Zurücksetzen",
      selectAllAvailable:"Alle verfügbaren auswählen",askAura:"MB Future Tech AI etwas fragen...",send:"Senden",
      connected:"Verbunden",disconnected:"Getrennt",connect:"Verbinden",disconnect:"Trennen",
      online:"ist online",offline:"ist offline",morning:"Guten Morgen",afternoon:"Guten Tag",
      evening:"Guten Abend",late:"Arbeiten Sie noch?",welcome:"Willkommen zurück.",close:"Schließen",search:"Suchen...",refresh:"Aktualisieren",
      underMaintenance:"In Wartung",businessIntelligence:"Business Intelligence",analyticsReports:"Analysen & Berichte",analyticsDescription:"Nachrichten, Kunden, Kanäle und Empfehlungen für dieses Dashboard",openAnalytics:"Analysen und Berichte öffnen",
      socialConnections:"Soziale Verbindungen",channels:"Kanäle",socialConnectionsHelp:"Verbinden Sie dieses Dashboard mit den Messaging-Konten Ihrer Kunden.",loginRequiredConnect:"Zum Verbinden ist eine Anmeldung erforderlich.",login:"Anmelden",notConnected:"Nicht verbunden",continueFacebook:"Mit Facebook fortfahren",advancedManualSetup:"Erweiterte manuelle Einrichtung",directMessages:"Direktnachrichten",businessMessaging:"Business-Messaging",botMessages:"Bot-Nachrichten",comingSoon:"Demnächst verfügbar",
      dashboard:"Dashboard",companyProfileManager:"Unternehmensprofil-Manager",discardChanges:"Änderungen verwerfen",profileEditor:"Profil-Editor",profileEditorHelp:"Fügen Sie das vom KI-System geordnete Unternehmensprofil in diesem Editor ein, bearbeiten und prüfen Sie es.",companyProfile:"Unternehmensprofil",searchWord:"Wort suchen…",clearAll:"Alles löschen",pasteWebsiteLink:"Öffentlichen Website-Link einfügen…",import:"Importieren",saveAutoEdit:"Speichern & automatisch bearbeiten",
      aiAssistant:"KI-Assistent",aiAssistantHelp:"Vorschläge und Warnungen erscheinen hier. Der KI-bearbeitete Entwurf bleibt im Profil-Editor.",pasteThenAutoEdit:"Fügen Sie ein Unternehmensprofil ein oder bearbeiten Sie es und wählen Sie dann Speichern & automatisch bearbeiten.",testAndHistory:"KI testen & Profilversionsverlauf",testYourAi:"KI testen",customizeResponses:"Antworten anpassen",testAiHelp:"Testen Sie eine Kundenfrage mit dem vorgeschlagenen Unternehmensprofil. Testnachrichten werden nicht im Kundenverlauf gespeichert.",trySampleQuestion:"Beispielfrage testen",askPreview:"Stellen Sie eine Frage, um die Antwort Ihrer KI zu prüfen.",sampleQuestionPlaceholder:"Beispielfrage eines Kunden eingeben…",profileVersionHistory:"Profilversionsverlauf",versionHistoryHelp:"Kehren Sie zu einem früheren Profil zurück oder löschen Sie eine alte Sicherung dauerhaft.",
      systemGuide:"MB-Systemleitfaden",systemGuideWelcome:"Hallo! Fragen Sie mich, wie Sie eine Funktion des MB Future Tech AI Chatbot-Systems verwenden.",askSystemGuide:"Fragen Sie, wie das System verwendet wird…",saveName:"Name speichern",useThisVersion:"Diese Version verwenden",delete:"Löschen",previousProfile:"Vorheriges Profil",noPreviousVersions:"Noch keine früheren Versionen.",loginRequired:"Anmeldung erforderlich",loginConnectFacebook:"Anmelden, um Facebook zu verbinden",manageFacebook:"Facebook verwalten",connectionUnavailable:"Verbindung nicht verfügbar",checkServer:"Server prüfen",manageDashboards:"Dashboards verwalten",manageDashboardsHelp:"AI-Chatbot-Arbeitsbereiche hinzufügen, umbenennen oder wechseln",saved:"Gespeichert",waiting:"Warten",connecting:"Verbindung wird hergestellt…",aiArrangingProfile:"Die KI ordnet Ihr Unternehmensprofil…",aiCheckingProfile:"Duplikate, Konflikte, fehlende Angaben und Abschnittsreihenfolge werden geprüft."
    },
    italian: {
      profile:"Profilo",settings:"Impostazioni",account:"Account",logout:"Esci",
      activeCompany:"Azienda attiva",aiModels:"Modelli IA",chooseAiModels:"Scegli modelli IA",
      language:"Lingua",languageVoice:"Lingua e voce",colorTheme:"Tema colore",
      customizeWorkspace:"Personalizza lo spazio",themeSettings:"Impostazioni tema",
      conversationHistory:"Cronologia conversazioni",apply:"Applica",reset:"Ripristina",
      selectAllAvailable:"Seleziona tutti",askAura:"Chiedi a MB Future Tech AI...",send:"Invia",
      connected:"Connesso",disconnected:"Disconnesso",connect:"Connetti",disconnect:"Disconnetti",
      online:"è online",offline:"è offline",morning:"Buongiorno",afternoon:"Buon pomeriggio",
      evening:"Buonasera",late:"Lavori fino a tardi?",welcome:"Bentornato.",close:"Chiudi",search:"Cerca...",refresh:"Aggiorna"
    },
    portuguese: {
      profile:"Perfil",settings:"Configurações",account:"Conta",logout:"Sair",
      activeCompany:"Empresa ativa",aiModels:"Modelos de IA",chooseAiModels:"Escolher modelos de IA",
      language:"Idioma",languageVoice:"Idioma e voz",colorTheme:"Tema de cores",
      customizeWorkspace:"Personalizar espaço",themeSettings:"Configurações do tema",
      conversationHistory:"Histórico de conversas",apply:"Aplicar",reset:"Redefinir",
      selectAllAvailable:"Selecionar todos",askAura:"Pergunte à MB Future Tech AI...",send:"Enviar",
      connected:"Conectado",disconnected:"Desconectado",connect:"Conectar",disconnect:"Desconectar",
      online:"está online",offline:"está offline",morning:"Bom dia",afternoon:"Boa tarde",
      evening:"Boa noite",late:"Trabalhando até tarde?",welcome:"Bem-vindo de volta.",close:"Fechar",search:"Pesquisar...",refresh:"Atualizar"
    },
    arabic: {
      profile:"الملف الشخصي",settings:"الإعدادات",account:"الحساب",logout:"تسجيل الخروج",
      activeCompany:"الشركة النشطة",aiModels:"نماذج الذكاء الاصطناعي",chooseAiModels:"اختيار نماذج الذكاء الاصطناعي",
      language:"اللغة",languageVoice:"اللغة والصوت",colorTheme:"سمة الألوان",
      customizeWorkspace:"تخصيص مساحة العمل",themeSettings:"إعدادات السمة",
      conversationHistory:"سجل المحادثات",apply:"تطبيق",reset:"إعادة ضبط",
      selectAllAvailable:"تحديد كل المتاح",askAura:"اسأل MB Future Tech AI أي شيء...",send:"إرسال",
      connected:"متصل",disconnected:"غير متصل",connect:"اتصال",disconnect:"قطع الاتصال",
      online:"متصل بالإنترنت",offline:"غير متصل",morning:"صباح الخير",afternoon:"مساء الخير",
      evening:"مساء الخير",late:"هل تعمل لوقت متأخر؟",welcome:"مرحبًا بعودتك.",close:"إغلاق",search:"بحث...",refresh:"تحديث"
    },
    russian: {
      profile:"Профиль",settings:"Настройки",account:"Аккаунт",logout:"Выйти",
      activeCompany:"Активная компания",aiModels:"Модели ИИ",chooseAiModels:"Выбрать модели ИИ",
      language:"Язык",languageVoice:"Язык и голос",colorTheme:"Цветовая тема",
      customizeWorkspace:"Настроить рабочее пространство",themeSettings:"Настройки темы",
      conversationHistory:"История разговоров",apply:"Применить",reset:"Сбросить",
      selectAllAvailable:"Выбрать все доступные",askAura:"Спросите MB Future Tech AI...",send:"Отправить",
      connected:"Подключено",disconnected:"Отключено",connect:"Подключить",disconnect:"Отключить",
      online:"в сети",offline:"не в сети",morning:"Доброе утро",afternoon:"Добрый день",
      evening:"Добрый вечер",late:"Работаете допоздна?",welcome:"С возвращением.",close:"Закрыть",search:"Поиск...",refresh:"Обновить"
    },
    thai: {
      profile:"โปรไฟล์",settings:"การตั้งค่า",account:"บัญชี",logout:"ออกจากระบบ",
      activeCompany:"บริษัทที่ใช้งาน",aiModels:"โมเดล AI",chooseAiModels:"เลือกโมเดล AI",
      language:"ภาษา",languageVoice:"ภาษาและเสียง",colorTheme:"ธีมสี",
      customizeWorkspace:"ปรับแต่งพื้นที่ทำงาน",themeSettings:"การตั้งค่าธีม",
      conversationHistory:"ประวัติการสนทนา",apply:"นำไปใช้",reset:"รีเซ็ต",
      selectAllAvailable:"เลือกทั้งหมดที่ใช้ได้",askAura:"ถาม MB Future Tech AI ได้ทุกเรื่อง...",send:"ส่ง",
      connected:"เชื่อมต่อแล้ว",disconnected:"ไม่ได้เชื่อมต่อ",connect:"เชื่อมต่อ",disconnect:"ตัดการเชื่อมต่อ",
      online:"ออนไลน์",offline:"ออฟไลน์",morning:"สวัสดีตอนเช้า",afternoon:"สวัสดีตอนบ่าย",
      evening:"สวัสดีตอนเย็น",late:"ยังทำงานอยู่หรือ?",welcome:"ยินดีต้อนรับกลับ",close:"ปิด",search:"ค้นหา...",refresh:"รีเฟรช"
    },
    vietnamese: {
      profile:"Hồ sơ",settings:"Cài đặt",account:"Tài khoản",logout:"Đăng xuất",
      activeCompany:"Công ty đang hoạt động",aiModels:"Mô hình AI",chooseAiModels:"Chọn mô hình AI",
      language:"Ngôn ngữ",languageVoice:"Ngôn ngữ và giọng nói",colorTheme:"Chủ đề màu",
      customizeWorkspace:"Tùy chỉnh không gian",themeSettings:"Cài đặt chủ đề",
      conversationHistory:"Lịch sử trò chuyện",apply:"Áp dụng",reset:"Đặt lại",
      selectAllAvailable:"Chọn tất cả",askAura:"Hỏi MB Future Tech AI bất cứ điều gì...",send:"Gửi",
      connected:"Đã kết nối",disconnected:"Đã ngắt",connect:"Kết nối",disconnect:"Ngắt kết nối",
      online:"đang trực tuyến",offline:"đang ngoại tuyến",morning:"Chào buổi sáng",afternoon:"Chào buổi chiều",
      evening:"Chào buổi tối",late:"Bạn vẫn đang làm việc?",welcome:"Chào mừng trở lại.",close:"Đóng",search:"Tìm kiếm...",refresh:"Làm mới"
    },
    indonesian: {
      profile:"Profil",settings:"Pengaturan",account:"Akun",logout:"Keluar",
      activeCompany:"Perusahaan aktif",aiModels:"Model AI",chooseAiModels:"Pilih model AI",
      language:"Bahasa",languageVoice:"Bahasa dan suara",colorTheme:"Tema warna",
      customizeWorkspace:"Sesuaikan ruang kerja",themeSettings:"Pengaturan tema",
      conversationHistory:"Riwayat percakapan",apply:"Terapkan",reset:"Atur ulang",
      selectAllAvailable:"Pilih semua yang tersedia",askAura:"Tanyakan apa saja kepada MB Future Tech AI...",send:"Kirim",
      connected:"Terhubung",disconnected:"Terputus",connect:"Hubungkan",disconnect:"Putuskan",
      online:"sedang online",offline:"sedang offline",morning:"Selamat pagi",afternoon:"Selamat siang",
      evening:"Selamat malam",late:"Masih bekerja?",welcome:"Selamat datang kembali.",close:"Tutup",search:"Cari...",refresh:"Segarkan"
    },
    malay: {
      profile:"Profil",settings:"Tetapan",account:"Akaun",logout:"Log keluar",
      activeCompany:"Syarikat aktif",aiModels:"Model AI",chooseAiModels:"Pilih model AI",
      language:"Bahasa",languageVoice:"Bahasa dan suara",colorTheme:"Tema warna",
      customizeWorkspace:"Sesuaikan ruang kerja",themeSettings:"Tetapan tema",
      conversationHistory:"Sejarah perbualan",apply:"Guna",reset:"Tetapkan semula",
      selectAllAvailable:"Pilih semua yang tersedia",askAura:"Tanya MB Future Tech AI apa sahaja...",send:"Hantar",
      connected:"Disambungkan",disconnected:"Terputus",connect:"Sambung",disconnect:"Putuskan",
      online:"dalam talian",offline:"luar talian",morning:"Selamat pagi",afternoon:"Selamat petang",
      evening:"Selamat malam",late:"Masih bekerja?",welcome:"Selamat kembali.",close:"Tutup",search:"Cari...",refresh:"Muat semula"
    },
    turkish: {
      profile:"Profil",settings:"Ayarlar",account:"Hesap",logout:"Çıkış",
      activeCompany:"Aktif şirket",aiModels:"AI modelleri",chooseAiModels:"AI modellerini seç",
      language:"Dil",languageVoice:"Dil ve ses",colorTheme:"Renk teması",
      customizeWorkspace:"Çalışma alanını özelleştir",themeSettings:"Tema ayarları",
      conversationHistory:"Konuşma geçmişi",apply:"Uygula",reset:"Sıfırla",
      selectAllAvailable:"Tüm kullanılabilirleri seç",askAura:"MB Future Tech AI'a bir şey sorun...",send:"Gönder",
      connected:"Bağlı",disconnected:"Bağlı değil",connect:"Bağlan",disconnect:"Bağlantıyı kes",
      online:"çevrimiçi",offline:"çevrimdışı",morning:"Günaydın",afternoon:"İyi günler",
      evening:"İyi akşamlar",late:"Geç saate kadar mı çalışıyorsunuz?",welcome:"Tekrar hoş geldiniz.",close:"Kapat",search:"Ara...",refresh:"Yenile"
    },
    dutch: {
      profile:"Profiel",settings:"Instellingen",account:"Account",logout:"Uitloggen",
      activeCompany:"Actief bedrijf",aiModels:"AI-modellen",chooseAiModels:"AI-modellen kiezen",
      language:"Taal",languageVoice:"Taal en stem",colorTheme:"Kleurthema",
      customizeWorkspace:"Werkruimte aanpassen",themeSettings:"Thema-instellingen",
      conversationHistory:"Gespreksgeschiedenis",apply:"Toepassen",reset:"Resetten",
      selectAllAvailable:"Alles selecteren",askAura:"Vraag MB Future Tech AI iets...",send:"Verzenden",
      connected:"Verbonden",disconnected:"Niet verbonden",connect:"Verbinden",disconnect:"Verbinding verbreken",
      online:"is online",offline:"is offline",morning:"Goedemorgen",afternoon:"Goedemiddag",
      evening:"Goedenavond",late:"Werk je nog laat?",welcome:"Welkom terug.",close:"Sluiten",search:"Zoeken...",refresh:"Vernieuwen",
      underMaintenance:"In onderhoud",businessIntelligence:"Bedrijfsinformatie",analyticsReports:"Analyses & rapporten",analyticsDescription:"Berichten, klanten, kanalen en aanbevelingen voor dit dashboard",openAnalytics:"Analyses en rapporten openen",
      socialConnections:"Sociale verbindingen",channels:"Kanalen",socialConnectionsHelp:"Verbind dit dashboard met de berichtenaccounts van uw klanten.",loginRequiredConnect:"Aanmelden vereist om te verbinden.",login:"Aanmelden",notConnected:"Niet verbonden",continueFacebook:"Doorgaan met Facebook",advancedManualSetup:"Geavanceerde handmatige instelling",directMessages:"Directe berichten",businessMessaging:"Zakelijke berichten",botMessages:"Botberichten",comingSoon:"Binnenkort beschikbaar",
      dashboard:"Dashboard",companyProfileManager:"Bedrijfsprofielbeheer",discardChanges:"Wijzigingen negeren",profileEditor:"Profieleditor",profileEditorHelp:"Plak, bewerk en controleer het door AI geordende bedrijfsprofiel in deze editor.",companyProfile:"Bedrijfsprofiel",searchWord:"Woord zoeken…",clearAll:"Alles wissen",pasteWebsiteLink:"Openbare websitelink plakken…",import:"Importeren",saveAutoEdit:"Opslaan & automatisch bewerken",
      aiAssistant:"AI-assistent",aiAssistantHelp:"Suggesties en waarschuwingen verschijnen hier. Het door AI bewerkte concept blijft in de profieleditor.",pasteThenAutoEdit:"Plak of bewerk een bedrijfsprofiel en kies daarna Opslaan & automatisch bewerken.",testAndHistory:"Test uw AI & profielversiegeschiedenis",testYourAi:"Test uw AI",customizeResponses:"Antwoorden aanpassen",testAiHelp:"Test een klantvraag met het voorgestelde bedrijfsprofiel. Testberichten worden niet toegevoegd aan de klantgeschiedenis.",trySampleQuestion:"Probeer een voorbeeldvraag",askPreview:"Stel een vraag om te bekijken hoe uw AI antwoordt.",sampleQuestionPlaceholder:"Stel een voorbeeldvraag van een klant…",profileVersionHistory:"Profielversiegeschiedenis",versionHistoryHelp:"Ga terug naar een eerder profiel of verwijder een oude back-up definitief.",
      systemGuide:"MB-systeemgids",systemGuideWelcome:"Hallo! Vraag mij hoe u een functie van het MB Future Tech AI Chatbot-systeem gebruikt.",askSystemGuide:"Vraag hoe u het systeem gebruikt…",saveName:"Naam opslaan",useThisVersion:"Deze versie gebruiken",delete:"Verwijderen",previousProfile:"Vorig profiel",noPreviousVersions:"Nog geen vorige versies.",loginRequired:"Aanmelden vereist",loginConnectFacebook:"Aanmelden om Facebook te verbinden",manageFacebook:"Facebook beheren",connectionUnavailable:"Verbinding niet beschikbaar",checkServer:"Server controleren",manageDashboards:"Dashboards beheren",manageDashboardsHelp:"AI Chatbot-werkruimten toevoegen, hernoemen of wisselen",saved:"Opgeslagen",waiting:"Wachten",connecting:"Verbinden…",aiArrangingProfile:"AI ordent uw bedrijfsprofiel…",aiCheckingProfile:"Duplicaten, conflicten, ontbrekende gegevens en sectievolgorde worden gecontroleerd."
    },
    polish: {
      profile:"Profil",settings:"Ustawienia",account:"Konto",logout:"Wyloguj",
      activeCompany:"Aktywna firma",aiModels:"Modele AI",chooseAiModels:"Wybierz modele AI",
      language:"Język",languageVoice:"Język i głos",colorTheme:"Motyw kolorów",
      customizeWorkspace:"Dostosuj obszar roboczy",themeSettings:"Ustawienia motywu",
      conversationHistory:"Historia rozmów",apply:"Zastosuj",reset:"Resetuj",
      selectAllAvailable:"Wybierz wszystkie dostępne",askAura:"Zapytaj MB Future Tech AI o cokolwiek...",send:"Wyślij",
      connected:"Połączono",disconnected:"Rozłączono",connect:"Połącz",disconnect:"Rozłącz",
      online:"jest online",offline:"jest offline",morning:"Dzień dobry",afternoon:"Dzień dobry",
      evening:"Dobry wieczór",late:"Pracujesz do późna?",welcome:"Witamy ponownie.",close:"Zamknij",search:"Szukaj...",refresh:"Odśwież"
    },
    ukrainian: {
      profile:"Профіль",settings:"Налаштування",account:"Обліковий запис",logout:"Вийти",
      activeCompany:"Активна компанія",aiModels:"Моделі ШІ",chooseAiModels:"Вибрати моделі ШІ",
      language:"Мова",languageVoice:"Мова та голос",colorTheme:"Кольорова тема",
      customizeWorkspace:"Налаштувати робочий простір",themeSettings:"Налаштування теми",
      conversationHistory:"Історія розмов",apply:"Застосувати",reset:"Скинути",
      selectAllAvailable:"Вибрати всі доступні",askAura:"Запитайте MB Future Tech AI про що завгодно...",send:"Надіслати",
      connected:"Підключено",disconnected:"Відключено",connect:"Підключити",disconnect:"Відключити",
      online:"онлайн",offline:"офлайн",morning:"Доброго ранку",afternoon:"Добрий день",
      evening:"Добрий вечір",late:"Працюєте допізна?",welcome:"З поверненням.",close:"Закрити",search:"Пошук...",refresh:"Оновити"
    }
  };
  Object.keys(translations).forEach(function (language) {
    translations[language] = Object.assign({}, base, translations[language]);
  });
  window.auraExtraTranslations = translations;
}());
