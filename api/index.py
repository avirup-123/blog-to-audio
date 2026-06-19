import asyncio
import base64
import json
import os
os.environ.setdefault("PYTHONUTF8", "1")
import re
import sys
import tempfile
import traceback

from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, Response
import requests as http_requests

edge_tts = None
genai = None

def _load_edge_tts():
    global edge_tts
    if edge_tts is None:
        import edge_tts as _edge_tts
        edge_tts = _edge_tts
    return edge_tts

def _load_genai():
    global genai
    if genai is None:
        from google import genai as _genai
        genai = _genai
    return genai

WORD_COUNT_THRESHOLD = 3000
CONDENSED_TARGET_WORDS = 2500

LANGUAGES = {
    "en": {
        "name": "English", "flag": "🇺🇸",
        "title": "Text to Audio",
        "subtitle": "Convert text and blog posts into natural-sounding MP3 audio files",
        "tab_url": "From URL", "tab_paste": "Paste Text",
        "label_lang": "Language", "label_voice": "Voice", "label_url": "Content URL", "label_content": "Your text content", "label_slug": "Filename slug",
        "btn_convert": "Convert to Audio", "btn_converting": "Converting...",
        "result_title": "Conversion Complete", "result_source": "Source", "result_wc": "Word count", "result_condensed": "Condensed", "result_condensed_wc": "Final word count", "result_duration": "Duration", "result_download": "Download MP3",
        "err_url": "Please enter a URL", "err_content": "Please paste your blog content", "err_slug": "Please enter a filename slug",
        "placeholder_url": "https://example.com/blog/my-post", "placeholder_content": "Paste your blog post content here...", "placeholder_slug": "my-blog-post-title",
        "voices": {"en-US-JennyNeural": "Jenny (US Female)", "en-US-AriaNeural": "Aria (US Female)", "en-US-GuyNeural": "Guy (US Male)", "en-US-ChristopherNeural": "Christopher (US Male)", "en-US-AndrewNeural": "Andrew (US Male)", "en-US-EmmaNeural": "Emma (US Female)", "en-US-BrianNeural": "Brian (US Male)", "en-GB-SoniaNeural": "Sonia (UK Female)", "en-GB-RyanNeural": "Ryan (UK Male)", "en-AU-NatashaNeural": "Natasha (AU Female)", "en-IN-NeerjaNeural": "Neerja (IN Female)"},
        "default_voice": "en-US-JennyNeural",
    },
    "es": {
        "name": "Español", "flag": "🇪🇸",
        "title": "Blog a Audio",
        "subtitle": "Convierte publicaciones de blog en archivos de audio MP3 con voz natural",
        "tab_url": "Desde URL", "tab_paste": "Pegar texto",
        "label_lang": "Idioma", "label_voice": "Voz", "label_url": "URL del artículo", "label_content": "Contenido del blog", "label_slug": "Nombre del archivo",
        "btn_convert": "Convertir a audio", "btn_converting": "Convirtiendo...",
        "result_title": "Conversión completada", "result_source": "Fuente", "result_wc": "Palabras", "result_condensed": "Condensado", "result_condensed_wc": "Palabras finales", "result_duration": "Duración", "result_download": "Descargar MP3",
        "err_url": "Introduce una URL", "err_content": "Pega el contenido de tu blog", "err_slug": "Introduce un nombre de archivo",
        "placeholder_url": "https://ejemplo.com/blog/mi-articulo", "placeholder_content": "Pega el contenido de tu blog aquí...", "placeholder_slug": "mi-articulo-de-blog",
        "voices": {"es-ES-ElviraNeural": "Elvira (España)", "es-ES-AlvaroNeural": "Álvaro (España)", "es-MX-DaliaNeural": "Dalia (México)", "es-MX-JorgeNeural": "Jorge (México)", "es-AR-ElenaNeural": "Elena (Argentina)"},
        "default_voice": "es-ES-ElviraNeural",
    },
    "fr": {
        "name": "Français", "flag": "🇫🇷",
        "title": "Blog en Audio",
        "subtitle": "Convertissez vos articles de blog en fichiers audio MP3 naturels",
        "tab_url": "Depuis URL", "tab_paste": "Coller le texte",
        "label_lang": "Langue", "label_voice": "Voix", "label_url": "URL de l'article", "label_content": "Contenu du blog", "label_slug": "Nom du fichier",
        "btn_convert": "Convertir en audio", "btn_converting": "Conversion...",
        "result_title": "Conversion terminée", "result_source": "Source", "result_wc": "Mots", "result_condensed": "Condensé", "result_condensed_wc": "Mots finaux", "result_duration": "Durée", "result_download": "Télécharger MP3",
        "err_url": "Veuillez entrer une URL", "err_content": "Veuillez coller votre contenu", "err_slug": "Veuillez entrer un nom de fichier",
        "placeholder_url": "https://exemple.com/blog/mon-article", "placeholder_content": "Collez le contenu de votre blog ici...", "placeholder_slug": "mon-article-de-blog",
        "voices": {"fr-FR-DeniseNeural": "Denise (France)", "fr-FR-HenriNeural": "Henri (France)", "fr-CA-SylvieNeural": "Sylvie (Canada)", "fr-CA-AntoineNeural": "Antoine (Canada)"},
        "default_voice": "fr-FR-DeniseNeural",
    },
    "de": {
        "name": "Deutsch", "flag": "🇩🇪",
        "title": "Blog zu Audio",
        "subtitle": "Verwandeln Sie Blogbeiträge in natürlich klingende MP3-Audiodateien",
        "tab_url": "Von URL", "tab_paste": "Text einfügen",
        "label_lang": "Sprache", "label_voice": "Stimme", "label_url": "Artikel-URL", "label_content": "Blog-Inhalt", "label_slug": "Dateiname",
        "btn_convert": "In Audio umwandeln", "btn_converting": "Wird konvertiert...",
        "result_title": "Konvertierung abgeschlossen", "result_source": "Quelle", "result_wc": "Wörter", "result_condensed": "Gekürzt", "result_condensed_wc": "Finale Wörter", "result_duration": "Dauer", "result_download": "MP3 herunterladen",
        "err_url": "Bitte URL eingeben", "err_content": "Bitte Inhalt einfügen", "err_slug": "Bitte Dateiname eingeben",
        "placeholder_url": "https://beispiel.de/blog/mein-artikel", "placeholder_content": "Blog-Inhalt hier einfügen...", "placeholder_slug": "mein-blog-artikel",
        "voices": {"de-DE-KatjaNeural": "Katja", "de-DE-ConradNeural": "Conrad", "de-DE-AmalaNeural": "Amala", "de-AT-IngridNeural": "Ingrid (AT)"},
        "default_voice": "de-DE-KatjaNeural",
    },
    "pt": {
        "name": "Português", "flag": "🇧🇷",
        "title": "Blog para Áudio",
        "subtitle": "Converta posts de blog em arquivos de áudio MP3 com voz natural",
        "tab_url": "Da URL", "tab_paste": "Colar texto",
        "label_lang": "Idioma", "label_voice": "Voz", "label_url": "URL do artigo", "label_content": "Conteúdo do blog", "label_slug": "Nome do arquivo",
        "btn_convert": "Converter para áudio", "btn_converting": "Convertendo...",
        "result_title": "Conversão concluída", "result_source": "Fonte", "result_wc": "Palavras", "result_condensed": "Condensado", "result_condensed_wc": "Palavras finais", "result_duration": "Duração", "result_download": "Baixar MP3",
        "err_url": "Insira uma URL", "err_content": "Cole o conteúdo do blog", "err_slug": "Insira um nome de arquivo",
        "placeholder_url": "https://exemplo.com/blog/meu-artigo", "placeholder_content": "Cole o conteúdo do blog aqui...", "placeholder_slug": "meu-artigo-de-blog",
        "voices": {"pt-BR-FranciscaNeural": "Francisca (BR)", "pt-BR-AntonioNeural": "Antonio (BR)", "pt-PT-RaquelNeural": "Raquel (PT)", "pt-PT-DuarteNeural": "Duarte (PT)"},
        "default_voice": "pt-BR-FranciscaNeural",
    },
    "it": {
        "name": "Italiano", "flag": "🇮🇹",
        "title": "Blog in Audio",
        "subtitle": "Converti i post del blog in file audio MP3 con voce naturale",
        "tab_url": "Da URL", "tab_paste": "Incolla testo",
        "label_lang": "Lingua", "label_voice": "Voce", "label_url": "URL dell'articolo", "label_content": "Contenuto del blog", "label_slug": "Nome file",
        "btn_convert": "Converti in audio", "btn_converting": "Conversione...",
        "result_title": "Conversione completata", "result_source": "Fonte", "result_wc": "Parole", "result_condensed": "Condensato", "result_condensed_wc": "Parole finali", "result_duration": "Durata", "result_download": "Scarica MP3",
        "err_url": "Inserisci un URL", "err_content": "Incolla il contenuto del blog", "err_slug": "Inserisci un nome file",
        "placeholder_url": "https://esempio.it/blog/mio-articolo", "placeholder_content": "Incolla il contenuto del blog qui...", "placeholder_slug": "mio-articolo-blog",
        "voices": {"it-IT-ElsaNeural": "Elsa", "it-IT-IsabellaNeural": "Isabella", "it-IT-DiegoNeural": "Diego", "it-IT-GiuseppeMultilingualNeural": "Giuseppe"},
        "default_voice": "it-IT-ElsaNeural",
    },
    "nl": {
        "name": "Nederlands", "flag": "🇳🇱",
        "title": "Blog naar Audio",
        "subtitle": "Zet blogberichten om in natuurlijk klinkende MP3-audiobestanden",
        "tab_url": "Van URL", "tab_paste": "Tekst plakken",
        "label_lang": "Taal", "label_voice": "Stem", "label_url": "Artikel-URL", "label_content": "Bloginhoud", "label_slug": "Bestandsnaam",
        "btn_convert": "Omzetten naar audio", "btn_converting": "Bezig met converteren...",
        "result_title": "Conversie voltooid", "result_source": "Bron", "result_wc": "Woorden", "result_condensed": "Ingekort", "result_condensed_wc": "Laatste woorden", "result_duration": "Duur", "result_download": "MP3 downloaden",
        "err_url": "Voer een URL in", "err_content": "Plak je bloginhoud", "err_slug": "Voer een bestandsnaam in",
        "placeholder_url": "https://voorbeeld.nl/blog/mijn-artikel", "placeholder_content": "Plak je bloginhoud hier...", "placeholder_slug": "mijn-blog-artikel",
        "voices": {"nl-NL-ColetteNeural": "Colette", "nl-NL-FennaNeural": "Fenna", "nl-NL-MaartenNeural": "Maarten"},
        "default_voice": "nl-NL-ColetteNeural",
    },
    "ru": {
        "name": "Русский", "flag": "🇷🇺",
        "title": "Блог в Аудио",
        "subtitle": "Преобразуйте статьи блога в естественно звучащие MP3-файлы",
        "tab_url": "Из URL", "tab_paste": "Вставить текст",
        "label_lang": "Язык", "label_voice": "Голос", "label_url": "URL статьи", "label_content": "Содержание блога", "label_slug": "Имя файла",
        "btn_convert": "Конвертировать в аудио", "btn_converting": "Конвертация...",
        "result_title": "Конвертация завершена", "result_source": "Источник", "result_wc": "Слова", "result_condensed": "Сокращено", "result_condensed_wc": "Итого слов", "result_duration": "Длительность", "result_download": "Скачать MP3",
        "err_url": "Введите URL", "err_content": "Вставьте содержание блога", "err_slug": "Введите имя файла",
        "placeholder_url": "https://пример.ru/блог/моя-статья", "placeholder_content": "Вставьте содержание блога здесь...", "placeholder_slug": "moya-statya",
        "voices": {"ru-RU-SvetlanaNeural": "Светлана", "ru-RU-DmitryNeural": "Дмитрий"},
        "default_voice": "ru-RU-SvetlanaNeural",
    },
    "ja": {
        "name": "日本語", "flag": "🇯🇵",
        "title": "ブログを音声に",
        "subtitle": "ブログ記事を自然な音声のMP3ファイルに変換します",
        "tab_url": "URLから", "tab_paste": "テキスト貼付",
        "label_lang": "言語", "label_voice": "音声", "label_url": "記事のURL", "label_content": "ブログの内容", "label_slug": "ファイル名",
        "btn_convert": "音声に変換", "btn_converting": "変換中...",
        "result_title": "変換完了", "result_source": "ソース", "result_wc": "単語数", "result_condensed": "要約", "result_condensed_wc": "最終単語数", "result_duration": "再生時間", "result_download": "MP3をダウンロード",
        "err_url": "URLを入力してください", "err_content": "ブログの内容を貼り付けてください", "err_slug": "ファイル名を入力してください",
        "placeholder_url": "https://example.jp/blog/my-post", "placeholder_content": "ブログの内容をここに貼り付けてください...", "placeholder_slug": "my-blog-post",
        "voices": {"ja-JP-NanamiNeural": "七海", "ja-JP-KeitaNeural": "圭太"},
        "default_voice": "ja-JP-NanamiNeural",
    },
    "ko": {
        "name": "한국어", "flag": "🇰🇷",
        "title": "블로그를 오디오로",
        "subtitle": "블로그 게시물을 자연스러운 MP3 오디오 파일로 변환하세요",
        "tab_url": "URL에서", "tab_paste": "텍스트 붙여넣기",
        "label_lang": "언어", "label_voice": "음성", "label_url": "게시물 URL", "label_content": "블로그 내용", "label_slug": "파일명",
        "btn_convert": "오디오로 변환", "btn_converting": "변환 중...",
        "result_title": "변환 완료", "result_source": "소스", "result_wc": "단어 수", "result_condensed": "축약", "result_condensed_wc": "최종 단어 수", "result_duration": "재생 시간", "result_download": "MP3 다운로드",
        "err_url": "URL을 입력하세요", "err_content": "블로그 내용을 붙여넣으세요", "err_slug": "파일명을 입력하세요",
        "placeholder_url": "https://example.kr/blog/my-post", "placeholder_content": "블로그 내용을 여기에 붙여넣으세요...", "placeholder_slug": "my-blog-post",
        "voices": {"ko-KR-SunHiNeural": "선희", "ko-KR-InJoonNeural": "인준", "ko-KR-HyunsuMultilingualNeural": "현수"},
        "default_voice": "ko-KR-SunHiNeural",
    },
    "zh": {
        "name": "中文", "flag": "🇨🇳",
        "title": "博客转音频",
        "subtitle": "将博客文章转换为自然发音的MP3音频文件",
        "tab_url": "从URL", "tab_paste": "粘贴文本",
        "label_lang": "语言", "label_voice": "语音", "label_url": "文章链接", "label_content": "博客内容", "label_slug": "文件名",
        "btn_convert": "转换为音频", "btn_converting": "转换中...",
        "result_title": "转换完成", "result_source": "来源", "result_wc": "字数", "result_condensed": "已精简", "result_condensed_wc": "最终字数", "result_duration": "时长", "result_download": "下载MP3",
        "err_url": "请输入URL", "err_content": "请粘贴博客内容", "err_slug": "请输入文件名",
        "placeholder_url": "https://example.cn/blog/my-post", "placeholder_content": "在此粘贴博客内容...", "placeholder_slug": "my-blog-post",
        "voices": {"zh-CN-XiaoxiaoNeural": "晓晓", "zh-CN-YunxiNeural": "云希", "zh-CN-XiaoyiNeural": "晓伊", "zh-CN-YunjianNeural": "云健"},
        "default_voice": "zh-CN-XiaoxiaoNeural",
    },
    "ar": {
        "name": "العربية", "flag": "🇸🇦",
        "title": "مدونة إلى صوت",
        "subtitle": "حوّل مقالات المدونة إلى ملفات صوتية MP3 بصوت طبيعي",
        "tab_url": "من رابط", "tab_paste": "لصق نص",
        "label_lang": "اللغة", "label_voice": "الصوت", "label_url": "رابط المقال", "label_content": "محتوى المدونة", "label_slug": "اسم الملف",
        "btn_convert": "تحويل إلى صوت", "btn_converting": "جارٍ التحويل...",
        "result_title": "اكتمل التحويل", "result_source": "المصدر", "result_wc": "عدد الكلمات", "result_condensed": "مختصر", "result_condensed_wc": "الكلمات النهائية", "result_duration": "المدة", "result_download": "تحميل MP3",
        "err_url": "أدخل رابطاً", "err_content": "الصق محتوى المدونة", "err_slug": "أدخل اسم الملف",
        "placeholder_url": "https://example.com/blog/my-post", "placeholder_content": "الصق محتوى المدونة هنا...", "placeholder_slug": "my-blog-post",
        "voices": {"ar-SA-ZariyahNeural": "زارية", "ar-SA-HamedNeural": "حامد", "ar-EG-SalmaNeural": "سلمى (مصر)"},
        "default_voice": "ar-SA-ZariyahNeural",
    },
    "hi": {
        "name": "हिन्दी", "flag": "🇮🇳",
        "title": "ब्लॉग से ऑडियो",
        "subtitle": "ब्लॉग पोस्ट को प्राकृतिक ध्वनि वाली MP3 ऑडियो फ़ाइलों में बदलें",
        "tab_url": "URL से", "tab_paste": "टेक्स्ट पेस्ट करें",
        "label_lang": "भाषा", "label_voice": "आवाज़", "label_url": "लेख का URL", "label_content": "ब्लॉग सामग्री", "label_slug": "फ़ाइल नाम",
        "btn_convert": "ऑडियो में बदलें", "btn_converting": "बदल रहा है...",
        "result_title": "रूपांतरण पूर्ण", "result_source": "स्रोत", "result_wc": "शब्द संख्या", "result_condensed": "संक्षिप्त", "result_condensed_wc": "अंतिम शब्द", "result_duration": "अवधि", "result_download": "MP3 डाउनलोड करें",
        "err_url": "URL दर्ज करें", "err_content": "ब्लॉग सामग्री पेस्ट करें", "err_slug": "फ़ाइल नाम दर्ज करें",
        "placeholder_url": "https://example.in/blog/mera-lekh", "placeholder_content": "अपनी ब्लॉग सामग्री यहाँ पेस्ट करें...", "placeholder_slug": "mera-blog-lekh",
        "voices": {"hi-IN-SwaraNeural": "स्वरा", "hi-IN-MadhurNeural": "मधुर"},
        "default_voice": "hi-IN-SwaraNeural",
    },
    "tr": {
        "name": "Türkçe", "flag": "🇹🇷",
        "title": "Blogdan Sese",
        "subtitle": "Blog yazılarını doğal sesli MP3 dosyalarına dönüştürün",
        "tab_url": "URL'den", "tab_paste": "Metin yapıştır",
        "label_lang": "Dil", "label_voice": "Ses", "label_url": "Makale URL'si", "label_content": "Blog içeriği", "label_slug": "Dosya adı",
        "btn_convert": "Sese dönüştür", "btn_converting": "Dönüştürülüyor...",
        "result_title": "Dönüştürme tamamlandı", "result_source": "Kaynak", "result_wc": "Kelime sayısı", "result_condensed": "Kısaltıldı", "result_condensed_wc": "Son kelime", "result_duration": "Süre", "result_download": "MP3 indir",
        "err_url": "Bir URL girin", "err_content": "Blog içeriğini yapıştırın", "err_slug": "Dosya adı girin",
        "placeholder_url": "https://ornek.com/blog/makale", "placeholder_content": "Blog içeriğini buraya yapıştırın...", "placeholder_slug": "blog-makalem",
        "voices": {"tr-TR-EmelNeural": "Emel", "tr-TR-AhmetNeural": "Ahmet"},
        "default_voice": "tr-TR-EmelNeural",
    },
    "pl": {
        "name": "Polski", "flag": "🇵🇱",
        "title": "Blog na Audio",
        "subtitle": "Konwertuj wpisy blogowe na naturalnie brzmiące pliki MP3",
        "tab_url": "Z URL", "tab_paste": "Wklej tekst",
        "label_lang": "Język", "label_voice": "Głos", "label_url": "URL artykułu", "label_content": "Treść bloga", "label_slug": "Nazwa pliku",
        "btn_convert": "Konwertuj na audio", "btn_converting": "Konwertowanie...",
        "result_title": "Konwersja zakończona", "result_source": "Źródło", "result_wc": "Słowa", "result_condensed": "Skrócono", "result_condensed_wc": "Końcowe słowa", "result_duration": "Czas", "result_download": "Pobierz MP3",
        "err_url": "Wprowadź URL", "err_content": "Wklej treść bloga", "err_slug": "Wprowadź nazwę pliku",
        "placeholder_url": "https://przyklad.pl/blog/moj-artykul", "placeholder_content": "Wklej treść bloga tutaj...", "placeholder_slug": "moj-artykul-blog",
        "voices": {"pl-PL-ZofiaNeural": "Zofia", "pl-PL-MarekNeural": "Marek"},
        "default_voice": "pl-PL-ZofiaNeural",
    },
    "sv": {
        "name": "Svenska", "flag": "🇸🇪",
        "title": "Blogg till Ljud",
        "subtitle": "Konvertera blogginlägg till naturligt ljudande MP3-filer",
        "tab_url": "Från URL", "tab_paste": "Klistra in text",
        "label_lang": "Språk", "label_voice": "Röst", "label_url": "Artikel-URL", "label_content": "Blogginnehåll", "label_slug": "Filnamn",
        "btn_convert": "Konvertera till ljud", "btn_converting": "Konverterar...",
        "result_title": "Konvertering klar", "result_source": "Källa", "result_wc": "Ord", "result_condensed": "Förkortad", "result_condensed_wc": "Slutliga ord", "result_duration": "Längd", "result_download": "Ladda ner MP3",
        "err_url": "Ange en URL", "err_content": "Klistra in blogginnehåll", "err_slug": "Ange ett filnamn",
        "placeholder_url": "https://exempel.se/blogg/min-artikel", "placeholder_content": "Klistra in blogginnehållet här...", "placeholder_slug": "min-blogg-artikel",
        "voices": {"sv-SE-SofieNeural": "Sofie", "sv-SE-MattiasNeural": "Mattias"},
        "default_voice": "sv-SE-SofieNeural",
    },
    "id": {
        "name": "Bahasa Indonesia", "flag": "🇮🇩",
        "title": "Blog ke Audio",
        "subtitle": "Ubah postingan blog menjadi file audio MP3 dengan suara alami",
        "tab_url": "Dari URL", "tab_paste": "Tempel teks",
        "label_lang": "Bahasa", "label_voice": "Suara", "label_url": "URL artikel", "label_content": "Konten blog", "label_slug": "Nama file",
        "btn_convert": "Ubah ke audio", "btn_converting": "Mengubah...",
        "result_title": "Konversi selesai", "result_source": "Sumber", "result_wc": "Jumlah kata", "result_condensed": "Diringkas", "result_condensed_wc": "Kata akhir", "result_duration": "Durasi", "result_download": "Unduh MP3",
        "err_url": "Masukkan URL", "err_content": "Tempel konten blog", "err_slug": "Masukkan nama file",
        "placeholder_url": "https://contoh.id/blog/artikel-saya", "placeholder_content": "Tempel konten blog di sini...", "placeholder_slug": "artikel-blog-saya",
        "voices": {"id-ID-GadisNeural": "Gadis", "id-ID-ArdiNeural": "Ardi"},
        "default_voice": "id-ID-GadisNeural",
    },
    "vi": {
        "name": "Tiếng Việt", "flag": "🇻🇳",
        "title": "Blog thành Âm thanh",
        "subtitle": "Chuyển đổi bài viết blog thành tệp âm thanh MP3 tự nhiên",
        "tab_url": "Từ URL", "tab_paste": "Dán văn bản",
        "label_lang": "Ngôn ngữ", "label_voice": "Giọng nói", "label_url": "URL bài viết", "label_content": "Nội dung blog", "label_slug": "Tên tệp",
        "btn_convert": "Chuyển thành âm thanh", "btn_converting": "Đang chuyển đổi...",
        "result_title": "Chuyển đổi hoàn tất", "result_source": "Nguồn", "result_wc": "Số từ", "result_condensed": "Đã rút gọn", "result_condensed_wc": "Số từ cuối", "result_duration": "Thời lượng", "result_download": "Tải MP3",
        "err_url": "Nhập URL", "err_content": "Dán nội dung blog", "err_slug": "Nhập tên tệp",
        "placeholder_url": "https://example.vn/blog/bai-viet", "placeholder_content": "Dán nội dung blog vào đây...", "placeholder_slug": "bai-viet-cua-toi",
        "voices": {"vi-VN-HoaiMyNeural": "Hoài My", "vi-VN-NamMinhNeural": "Nam Minh"},
        "default_voice": "vi-VN-HoaiMyNeural",
    },
    "th": {
        "name": "ไทย", "flag": "🇹🇭",
        "title": "บล็อกเป็นเสียง",
        "subtitle": "แปลงบทความบล็อกเป็นไฟล์เสียง MP3 ที่ฟังเป็นธรรมชาติ",
        "tab_url": "จาก URL", "tab_paste": "วางข้อความ",
        "label_lang": "ภาษา", "label_voice": "เสียง", "label_url": "URL บทความ", "label_content": "เนื้อหาบล็อก", "label_slug": "ชื่อไฟล์",
        "btn_convert": "แปลงเป็นเสียง", "btn_converting": "กำลังแปลง...",
        "result_title": "การแปลงเสร็จสมบูรณ์", "result_source": "แหล่งที่มา", "result_wc": "จำนวนคำ", "result_condensed": "ย่อแล้ว", "result_condensed_wc": "จำนวนคำสุดท้าย", "result_duration": "ระยะเวลา", "result_download": "ดาวน์โหลด MP3",
        "err_url": "กรุณาใส่ URL", "err_content": "กรุณาวางเนื้อหาบล็อก", "err_slug": "กรุณาใส่ชื่อไฟล์",
        "placeholder_url": "https://example.th/blog/my-post", "placeholder_content": "วางเนื้อหาบล็อกที่นี่...", "placeholder_slug": "my-blog-post",
        "voices": {"th-TH-PremwadeeNeural": "เปรมวดี", "th-TH-NiwatNeural": "นิวัฒน์"},
        "default_voice": "th-TH-PremwadeeNeural",
    },
}

