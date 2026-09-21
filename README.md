# EvrenLLMApi

Evren LLM Gateway (`https://evren-llmapi.ssyz.org.tr/v1`) için çalışan CLI + örnek kod.

Bütün yetenekler üç şekilde kullanılabilir:

| Nasıl | Örnek |
|---|---|
| Komut satırı | `python main.py ocr test_fatura.png` |
| Python kodu | `from main import ocr` → `ocr("test_fatura.png")` |
| Ham HTTP | `requests.post(...)` — bölüm 17 |

Her bölümde hem komut satırı hem Python kodu gösterilir; ham HTTP'nin karşılıkları
bölüm 17'dedir.

Tüm komutlar için: `python main.py --help`

> İlk kullanımda şartlar ekrana gelir ve `E/h` onayın istenir (otomatik kabul yoktur) — bölüm 2.

> Bu sağlayıcıyı başka bir araca OpenAI uyumlu olarak bağlamak için: [`OPENAI_UYUMLU.md`](OPENAI_UYUMLU.md)

---

## 1. Ne lazım

```bash
pip install requests python-dotenv
```

`.env` dosyası (proje kökünde) — örnek şablon: [`.env.example`](.env.example:1)

```bash
copy .env.example .env      # Windows  (Linux/macOS: cp .env.example .env)
```

```
BASE_URL=https://evren-llmapi.ssyz.org.tr/v1
API_URL=evren_llm_...
```

| Değişken | Anlamı |
|---|---|
| `API_URL` | API anahtarın (`evren_llm_...`) — **zorunlu** |
| `BASE_URL` | Gateway adresi — verilmezse `https://evren-llmapi.ssyz.org.tr/v1` |

`.env` dosyası gizli tutulur; anahtarın sürüm kontrolüne girmez.
Anahtar boşsa program net bir hata verip durur (sessiz 401 yerine).

### Denemek için dosyalar

Depoda örnekleri çalıştırmak üzere hazır dosyalar bulunur:

| Dosya | Ne için |
|---|---|
| `test_gorsel.png` | `vision` (tek satır yazı + şekiller) |
| `test_fatura.png` | `ocr` (dolu belge görseli) |
| `test_ses.wav` | `transcribe` (Türkçe konuşma) |
| `test_belgeler.txt` | `rerank --docs-file` (her satır bir belge) |
| `test_belgeler.json` | `rerank --docs-file` (JSON dizi) |

Kendi dosyanı da kullanabilirsin; dosya yoksa komutlar net "dosya yok" hatası verir.
Belge dosyasını hızlıca oluşturmak için:

```bash
echo Kediler evcil hayvandir.> test_belgeler.txt
echo Araba motorlu bir tasittir.>> test_belgeler.txt
```

## 2. İlk 3 dakika

```bash
chcp 65001 >nul && python main.py list_models   # modelleri gör
chcp 65001 >nul && python main.py repl          # sohbete başla (önerilen)
```

### Kullanım şartları (ilk kullanımda bir kez)

Şartlar **otomatik kabul edilmez**. İlk API çağrısında şart metni ekrana gelir ve sen karar verirsin:

```
======================================================================
EVREN LLM GATEWAY — KULLANIM ŞARTLARI (v1)
======================================================================
...şartların tam metni...
======================================================================
Kabul ediyor musunuz? (E/h):
```

| Cevap | Sonuç |
|---|---|
| `E` / `evet` / `yes` / `y` | Onaylanır, komut çalışır — bir daha sorulmaz |
| `h` / boş / başka bir şey | **Reddedilir**, komut çalışmaz (çıkış) |
| Etkileşim yok (stdin yok, script/CI) | **Reddedilmiş sayılır**, çıkar |

Bu davranış her kullanım yolunda aynıdır: CLI komutları, `from main import ...` çağrıları,
`repl` açılışı ve ham HTTP (bkz. bölüm 17). Soru bir kez cevaplanır, sunucuya kaydedilir.

> Ham HTTP kullanıyorsan onay yükümlülüğü sende: `/v1/terms/status` ile kontrol et,
> gerekirse `/v1/terms/text` metnini kullanıcıya göster, sonra `/v1/terms/accept` çağır
> ([`OPENAI_UYUMLU.md`](OPENAI_UYUMLU.md:26)).

