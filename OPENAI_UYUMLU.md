# OpenAI Uyumlu Sağlayıcı Olarak Kullanma

Evren LLM Gateway, OpenAI REST sözleşmesini (istek/yanıt şeması, hata gövdesi, streaming) uygular.
Yani OpenAI istemcisi bekleyen her araca **özel sağlayıcı (custom / OpenAI-compatible provider)** olarak eklenebilir.

## 1. Gerekli 3 bilgi
Her yere gireceğin alanlar:

| Alan | Değer |
|------|-------|
| **Base URL** | `https://evren-llmapi.ssyz.org.tr/v1` |
| **API Key** | `evren_llm_...` (`.env` → `API_URL`) |
| **Model** | `auto` veya tabloda bir `id` (bkz. bölüm 4) |

Not: Base URL sonunda `/v1` olmalı. Bazı araçlar sona `/` ister:
`https://evren-llmapi.ssyz.org.tr/v1/`

## 2. Kimlik doğrulama
İki başlık da kabul edilir:
```
Authorization: Bearer evren_llm_...
X-API-Key: evren_llm_...
```
SDK'lar otomatik `Authorization: Bearer` gönderir → ek ayar gerekmez.

## 3. Ön koşul: kullanım şartları (kullanıcı onayı zorunlu)
İlk çağrı öncesi **tek seferlik** onay gerekir, yoksa **403 `terms_not_accepted`**.
Onay **otomatik yapılmaz** — kullanıcının şartları okuyup kabul etmesi gerekir.

### Bu CLI ile
İlk çağrıda şart metni ekrana yazdırılır ve `Kabul ediyor musunuz? (E/h)` sorulur.
`E` → onaylanır ve devam edilir. `h` / boş / etkileşimsiz ortam → çalışmaz.
Onay bir kez verilir (sunucuya kaydedilir).

### SDK / kendi kodun / başka araç ile
Akış iki adımdır; onay cümlesini kullanıcıya gösterip onayı aldıktan sonra:
```
GET  /v1/terms/text                                # metni kullanıcıya göster
     → kullanıcı E/h cevabı verir
POST /v1/terms/accept  {"version": 1}              # E ise onayla
```
Terminalden hızlı yol: `python main.py terms_text` (oku) → `python main.py accept_terms` (onayla).

> Bir GUI/araç içinde otomatik kabul yapmayın: kullanıcıya metni gösterin.
> Onay kullanıcıya ait bir iradedir, uygulamanın kararı değil.

## 4. Sohbet için model id'leri
| id | açıklama |
|----|----------|
| `auto` | otomatik yönlendirme — model seçmek istemezsen bunu yaz |
| `glm-5.3` | amiral model, derin akıl yürütme |
| `deepseek-v4-flash` | kod/ajan, 1M bağlam |
| `gemma-4-31b` | görsel okuma + chat |
| `qwen3.8-flash-next` | hızlı, yüksek hacim |
| `qwen3-vl-30b` | görsel (image_url); **video Wave-1'de kapalı** |

Embedding/rerank/OCR/ASR modelleri sohbet ucunu desteklemez (bkz. `README.md`).
OCR için `dots-ocr` kullan; `deepseek-ocr-2` testlerde kullanılabilir sonuç vermedi.
OCR'ı sohbet ucundan değil, `/v1/ocr` uçundan çağır.
`qwen3-guard-4b` için henüz uç yok: `/guard` → 404, chat → 400 `(görev: guard)`.
Görsel mesaj biçimi ve diğer görev uçları (vision/OCR/ASR/embeddings/rerank)
için `README.md` bölümlerine bak.

## 5. Sohbet ucu (temel)
```
POST /v1/chat/completions
{
  "model": "auto",
  "messages": [{"role": "user", "content": "Merhaba"}],
  "stream": false
}
```
Yanıt OpenAI şeması: `choices[0].message.content`, `usage.total_tokens`.
`"stream": true` → standart `text/event-stream` (SSE) döner.

## 6. Python SDK
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://evren-llmapi.ssyz.org.tr/v1",
    api_key="evren_llm_...",
)
r = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Merhaba"}],
)
print(r.choices[0].message.content)
```

## 7. Node.js SDK
```js
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://evren-llmapi.ssyz.org.tr/v1",
  apiKey: "evren_llm_...",
});
const r = await client.chat.completions.create({
  model: "auto",
  messages: [{ role: "user", content: "Merhaba" }],
});
console.log(r.choices[0].message.content);
```

## 8. LangChain
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="https://evren-llmapi.ssyz.org.tr/v1",
    api_key="evren_llm_...",
    model="auto",
)
```

## 9. GUI araçları (Open WebUI, LM Studio-vari, Cline, Continue, Aider...)
"OpenAI" veya "OpenAI-compatible" sağlayıcısını seç, alanları doldur:

| Araç alanı | Değer |
|------------|-------|
| Base URL / API Base / Endpoint | `https://evren-llmapi.ssyz.org.tr/v1` |
| API Key / Token | `evren_llm_...` |
| Model / Model ID | `auto` (liste çekilemezse elle yaz) |

Model listesi otomatik çekilmiyorsa (`/v1/models` çağrısını desteklemeyen araçlar), model adını elle `auto` yaz.

## 10. curl ile doğrulama
```powershell
curl.exe "https://evren-llmapi.ssyz.org.tr/v1/chat/completions" `
  -H "Authorization: Bearer evren_llm_..." `
  -H "Content-Type: application/json" `
  -d '{\"model\":\"auto\",\"messages\":[{\"role\":\"user\",\"content\":\"Merhaba\"}]}'
```

## 11. Sorun giderme
| Hata | Sebep / çözüm |
|------|----------------|
| `401 unauthorized` | API key yok/yanlış. `X-API-Key` veya `Bearer` başlığını kontrol et. |
| `403 terms_not_accepted` | Bölüm 3'teki onayı yap (`error.evren.required_terms_version`). |
| `404` | Base URL'de `/v1` eksik veya `/models` yerine yanlış yol. |
| Model seçilemiyor | Model id'yi bölüm 4'ten birebir yaz (`glm-5.3`, `auto`...). |
| Stream donuyor | İstekte `"stream": true` var mı, araç SSE destekliyor mu. |

## 12. EVREN'e özgü ek alanlar
OpenAI şemasının üzerine eklenir, SDK'lar **yok sayar** (akışı bozmaz):
- `error.evren` → kalan kota, alternatif model, kabul edilecek sürüm.
- `X-Evren-Credits-*` yanıt başlıkları → BORÇ/kalan kredi.
- `usage.evren.routed_model` → `auto` seçiminde hangi modele gittiği.

## 13. Not
- Tüm çıkarım modelleri **2026-11-01'e kadar ücretsiz** (0.00 CR).
- Benim denemelerimde Usage Limit günlük 10m token, dakikalık 500k token, bu limitler bana çok az geldi ilerde artmasını temenni ederim.