ALL_VOICES = {}
for lang_data in LANGUAGES.values():
    ALL_VOICES.update(lang_data["voices"])

app = Flask(__name__)

SYMBOL_MAP = {"&": " and ", "%": " percent ", "→": " to "}
ABBREVIATION_MAP = {"e.g.": "for example", "i.e.": "that is", "etc.": "and so on", "vs.": "versus", "approx.": "approximately"}


def fetch_article(url):
    resp = http_requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup.find_all(["nav", "header", "footer", "aside", "form", "script", "style", "noscript"]):
        tag.decompose()
    for sel in [".author-bio",".author-info",".byline",".related-posts",".related-articles",".cta",".call-to-action",".social-share",".share-buttons",".comments","#comments",".comment-section",".cookie-banner",".cookie-notice",".breadcrumb",".breadcrumbs",".sidebar"]:
        for el in soup.select(sel):
            el.decompose()
    article = soup.find("article") or soup.find("div", class_=re.compile(r"(article|post|entry|content)-?(body|content|text)", re.I)) or soup.find("div", {"role": "main"}) or soup.find("main")
    if article:
        return article.get_text(separator="\n")
    return soup.body.get_text(separator="\n") if soup.body else soup.get_text(separator="\n")


def clean_text(raw):
    text = BeautifulSoup(raw, "html.parser").get_text(separator="\n")
    faq_match = re.search(r"(?:FAQ|FAQs|Frequently\s+Asked\s+Questions)", text, re.IGNORECASE)
    if faq_match:
        text = text[:faq_match.start()].rstrip()
    text = re.sub(r"[*_`#]", "", text)
    text = re.sub(r"---+", "", text)
    for sym, word in SYMBOL_MAP.items():
        text = text.replace(sym, word)
    for abbr, exp in ABBREVIATION_MAP.items():
        text = text.replace(abbr, exp)

    def replace_list(m):
        items = re.findall(r"(?:^|\n)\s*(?:[-•*]|\d+[.)]) *(.*)", m.group(0))
        if not items: return m.group(0)
        ords = ["First","Second","Third","Fourth","Fifth","Sixth","Seventh","Eighth","Ninth","Tenth"]
        parts = []
        for i, item in enumerate(items):
            p = ords[i] if i < len(ords) else "Next"
            if i == len(items) - 1 and len(items) > 1: p = "Finally"
            parts.append(f"{p}, {item.strip()}.")
        return " ".join(parts)

    text = re.sub(r"((?:^|\n)\s*(?:[-•*]|\d+[.)]) +.+(?:\n\s*(?:[-•*]|\d+[.)]) +.+)*)", replace_list, text)
    lines = text.split("\n")
    processed = []
    for line in lines:
        s = line.strip()
        if not s: processed.append(""); continue
        words = s.split()
        if len(words) <= 12 and s == s.rstrip(".!?") and not any(c in s for c in ".,;:") and s[0].isupper() and processed and processed[-1] == "":
            s = f"Now, let's talk about {s}."
        processed.append(s)
    text = "\n".join(processed)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"  +", " ", text)
    return text.strip()