---

## 3. Görev → komut

| Yapmak istediğim | Komut |
|---|---|
| Modelleri listele | `python main.py list_models` |
| Sohbet et | `python main.py chat "Merhaba" -m glm-5.3` |
| Sürekli sohbet | `python main.py repl` |
| Görseli sor | `python main.py vision "Bu resimde ne var?" test_gorsel.png` |
| Belgeden yazı çıkar (OCR) | `python main.py ocr test_fatura.png` |
| Sesi yazıya çevir | `python main.py transcribe test_ses.wav` |
| Vektör üret | `python main.py embeddings "merhaba dünya"` |
| Belgeleri sırala | `python main.py rerank "kedi" --docs "kedi hayvandır" "araba hızlıdır"` |
| Guard durumu | `python main.py guard_note` |
| Tüm komutlar | `python main.py --help` |

Windows'ta `chcp 65001 >nul &&` öneki Türkçe karakterler için gerekli — bölüm 15.

---

## 4. Sohbet

### CLI

Model vermezsen **canlı model listesinden menü** açılır, sonra prompt sorar:

```bash
python main.py chat
```
```
Model seç:
  1) auto (varsayılan)
  2) glm-5.3
  3) deepseek-v4-flash
  ...
numara [1=auto]: 2
Sen: Merhaba
glm-5.3> Merhaba! Size nasıl yardımcı olabilirim?
```

Modeli baştan söylemek için `-m`:

```bash
python main.py chat "Python'da liste nasıl ters çevrilir?" -m deepseek-v4-flash
python main.py stream "Uzun bir cevap yaz" -m auto     # akışlı (SSE)
```

### Kod içinden

```python
from main import chat, stream

cevap = chat("Merhaba", model="glm-5.3")        # -> cevap metni
chat()                                          # menüden model + prompt sorar
stream("Uzun bir cevap yaz", model="auto")      # akışlı yazdırır
```

`repl` sürekli sohbet — içinde şu komutlar var:

| Komut | İş |
|---|---|
| `/model` | model değiştir (menü açılır) |
| `/stream` | akışı aç/kapa |
| `/reset` | sohbet geçmişini sil |
| `/quit` | çık |

---

## 5. Görsel sor — `qwen3-vl-30b`

### CLI

```bash
python main.py vision "Bu resimde ne var?" test_gorsel.png
```
```
qwen3-vl-30b> Kırmızı dikdörtgen, mavi daire ve "MERHABA EVREN 12345" yazısı.
```

Farklı görsel + kendi sorun:

```bash
python main.py vision "Faturadaki toplam tutar kaç TL?" test_fatura.png
python main.py vision "Bu görselde kaç nesne var?" nesneler.png -m qwen3-vl-30b
```

### Kod içinden

```python
from main import vision

cevap = vision("Bu resimde ne var?", "test_gorsel.png")       # -> metin
vision("Faturadaki toplam tutar kaç TL?", "test_fatura.png")
vision("Bu görselde kaç nesne var?", "nesneler.png", model="qwen3-vl-30b")
```

⚠️ **Video desteklenmiyor (Wave-1):** `video_url` veya kare listesi gönderilirse
`400 feature_not_enabled — "Wave 1 yalnız metin kabul eder"` döner. Sadece `image_url` çalışır.

---

## 6. OCR — `dots-ocr`

### CLI

```bash
python main.py ocr test_fatura.png
```
Çıktı (`test_fatura.png` dosyasındaki metnin tamamı):

```json
{
  "model": "dots-ocr",
  "text": "FATURA\n\nEvren Teknoloji A.S.\n\nTarih: 21.09.2026\n\nFatura No: TR-2026-0042\n\nUrun: Sunucu Kiralama\n\nAdet: 3\n\nBirim Fiyat: 1.250,00 TL\n\nTOPLAM: 3.750,00 TL"
}
```

### ⚠️ Önemli: görselin içi dolu olmalı

`/v1/ocr` ayrı bir "yazı tanıma" motoru değil, **görsel-dil modeli**. Az yazı içeren
görselde (ör. tek satır "MERHABA EVREN 12345") belgeyi "boş sayfa" sanıp
**halüsinasyon** üretir — aynı görselde her çağrıda farklı sonuç dönebilir:

```
> python main.py ocr test_gorsel.png     # tek satır yazılı görsel
"text": "Merhaba Evren 122345"           # aynı görsel, iki farklı çağrı
"text": "Implementasyon Metriği的努力..."
```

Dolu bir belge görseli (sayfa, fatura) verildiğinde model tutarlı ve doğru çalışır:

| Görsel | dots-ocr |
|---|---|
| `test_fatura.png` (dolu belge) | doğru metin ✅ |
| `test_gorsel.png` (tek satır) | uydurma metin ❌ |

### `deepseek-ocr-2` çalışmıyor
Multipart ve base64 JSON, prompt'lu ve prompt'suz — her biçimde bozuk/uydurma metin
döndürüyor. Bunun yerine `dots-ocr` kullanın.

### İpuçları
- İstek yönergesi değiştirilebilir: `python main.py ocr sayfa.png --prompt "Sadece tabloyu çıkar"`
- Multipart'ta **MIME türü açıkça gönderilmeli**; `main.py` bunu `mimetypes` ile
  otomatik yapar. Elle kodda `files={"file": (ad, fh, "image/png")}` yazmazsan
  `400 "OCR dosyası bir görsel olmalıdır"` alırsın.
- Alternatif biçim: gövdede base64 data-URL — `{"model": "dots-ocr", "image": "data:image/png;base64,..."}` (bölüm 17).
- Uzak URL kabul edilmez, sadece gömülü (`data:`) görsel:
  `400 "OCR sadece gömülü (data:image/) görsel kabul eder, uzak URL değil"`.

### Kod içinden

```python
from main import ocr

sonuc = ocr("test_fatura.png")                        # -> {"model": ..., "text": ...}
print(sonuc["text"])
ocr("sayfa.png", prompt="Sadece tabloyu çıkar")       # çıktıyı yönlendir
ocr("belge.pdf", model="dots-ocr")
```

---

## 7. Ses → metin — `qwen3-asr-1.7b`

### CLI

```bash
python main.py transcribe test_ses.wav
```
```
Merhaba, bu leden bir eski es tanımı test eder. Bugun hava çok güzel.
```

Seçenekler:

| Seçenek | Değerler | Varsayılan |
|---|---|---|
| `--lang` | `tr`, `en`, ... | `tr` |
| `--format` | `json`, `text`, `srt`, `verbose_json`, `diarized_json` | `json` |
| `-m` | `qwen3-asr-1.7b` | `qwen3-asr-1.7b` |

```bash
python main.py transcribe ders.mp3 --lang tr --format srt
python main.py transcribe meeting.m4a --format diarized_json   # konuşmacı ayrımı
```

### Kod içinden

```python
from main import transcribe

sonuc = transcribe("test_ses.wav")                        # -> {"text": ...}
transcribe("ders.mp3", language="tr", response_format="srt")
transcribe("toplanti.m4a", response_format="diarized_json")   # konuşmacı ayrımı
```

---

## 8. Vektör — `qwen3-embedding-8b`

### CLI

Tek metin:
```bash
python main.py embeddings "merhaba dünya"
```
```
boyut: 4096  ilk 5: [0.0418, 0.0067, -0.0160, -0.0348, 0.0114]
```

Birden çok metin (her argüman bir metin):
```bash
python main.py embeddings "kedi" "köpek" "kuş"
```
```
3 metin için vektör üretildi
  [0] boyut 4096  ilk 5: [0.0167, -0.0042, 0.0032, -0.0324, 0.0284]
  [1] boyut 4096  ilk 5: [-0.0032, 0.0000, 0.0158, -0.0234, 0.0190]
  [2] boyut 4096  ilk 5: [0.0130, 0.0072, 0.0080, 0.0061, 0.0136]
```

### Kod içinden

```python
from main import embeddings

# tek metin
sonuc = embeddings("merhaba dünya")            # -> {"data": [{"embedding": [...], ...}]}
vec = sonuc["data"][0]["embedding"]            # 4096 boyutlu liste

# çok metin (API `input` dizisini destekler: 200 döner)
sonuc = embeddings(["kedi", "köpek", "kuş"])
for item in sonuc["data"]:
    print(item["index"], len(item["embedding"]))   # 0 4096 / 1 4096 / 2 4096

embeddings("aranacak metin", model="qwen3-embedding-8b")
```