def word_count(text):
    return len(text.split())


def _get_gemini_key():
    key = os.getenv("GEMINI_API_KEY", "")
    key = key.strip().lstrip("﻿").strip()
    if not key:
        raise ValueError("GEMINI_API_KEY not set")
    return key


def _strip_gemini_artifacts(text):
    text = text.replace("﻿", "").replace("￾", "")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def translate_with_gemini(text, lang_code):
    api_key = _get_gemini_key()
    lang_name = LANGUAGES.get(lang_code, {}).get("name", "English")
    client = _load_genai().Client(api_key=api_key)
    prompt = (
        f"Translate the following text into {lang_name}.\n\n"
        "Rules:\n"
        "- Produce a natural, fluent translation — not a word-for-word literal one\n"
        "- Preserve the meaning, tone, and structure of the original\n"
        "- Keep proper nouns, brand names, and technical terms as-is when appropriate\n"
        "- Return only the translated text, no commentary or explanation\n"
        "- Do NOT include any BOM characters or special markers\n\n"
        f"Text:\n{text}"
    )
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return _strip_gemini_artifacts(response.text)


def condense_with_gemini(text, lang_code="en"):
    api_key = _get_gemini_key()
    lang_name = LANGUAGES.get(lang_code, {}).get("name", "English")
    client = _load_genai().Client(api_key=api_key)
    prompt = (
        f"Condense the following article to approximately {CONDENSED_TARGET_WORDS} words.\n"
        f"The article is in {lang_name}. Keep the output in {lang_name}.\n\n"
        "Rules:\n"
        "- Preserve every key point, all details, data points, statistics, steps, and important information\n"
        "- Remove only filler phrases, redundant sentences, decorative transitions, and repetitive content\n"
        "- Do not remove any section entirely unless it contains zero informational value\n"
        "- Maintain the logical flow and structure of the original article\n"
        "- Return only the condensed article text, no commentary or explanation\n\n"
        f"Article:\n{text}"
    )
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return _strip_gemini_artifacts(response.text)