---

## 9. Yeniden sıralama — `qwen3-reranker-8b`

Belgeleri `--docs` (doğrudan) veya `--docs-file` (dosyadan) ile verirsin; ikisi birlikte de
kullanılabilir.

### CLI

```bash
python main.py rerank "kedi" --docs "kedi hayvandır" "araba hızlıdır"
```
```json
{
  "model": "qwen/qwen3-vl-reranker-8b",
  "results": [
    { "index": 0, "document": { "text": "kedi hayvandır" }, "relevance_score": 0.3106 },
    { "index": 1, "document": { "text": "araba hızlıdır" }, "relevance_score": 0.0048 }
  ]
}
```

`.txt` dosyası — her satır bir belge:
```bash
python main.py rerank "fatura" --docs-file test_belgeler.txt
```

`.json` dosyası — dizideki her öğe bir belge:
```bash
python main.py rerank "sunucu" --docs-file test_belgeler.json
```

İkisini birlikte verirsen `--docs` önce, dosya sonra eklenir:
```bash
python main.py rerank "kahve" --docs "Cay demleme" --docs-file test_belgeler.json
```

Belge vermezsen çalışması için 2 örnek belge kullanılır ve şu uyarı çıkar:
```
uyarı: örnek belgeler kullanılıyor. kendi belgelerin için --docs veya --docs-file kullan.
```

Sorgu vermezsen terminalde `Sorgu:` diye sorulur.

> Puanlar çağrıdan çağrıya çok az değişebilir; sıralama kararlıdır.

### Kod içinden

```python
from main import rerank

# belge listesi doğrudan
sonuc = rerank("kredi faizi", ["faiz oranları yükseldi", "hava bugün güneşli"])
for r in sonuc["results"]:
    print(r["index"], r["relevance_score"])

# belge dosyadan (.txt satır satır | .json dizi)
sonuc = rerank("fatura", docs_file="test_belgeler.txt")

# ikisi birlikte
sonuc = rerank("kahve", ["Çay demleme"], docs_file="test_belgeler.json")
```

Çıktı (`results`) **alaka puanına göre azalan** sırada gelir; `index` özgün belge sırasıdır.

---

## 10. Guard — `qwen3-guard-4b` (şu an kapalı)

### CLI

```bash
python main.py guard_note
```
```
qwen3-guard-4b şu an kullanılamıyor:
  - POST /v1/guard            -> 404 (uç yok)
  - POST /v1/chat/completions -> 400 "bu model sohbet ucunu desteklemiyor (görev: guard)"
```

### Kod içinden

```python
from main import guard_note

guard_note()      # kısıt açıklamasını yazdırır
```

Sunucu tarafında açılana kadar bu model hiçbir uçtan çağrılamaz.

---

## 11. Model listesi

### CLI

```bash
python main.py list_models
```

### Kod içinden

```python
from main import list_models

data = list_models()                    # yazdırır + {"data": [...]} döner
for m in data["data"]:
    print(m["id"], m["task"])
```

---

## 12. Şartlar (kullanım sözleşmesi)

Her API fonksiyonu başında `ensure_terms()` çağırır. Kabul edilmemişse şart
metni gösterilir ve **E/h** sorulur; otomatik kabul **yoktur**:

```
fonksiyon çağrıldı
   └─ GET /v1/terms/status
        ├─ accepted = true  ──────────────→ çağrıya devam
        └─ accepted = false
             └─ GET /v1/terms/text → metni yazdır
                  └─ "Kabul ediyor musunuz? (E/h)"
                       ├─ E  → POST /v1/terms/accept → devam
                       └─ h / başka / EOF → çık (kabul edilmedi)
```

### CLI

```bash
python main.py terms_status      # {"current_version": 1, "accepted": true, ...}
python main.py terms_text        # şart metnini oku
python main.py accept_terms      # okuduktan sonra onayla (sürümü otomatik bulur)
```

### Kod içinden

```python
from main import terms_status, terms_text, accept_terms, ensure_terms

terms_status()        # {"current_version": 1, "is_material": True, "accepted": False}
terms_text()          # sözleşme metni
accept_terms()        # onayla (sürüm verilmezse sunucudaki güncel sürüm)
ensure_terms()        # kabul yoksa metni göster + E/h sor; red/EOF -> SystemExit
```

`accept_terms` ve `terms_text` diğer komutlardan **bağımsız** çalışır (şart sorusu sormazlar),
böylece reddettikten sonra tekrar okumak/onaylamak mümkündür.

---

## 13. Tümünü birlikte: kod içinden kullanım

```python
from main import (list_models, chat, stream, vision, ocr, transcribe,
                  embeddings, rerank, guard_note, repl)

list_models()                                   # modelleri yazdırır + dict döner
chat("Merhaba", model="glm-5.3")                # -> cevap metni
stream("Uzun cevap", model="auto")              # -> akışlı yazdırır
vision("Ne var?", "test_gorsel.png")            # -> cevap metni
ocr("test_fatura.png")                          # -> {"model": ..., "text": ...}
transcribe("test_ses.wav", language="tr")       # -> {"text": ...}
embeddings("merhaba", model="qwen3-embedding-8b")
embeddings(["kedi", "köpek"])                   # çoklu metin
rerank("kedi", ["kedi hayvandır", "araba hızlıdır"])
rerank("fatura", docs_file="test_belgeler.txt")  # belgeler dosyadan
repl()                                          # sürekli sohbet döngüsü
```

Hepsi `ensure_terms()` çağırır: şartlar kabul edilmemişse metin gösterilir ve
**E/h** onayın istenir (red verirsen ya da etkileşim yoksa çalışmaz).
Bağlantı bilgileri `.env` → `API_URL` (anahtar), `BASE_URL` (adres; varsayılan `https://evren-llmapi.ssyz.org.tr/v1`).

## 14. CLI referansı

`[ ... ]` = isteğe bağlı, değilse komut sen sorar (ya da varsayılanı kullanır).

| Komut | Argüman | Notlar |
|---|---|---|
| `list_models` | — | id, task, modalities, free_until |
| `chat` | `["prompt"]` | prompt yoksa sorar |
| `stream` | `["prompt"]` | SSE akışlı |
| `repl` | — | `/model` `/stream` `/reset` `/quit` |
| `vision` | `["soru" [görsel]]` | varsayılan görsel: `test_gorsel.png`; `-m qwen3-vl-30b` |
| `embeddings` | `"metin" ["metin2" ...]` | tek ya da çok metin; 4096 boyut |
| `rerank` | `["sorgu"] [--docs ...] [--docs-file ...]` | belge verilmezse 2 örnek belge + uyarı |
| `transcribe` | `[dosya]` | `--lang`, `--format` |
| `ocr` | `[dosya]` | `--prompt <metin>`; `-m dots-ocr` (önerilen) |
| `guard_note` | — | kısıt açıklaması |
| `terms_status` `terms_text` `accept_terms` | — | kullanım şartları (onay sorusu sormazlar) |

Seçenekler:

| Seçenek | Komut | Anlam |
|---|---|---|
| `-m, --model <id>` | hepsi | model seç (`auto`, `glm-5.3`, `deepseek-v4-flash`, `gemma-4-31b`, `qwen3.8-flash-next`, `qwen3-vl-30b`) |
| `--prompt <metin>` | `ocr` | OCR yönergesi (varsayılan: metni aynen çıkar) |
| `--lang <kod>` | `transcribe` | dil (varsayılan `tr`) |
| `--format <biçim>` | `transcribe` | `json`\|`text`\|`srt`\|`verbose_json`\|`diarized_json` |
| `--docs "b1" "b2"` | `rerank` | belgeleri doğrudan ver (birden çok değer alır) |
| `--docs-file <dosya>` | `rerank` | belgeler dosyadan: `.txt` (her satır bir belge) \| `.json` (dizi) |

---

## 15. Sık hatalar