def sanitize_slug(slug):
    slug = slug.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def slug_from_url(url):
    path = url.rstrip("/").split("/")[-1]
    path = path.split("?")[0].split("#")[0]
    return sanitize_slug(path)


def estimate_duration(wc):
    seconds = int(wc / 150 * 60)
    return f"{seconds // 60}m {seconds % 60}s"


def build_html():
    lang_json = json.dumps(LANGUAGES, ensure_ascii=False)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Text to Audio Online - Free Blog to MP3 Converter | 19 Languages, 60+ AI Voices</title>
    <meta name="description" content="Convert any blog post or text into natural-sounding MP3 audio for free. Paste a URL or text, pick from 60+ AI voices in 19 languages, and download your audio instantly. No signup required.">
    <meta name="keywords" content="text to audio, blog to audio, text to speech, TTS, MP3 converter, AI voice, free text to speech, blog post to podcast, multilingual TTS, convert blog to audio">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://text-to-audio-online.vercel.app/">
    <meta property="og:title" content="Text to Audio Online - Free Blog to MP3 Converter">
    <meta property="og:description" content="Convert any blog post or text into natural-sounding MP3 audio for free. 60+ AI voices, 19 languages. No signup required.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://text-to-audio-online.vercel.app/">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="Text to Audio Online - Free Blog to MP3 Converter">
    <meta name="twitter:description" content="Convert any blog post or text into natural-sounding MP3 audio for free. 60+ AI voices, 19 languages.">
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
        {{"@type": "Question", "name": "Can I convert a private or paywalled blog post to audio?", "acceptedAnswer": {{"@type": "Answer", "text": "Nope, it won't work for private and paywalled blogs."}}}},
        {{"@type": "Question", "name": "Will the audio sound like a natural conversation or a robot reading my post?", "acceptedAnswer": {{"@type": "Answer", "text": "Based on the response from people so far, they have liked the audio. Of course you should always use your due diligence since there are so many voices you can test. Pick the one which works the best for you."}}}},
        {{"@type": "Question", "name": "How long will the audio file be from a typical blog post?", "acceptedAnswer": {{"@type": "Answer", "text": "It depends. The longer the blog post, the longer the audio file will be."}}}},
        {{"@type": "Question", "name": "Can I convert multiple blog posts at once or just one at a time?", "acceptedAnswer": {{"@type": "Answer", "text": "No, this feature is not available yet, but we are in the process of adding this. It will be live sooner or later."}}}},
        {{"@type": "Question", "name": "Do I need to copy-paste my content or can I just paste the URL?", "acceptedAnswer": {{"@type": "Answer", "text": "You have both the options. You can paste your blog URL. If you feel the blog URL is not giving you the desired output, you have the option to paste the content itself. This will take 1-2 minutes extra, but the results will be better."}}}},
        {{"@type": "Question", "name": "What audio file formats can I download (MP3, WAV, M4A)?", "acceptedAnswer": {{"@type": "Answer", "text": "You can download the audio files in only MP3 format."}}}},
        {{"@type": "Question", "name": "How many AI voices and languages are available?", "acceptedAnswer": {{"@type": "Answer", "text": "There are multiple languages covered, and we are adding more voices to it."}}}},
        {{"@type": "Question", "name": "Can I customize the voice speed, pitch, and emotion?", "acceptedAnswer": {{"@type": "Answer", "text": "You can customise the voice speed only. The audio will by default have the pitch and emotion. Different voices will have different pitch and emotion."}}}},
        {{"@type": "Question", "name": "Is the audio quality good enough for podcasting?", "acceptedAnswer": {{"@type": "Answer", "text": "It is good enough based on the opinion of most people who have used it so far. But you should certainly use your due diligence. Give it a shot, you have many voices to experiment with, whichever you like the most, you can download it."}}}},
        {{"@type": "Question", "name": "Can I embed the audio player directly on my blog post?", "acceptedAnswer": {{"@type": "Answer", "text": "Not the audio player, but the audio file you can definitely post on your blog post."}}}},
        {{"@type": "Question", "name": "Can I download the audio file or just play it online?", "acceptedAnswer": {{"@type": "Answer", "text": "You can play the audio online and also download the MP3 file."}}}},
        {{"@type": "Question", "name": "Does converting blogs to audio help with SEO?", "acceptedAnswer": {{"@type": "Answer", "text": "Yeah, it does. One of the key factors for ranking well is having your content involve a multi-modal approach. This means don't stick to text-based content alone, incorporate images, videos, tools (if you can) and audio happens to be one of the ways to incorporate a multimodal approach. And let's not forget voice search is growing every week."}}}},
        {{"@type": "Question", "name": "Can I publish the audio to Spotify and Apple Podcasts automatically?", "acceptedAnswer": {{"@type": "Answer", "text": "Not automatically. This text-to-voice software will only convert your text content into an audio file. You can download it and then publish it on the desired platforms."}}}},
        {{"@type": "Question", "name": "Will offering audio versions improve accessibility for my readers?", "acceptedAnswer": {{"@type": "Answer", "text": "It does, because not everyone will be comfortable reading through a 1000 or 2000 word article. In such cases the audio file will come to your rescue. And if the visitor sticks around throughout the duration of the audio, it will signal to Google strong retention."}}}},
        {{"@type": "Question", "name": "Is there a free version or trial available?", "acceptedAnswer": {{"@type": "Answer", "text": "This is a free version you're looking at."}}}}
      ]
    }}
    </script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a; color: #e2e8f0;
            min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 0;
        }}
        .hero {{ display: flex; align-items: flex-start; justify-content: center; padding: 12vh 2rem 2rem; width: 100%; }}
        .container {{ width: 100%; max-width: 640px; }}
        h1 {{ font-size: 1.75rem; font-weight: 700; margin-bottom: 0.25rem; }}
        .subtitle {{ color: #94a3b8; margin-bottom: 2rem; font-size: 0.95rem; }}
        .tabs {{ display: flex; margin-bottom: 1.5rem; border-bottom: 2px solid #1e293b; }}
        .tab {{
            padding: 0.75rem 1.5rem; cursor: pointer; color: #94a3b8; font-weight: 500;
            border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.2s;
            background: none; border-top: none; border-left: none; border-right: none; font-size: 0.95rem;
        }}
        .tab:hover {{ color: #e2e8f0; }}
        .tab.active {{ color: #818cf8; border-bottom-color: #818cf8; }}
        .panel {{ display: none; }}
        .panel.active {{ display: block; }}
        label {{ display: block; font-size: 0.85rem; font-weight: 500; color: #94a3b8; margin-bottom: 0.4rem; }}
        input[type="text"], textarea {{
            width: 100%; padding: 0.75rem 1rem; background: #1e293b; border: 1px solid #334155;
            border-radius: 8px; color: #e2e8f0; font-size: 0.95rem; font-family: inherit;
            outline: none; transition: border-color 0.2s;
        }}
        input[type="text"]:focus, textarea:focus {{ border-color: #818cf8; }}
        textarea {{ min-height: 200px; resize: vertical; }}
        .field {{ margin-bottom: 1rem; }}
        .row {{ display: flex; gap: 1rem; }}
        .row .field {{ flex: 1; }}
        .btn {{
            width: 100%; padding: 0.85rem; background: #818cf8; color: #fff; border: none;
            border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer;
            transition: background 0.2s; margin-top: 0.5rem;
        }}
        .btn:hover {{ background: #6366f1; }}
        .btn:disabled {{ background: #475569; cursor: not-allowed; }}
        select {{
            width: 100%; padding: 0.75rem 1rem; background: #1e293b; border: 1px solid #334155;
            border-radius: 8px; color: #e2e8f0; font-size: 0.95rem; font-family: inherit;
            outline: none; transition: border-color 0.2s; appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%2394a3b8' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10z'/%3E%3C/svg%3E");
            background-repeat: no-repeat; background-position: right 1rem center;
        }}
        select:focus {{ border-color: #818cf8; }}
        .result {{
            margin-top: 1.5rem; padding: 1.25rem; background: #1e293b; border-radius: 8px; display: none;
        }}
        .result.show {{ display: block; }}
        .result h3 {{ font-size: 1rem; margin-bottom: 0.75rem; color: #818cf8; }}
        .result-row {{ display: flex; justify-content: space-between; padding: 0.35rem 0; font-size: 0.9rem; }}
        .result-row span:first-child {{ color: #94a3b8; }}
        .result audio {{ width: 100%; margin-top: 1rem; }}
        .download-link {{
            display: inline-block; margin-top: 0.75rem; color: #818cf8;
            text-decoration: none; font-weight: 500; font-size: 0.9rem;
        }}
        .download-link:hover {{ text-decoration: underline; }}
        .error-msg {{
            margin-top: 1rem; padding: 0.75rem 1rem; background: #7f1d1d;
            border-radius: 8px; font-size: 0.9rem; display: none;
        }}
        .error-msg.show {{ display: block; }}
        .faq {{ margin-top: 110px; padding-bottom: 2rem; }}
        .faq h2 {{ font-size: 1.25rem; font-weight: 700; margin-bottom: 1.25rem; color: #818cf8; }}
        .faq-item {{ margin-bottom: 0.5rem; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; }}
        .faq-q {{
            width: 100%; padding: 0.85rem 1rem; background: #1e293b; border: none; color: #e2e8f0;
            font-size: 0.9rem; font-weight: 500; text-align: left; cursor: pointer;
            display: flex; justify-content: space-between; align-items: center; font-family: inherit;
        }}
        .faq-q:hover {{ background: #253046; }}
        .faq-q::after {{ content: '+'; font-size: 1.1rem; color: #818cf8; transition: transform 0.2s; flex-shrink: 0; margin-left: 0.75rem; }}
        .faq-item.open .faq-q::after {{ content: '\\2212'; }}
        .faq-a {{
            max-height: 0; overflow: hidden; transition: max-height 0.3s ease, padding 0.3s ease;
            background: #162032; font-size: 0.85rem; color: #94a3b8; line-height: 1.6; padding: 0 1rem;
        }}
        .faq-item.open .faq-a {{ max-height: 300px; padding: 0.75rem 1rem; }}
        .spinner {{
            display: inline-block; width: 18px; height: 18px; border: 2px solid #fff;
            border-top-color: transparent; border-radius: 50%;
            animation: spin 0.7s linear infinite; vertical-align: middle; margin-right: 0.5rem;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        @media (max-width: 600px) {{
            .hero {{ padding: 6vh 1rem 1.5rem; }}
            .container {{ max-width: 100%; }}
            h1 {{ font-size: 1.4rem; }}
            .subtitle {{ font-size: 0.85rem; margin-bottom: 1.5rem; }}
            .row {{ flex-direction: column; gap: 0; }}
            .tab {{ padding: 0.65rem 1rem; font-size: 0.85rem; }}
            input[type="text"], textarea, select {{ font-size: 16px; padding: 0.7rem 0.85rem; }}
            .btn {{ padding: 0.9rem; font-size: 0.95rem; }}
            .faq {{ margin-top: 70px; }}
            .faq h2 {{ font-size: 1.1rem; }}
            .faq-q {{ font-size: 0.82rem; padding: 0.75rem 0.85rem; }}
            .faq-a {{ font-size: 0.8rem; }}
            .result-row {{ font-size: 0.82rem; }}
            .result {{ padding: 1rem; }}
        }}
    </style>
</head>
<body>
    <div class="hero"><div class="container">
        <h1 id="t-title">Text to Audio</h1>
        <p class="subtitle" id="t-subtitle">Convert text and blog posts into natural-sounding MP3 audio files</p>
        <div class="tabs">
            <button class="tab active" data-tab="url" id="t-tab-url">From URL</button>
            <button class="tab" data-tab="manual" id="t-tab-paste">Paste Text</button>
        </div>
        <div class="row">
            <div class="field">
                <label id="t-label-lang">Language</label>
                <select id="lang-select"></select>
            </div>
            <div class="field">
                <label id="t-label-voice">Voice</label>
                <select id="voice-select"></select>
            </div>
        </div>
        <div id="panel-url" class="panel active">
            <div class="field">
                <label id="t-label-url">Content URL</label>
                <input type="text" id="url-input">
            </div>
            <button class="btn" id="btn-url">Convert to Audio</button>
        </div>
        <div id="panel-manual" class="panel">
            <div class="field">
                <label id="t-label-content">Blog content</label>
                <textarea id="text-input"></textarea>
            </div>
            <div class="field">
                <label id="t-label-slug">Filename slug</label>
                <input type="text" id="slug-input">
            </div>
            <button class="btn" id="btn-manual">Convert to Audio</button>
        </div>
        <div class="error-msg" id="error"></div>
        <div class="result" id="result">
            <h3 id="t-result-title">Conversion Complete</h3>
            <div class="result-row"><span id="t-result-source">Source</span><span id="r-source"></span></div>
            <div class="result-row"><span id="t-result-wc">Word count</span><span id="r-wc"></span></div>
            <div class="result-row"><span id="t-result-condensed">Condensed</span><span id="r-condensed"></span></div>
            <div class="result-row" id="r-condensed-wc-row" style="display:none"><span id="t-result-condensed-wc">Final word count</span><span id="r-condensed-wc"></span></div>
            <div class="result-row"><span id="t-result-duration">Duration</span><span id="r-duration"></span></div>
            <audio id="r-audio" controls></audio>
            <a class="download-link" id="r-download" href="#" download id-text="t-result-download">Download MP3</a>
        </div>
        <div class="faq">
        <div class="faq">
            <h2>Frequently Asked Questions</h2>
            <div class="faq-item"><button class="faq-q">Can I convert a private or paywalled blog post to audio?</button><div class="faq-a">Nope, it won't work for private and paywalled blogs.</div></div>
            <div class="faq-item"><button class="faq-q">Will the audio sound like a natural conversation or a robot reading my post?</button><div class="faq-a">Based on the response from people so far, they have liked the audio. Of course you should always use your due diligence since there are so many voices you can test. Pick the one which works the best for you.</div></div>
            <div class="faq-item"><button class="faq-q">How long will the audio file be from a typical blog post?</button><div class="faq-a">It depends. The longer the blog post, the longer the audio file will be.</div></div>
            <div class="faq-item"><button class="faq-q">Can I convert multiple blog posts at once or just one at a time?</button><div class="faq-a">No, this feature is not available yet, but we are in the process of adding this. It will be live sooner or later.</div></div>
            <div class="faq-item"><button class="faq-q">Do I need to copy-paste my content or can I just paste the URL?</button><div class="faq-a">You have both the options. You can paste your blog URL. If you feel the blog URL is not giving you the desired output, you have the option to paste the content itself. This will take 1-2 minutes extra, but the results will be better.</div></div>
            <div class="faq-item"><button class="faq-q">What audio file formats can I download (MP3, WAV, M4A)?</button><div class="faq-a">You can download the audio files in only MP3 format.</div></div>
            <div class="faq-item"><button class="faq-q">How many AI voices and languages are available?</button><div class="faq-a">There are multiple languages covered, and we are adding more voices to it.</div></div>
            <div class="faq-item"><button class="faq-q">Can I customize the voice speed, pitch, and emotion?</button><div class="faq-a">You can customise the voice speed only. The audio will by default have the pitch and emotion. Different voices will have different pitch and emotion.</div></div>
            <div class="faq-item"><button class="faq-q">Is the audio quality good enough for podcasting?</button><div class="faq-a">It is good enough based on the opinion of most people who have used it so far. But you should certainly use your due diligence. Give it a shot, you have many voices to experiment with, whichever you like the most, you can download it.</div></div>
            <div class="faq-item"><button class="faq-q">Can I embed the audio player directly on my blog post?</button><div class="faq-a">Not the audio player, but the audio file you can definitely post on your blog post.</div></div>
            <div class="faq-item"><button class="faq-q">Can I download the audio file or just play it online?</button><div class="faq-a">You can play the audio online and also download the MP3 file.</div></div>
            <div class="faq-item"><button class="faq-q">Does converting blogs to audio help with SEO?</button><div class="faq-a">Yeah, it does. One of the key factors for ranking well is having your content involve a multi-modal approach. This means don't stick to text-based content alone, incorporate images, videos, tools (if you can) and audio happens to be one of the ways to incorporate a multimodal approach. And let's not forget voice search is growing every week.</div></div>
            <div class="faq-item"><button class="faq-q">Can I publish the audio to Spotify and Apple Podcasts automatically?</button><div class="faq-a">Not automatically. This text-to-voice software will only convert your text content into an audio file. You can download it and then publish it on the desired platforms.</div></div>
            <div class="faq-item"><button class="faq-q">Will offering audio versions improve accessibility for my readers?</button><div class="faq-a">It does, because not everyone will be comfortable reading through a 1000 or 2000 word article. In such cases the audio file will come to your rescue. And if the visitor sticks around throughout the duration of the audio, it will signal to Google strong retention.</div></div>
            <div class="faq-item"><button class="faq-q">Is there a free version or trial available?</button><div class="faq-a">This is a free version you're looking at.</div></div>
        </div>
    </div></div>
    <script>
    const LANGS = {lang_json};
    let currentLang = 'en';

    // Build language selector
    const langSel = document.getElementById('lang-select');
    for (const [code, data] of Object.entries(LANGS)) {{
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = data.flag + ' ' + data.name;
        if (code === 'en') opt.selected = true;
        langSel.appendChild(opt);
    }}

    function setLang(code) {{
        currentLang = code;
        const L = LANGS[code];
        document.documentElement.lang = code;
        document.title = (code === 'en') ? 'Text to Audio Online - Free Blog to MP3 Converter | 19 Languages, 60+ AI Voices' : L.title;
        document.getElementById('t-title').textContent = L.title;
        document.getElementById('t-subtitle').textContent = L.subtitle;
        document.getElementById('t-tab-url').textContent = L.tab_url;
        document.getElementById('t-tab-paste').textContent = L.tab_paste;
        document.getElementById('t-label-lang').textContent = L.label_lang;
        document.getElementById('t-label-voice').textContent = L.label_voice;
        document.getElementById('t-label-url').textContent = L.label_url;
        document.getElementById('t-label-content').textContent = L.label_content;
        document.getElementById('t-label-slug').textContent = L.label_slug;
        document.getElementById('btn-url').textContent = L.btn_convert;
        document.getElementById('btn-manual').textContent = L.btn_convert;
        document.getElementById('t-result-title').textContent = L.result_title;
        document.getElementById('t-result-source').textContent = L.result_source;
        document.getElementById('t-result-wc').textContent = L.result_wc;
        document.getElementById('t-result-condensed').textContent = L.result_condensed;
        document.getElementById('t-result-condensed-wc').textContent = L.result_condensed_wc;
        document.getElementById('t-result-duration').textContent = L.result_duration;
        document.getElementById('r-download').textContent = L.result_download;
        document.getElementById('url-input').placeholder = L.placeholder_url;
        document.getElementById('text-input').placeholder = L.placeholder_content;
        document.getElementById('slug-input').placeholder = L.placeholder_slug;
        // Update voices
        const voiceSel = document.getElementById('voice-select');
        voiceSel.innerHTML = '';
        for (const [vid, vname] of Object.entries(L.voices)) {{
            const opt = document.createElement('option');
            opt.value = vid;
            opt.textContent = vname;
            if (vid === L.default_voice) opt.selected = true;
            voiceSel.appendChild(opt);
        }}
        // RTL for Arabic
        document.body.dir = code === 'ar' ? 'rtl' : 'ltr';
    }}

    langSel.addEventListener('change', () => setLang(langSel.value));
    setLang('en');

    // Tabs
    document.querySelectorAll('.tab').forEach(tab => {{
        tab.addEventListener('click', () => {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
            hideResults();
        }});
    }});

    function hideResults() {{
        document.getElementById('result').classList.remove('show');
        document.getElementById('error').classList.remove('show');
    }}
    function showError(msg) {{
        const el = document.getElementById('error');
        el.textContent = msg; el.classList.add('show');
        document.getElementById('result').classList.remove('show');
    }}
    function showResult(data) {{
        document.getElementById('error').classList.remove('show');
        document.getElementById('r-source').textContent = data.input_source;
        document.getElementById('r-wc').textContent = data.word_count_cleaned;
        document.getElementById('r-condensed').textContent = data.condensation_applied ? 'Yes' : 'No';
        const cwcRow = document.getElementById('r-condensed-wc-row');
        if (data.condensation_applied) {{
            cwcRow.style.display = 'flex';
            document.getElementById('r-condensed-wc').textContent = data.word_count_final;
        }} else {{ cwcRow.style.display = 'none'; }}
        document.getElementById('r-duration').textContent = data.estimated_duration;
        const audioBlob = base64ToBlob(data.audio_base64, 'audio/mpeg');
        const audioUrl = URL.createObjectURL(audioBlob);
        document.getElementById('r-audio').src = audioUrl;
        const dl = document.getElementById('r-download');
        dl.href = audioUrl; dl.download = data.filename;
        document.getElementById('result').classList.add('show');
    }}
    function base64ToBlob(b64, mime) {{
        const bytes = atob(b64);
        const arr = new Uint8Array(bytes.length);
        for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
        return new Blob([arr], {{ type: mime }});
    }}
    async function convert(body, btn) {{
        hideResults();
        const L = LANGS[currentLang];
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span>' + L.btn_converting;
        try {{
            const resp = await fetch('/convert', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(body),
            }});
            const data = await resp.json();
            if (!resp.ok) showError(data.error || 'Something went wrong');
            else showResult(data);
        }} catch (e) {{ showError('Network error: ' + e.message); }}
        finally {{ btn.disabled = false; btn.innerHTML = originalText; }}
    }}
    document.getElementById('btn-url').addEventListener('click', () => {{
        const L = LANGS[currentLang];
        const url = document.getElementById('url-input').value.trim();
        if (!url) return showError(L.err_url);
        const voice = document.getElementById('voice-select').value;
        convert({{ input_type: 'url', url, voice, lang: currentLang }}, document.getElementById('btn-url'));
    }});
    document.getElementById('btn-manual').addEventListener('click', () => {{
        const L = LANGS[currentLang];
        const text = document.getElementById('text-input').value.trim();
        const slug = document.getElementById('slug-input').value.trim();
        if (!text) return showError(L.err_content);
        if (!slug) return showError(L.err_slug);
        const voice = document.getElementById('voice-select').value;
        convert({{ input_type: 'manual', text, slug, voice, lang: currentLang }}, document.getElementById('btn-manual'));
    }});
    document.querySelectorAll('.faq-q').forEach(btn => {{
        btn.addEventListener('click', () => {{
            const item = btn.parentElement;
            const wasOpen = item.classList.contains('open');
            document.querySelectorAll('.faq-item.open').forEach(i => i.classList.remove('open'));
            if (!wasOpen) item.classList.add('open');
        }});
    }});
    </script>
</body>
</html>'''


@app.route("/")
def index():
    return Response(build_html(), content_type="text/html; charset=utf-8")


@app.route("/sitemap.xml")
def sitemap():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://text-to-audio-online.vercel.app/</loc>
    <lastmod>2026-06-17</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>'''
    return Response(xml, content_type="application/xml; charset=utf-8")


@app.route("/robots.txt")
def robots():
    txt = '''User-agent: *
Allow: /

Sitemap: https://text-to-audio-online.vercel.app/sitemap.xml
'''
    return Response(txt, content_type="text/plain; charset=utf-8")


@app.route("/convert", methods=["POST"])
def convert():
    data = request.get_json()
    input_type = data.get("input_type")
    url = data.get("url", "").strip()
    text = data.get("text", "").strip()
    slug = data.get("slug", "").strip()
    voice = data.get("voice", "en-US-JennyNeural")
    lang = data.get("lang", "en")

    if voice not in ALL_VOICES:
        voice = LANGUAGES.get(lang, LANGUAGES["en"])["default_voice"]

    try:
        if input_type == "url":
            if not url:
                return jsonify({"error": "URL is required"}), 400
            raw_text = fetch_article(url)
            file_slug = slug_from_url(url)
        elif input_type == "manual":
            if not text:
                return jsonify({"error": "Text content is required"}), 400
            if not slug:
                return jsonify({"error": "Filename slug is required"}), 400
            raw_text = text
            file_slug = sanitize_slug(slug)
            if not file_slug:
                return jsonify({"error": "Invalid slug"}), 400
        else:
            return jsonify({"error": "Invalid input type"}), 400

        cleaned = clean_text(raw_text)
        wc = word_count(cleaned)

        condensed = False
        final_text = cleaned
        if wc > WORD_COUNT_THRESHOLD:
            final_text = condense_with_gemini(cleaned, lang)
            condensed = True

        if lang != "en":
            final_text = translate_with_gemini(final_text, lang)

        final_wc = word_count(final_text)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        final_text = final_text.encode("utf-8", errors="ignore").decode("utf-8")

        _edge_tts = _load_edge_tts()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_edge_tts.Communicate(final_text, voice).save(tmp_path))
        finally:
            loop.close()

        with open(tmp_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        os.unlink(tmp_path)

        return jsonify({
            "success": True,
            "input_source": f"URL: {url}" if input_type == "url" else "Pasted text",
            "word_count_cleaned": wc,
            "condensation_applied": condensed,
            "translated": lang != "en",
            "word_count_final": final_wc if condensed else wc,
            "estimated_duration": estimate_duration(final_wc),
            "filename": f"{file_slug}.mp3",
            "audio_base64": audio_b64,
        })
    except Exception as e:
        print(f"CONVERT ERROR: {traceback.format_exc()}", file=sys.stderr, flush=True)
        return jsonify({"error": str(e)}), 500