| Hata | Sebep | Çözüm |
|---|---|---|
| `403 terms_not_accepted` | Şartlar onaylanmamış (ör. E/h sorusuna `h` dedin) | `python main.py terms_text` oku, sonra `python main.py accept_terms` |
| Şart sorusu hiç çıkmıyor / komut çıkıyor | Etkileşimsiz ortam (stdin yok) | Terminalden çalıştır; onay için `accept_terms` |
| `400 OCR dosyası bir görsel olmalıdır` | multipart'ta MIME yok | `files={"file": (ad, fh, "image/png")}` |
| OCR çıktısı uydurma/anlamsız | Görselde az yazı var, model halüsine ediyor | Dolu belge görseli kullan; `dots-ocr` tercih et |
| `400 feature_not_enabled (video)` | Wave-1'de video kapalı | Görsel (`image_url`) kullan, video gönderme |
| `400 ... (görev: guard)` | Guard ucu yok | Şimdilik kullanılamaz, `guard_note` |
| `UnicodeEncodeError: charmap` | Windows konsol kodlaması | `chcp 65001 >nul && python ...` |
| `IndexError` akışta | SSE'nin son `usage` paketinde `choices` boş | `main.py` bunu atlar; elle kodda `if not choices: continue` |
| `API_URL boş...` ile çıkıyor | `.env` yok ya da `API_URL` yazılmamış | `copy .env.example .env` → `API_URL=evren_llm_...` |
| `belge dosyası yok: X` | `--docs-file` yolu hatalı | Yolu kontrol et (dosya `.txt`/`.json` olmalı) |
| `X geçerli JSON değil` | `.json` belge dosyası bozuk | Dosyayı düzelt ya da `.txt` kullan (her satır bir belge) |
| `hata: --docs için en az bir belge gerekli` | `--docs` verildi ama değer yok | `--docs "belge 1" "belge 2"` |
| rerank "örnek belgeler" uyarısı | Belge verilmedi | `--docs` veya `--docs-file` ekle |
| `401 API anahtarı eksik` | Anahtar geçersiz | `.env` içindeki `API_URL` değerini kontrol et |
| İstek yanlış adrese gidiyor | `BASE_URL` hatalı | `BASE_URL` `/v1` ile bitmeli |

---

## 16. Uçlar

| Uç | İş | CLI |
|---|---|---|
| `/chat/completions` | sohbet (+stream, görsel) | `chat` `stream` `repl` `vision` |
| `/models` | model kataloğu | `list_models` |
| `/embeddings` | vektörleştirme | `embeddings` |
| `/rerank` | yeniden sıralama | `rerank` |
| `/ocr` | belge/görsel → metin | `ocr` |
| `/audio/transcriptions` | ses → metin | `transcribe` |
| `/responses` | OpenAI Responses şekli | — |
| `/terms/status` `/terms/text` `/terms/accept` | kullanım şartları | `terms_*` |
| `/quota` `/requests/{id}` | kota / istek takibi | — |

Notlar:
- Tüm çıkarım modelleri **2026-11-01'e kadar ücretsiz** (0.00 CR).
- Model seçmek istemezsen `auto` yaz — gateway uygun modele yönlendirir.
- Yanıtlarda `usage.evren.routed_model` gerçekte hangi modelin çalıştığını gösterir.

---

## 17. Ham API referansı

CLI'ı (`python main.py ...`) veya `from main import ...` çağrısını kullanmadan
**doğrudan HTTP** isteği atmak isteyenler için. Bölüm 4-12'deki her işin
ham karşılığı burada.

### Bağlantı

```python
import os, sys, requests
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows Türkçe karakter
except Exception:
    pass

load_dotenv()
KEY = os.getenv("API_URL")
BASE = os.getenv("BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1")
H = {"X-API-Key": KEY, "Authorization": f"Bearer {KEY}"}
```
Başlık olarak `X-API-Key` veya `Authorization: Bearer` — ikisi de geçerli.

### Şartları onayla (ilk sefer)

```python
status = requests.get(f"{BASE}/terms/status", headers=H).json()
if not status["accepted"]:
    text = requests.get(f"{BASE}/terms/text", headers=H).json()   # metni oku
    print(text["content"])
    requests.post(f"{BASE}/terms/accept", headers=H, json={"version": status["current_version"]})
```

### Modelleri listele

```python
data = requests.get(f"{BASE}/models", headers=H).json()
for m in data["data"]:
    print(m["id"], m["task"], m["modalities"])
```
```
dots-ocr           ocr
deepseek-v4-flash  chat
gemma-4-31b        chat
qwen3-vl-30b       vision_chat
qwen3-embedding-8b embedding
qwen3-reranker-8b  rerank
deepseek-ocr-2     ocr
qwen3-asr-1.7b     audio_transcription
auto               chat
qwen3.8-flash-next chat
glm-5.3            chat
```

### Sohbet

```python
r = requests.post(
    f"{BASE}/chat/completions",
    headers=H,
    json={"model": "auto", "messages": [{"role": "user", "content": "Merhaba"}]},
)
print(r.json()["choices"][0]["message"]["content"])
```

### Akış (streaming)

```python
r = requests.post(
    f"{BASE}/chat/completions",
    headers=H,
    json={"model": "glm-5.3", "messages": [{"role": "user", "content": "Merhaba"}], "stream": True},
    stream=True,
)
for line in r.iter_lines():
    if line:
        print(line.decode())
```

### Görsel (vision)

```python
import base64

b64 = base64.b64encode(open("test_gorsel.png", "rb").read()).decode()
r = requests.post(f"{BASE}/chat/completions", headers=H, json={
    "model": "qwen3-vl-30b",
    "messages": [{"role": "user", "content": [
        {"type": "image_url",
         "image_url": {"url": f"data:image/png;base64,{b64}"}},
        {"type": "text", "text": "Bu resimde ne var?"},
    ]}],
})
print(r.json()["choices"][0]["message"]["content"])
```

### OCR

Multipart (dosya) — tercih edilen yol:

```python
with open("test_fatura.png", "rb") as fh:
    r = requests.post(f"{BASE}/ocr", headers=H,
                      data={"model": "dots-ocr",
                            "prompt": "Metni aynen çıkar."},   # isteğe bağlı
                      files={"file": ("test_fatura.png", fh, "image/png")})
print(r.json()["text"])
```

Base64 JSON — uzak URL değil, gömülü `data:` URL olmalı:

```python
import base64
b64 = base64.b64encode(open("test_fatura.png", "rb").read()).decode()
r = requests.post(f"{BASE}/ocr", headers={**H, "Content-Type": "application/json"},
                  json={"model": "dots-ocr",
                        "image": f"data:image/png;base64,{b64}"})
print(r.json()["text"])
```

### Ses → metin

```python
with open("test_ses.wav", "rb") as fh:
    r = requests.post(f"{BASE}/audio/transcriptions", headers=H,
                      data={"model": "qwen3-asr-1.7b", "language": "tr",
                            "response_format": "json"},
                      files={"file": ("test_ses.wav", fh, "audio/wav")})
print(r.json()["text"])
```

### Embedding

```python
r = requests.post(f"{BASE}/embeddings", headers=H,
                  json={"model": "qwen3-embedding-8b", "input": "merhaba dünya"})
vec = r.json()["data"][0]["embedding"]   # boyut: 4096

# `input` dizi de olabilir (tek istekte çok metin -> `data` listesi)
r = requests.post(f"{BASE}/embeddings", headers=H,
                  json={"model": "qwen3-embedding-8b",
                        "input": ["kedi", "köpek", "kuş"]})
for item in r.json()["data"]:
    print(item["index"], len(item["embedding"]))
```

### Rerank

```python
r = requests.post(f"{BASE}/rerank", headers=H, json={
    "model": "qwen3-reranker-8b",
    "query": "kedi",
    "documents": ["kedi hayvandır", "araba hızlıdır"],   # kendi belgelerin
})
for res in r.json()["results"]:
    print(res["index"], res["relevance_score"])
```

`/rerank` yalnızca gövdedeki `documents` dizisini kullanır; dosyadan okuma
(`--docs-file`) tamamen istemci tarafındadır ([`main.py` `_load_docs()`](main.py:401)).

### OpenAI SDK ile

```python
from openai import OpenAI
client = OpenAI(
    base_url=os.getenv("BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1"),
    api_key=os.getenv("API_URL"),
)
resp = client.chat.completions.create(model="auto", messages=[{"role": "user", "content": "Merhaba"}])
print(resp.choices[0].message.content)
```
