"""EvrenLLMApi - her fonksiyon tek başına çalıştırılabilir.

Kullanım:
    python main.py list_models
    python main.py chat "Merhaba"
    python main.py vision "Bu resimde ne var?" test_gorsel.png
    python main.py ocr test_fatura.png
    python main.py transcribe test_ses.wav
    ...

Veya kod içinden:
    from main import list_models
    list_models()

Kullanım şartları (ilk kullanım):
    Şartlar OTOMATİK KABUL EDİLMEZ. Kabul edilmemişse şart metni ekrana
    yazdırılır ve "Kabul ediyor musunuz? (E/h)" sorusu sorulur. Red verilirse
    ya da etkileşim kurulamazsa (stdin yok) program çalışmaz.

Not (Wave-1 gateway kısıtları, canlı test edilmiştir):
    - qwen3-guard-4b : uç yok (/guard 404, chat 400 "görev: guard") -> kullanılamaz
    - qwen3-vl-30b video : 400 feature_not_enabled "Wave 1 yalnız metin kabul eder"
      -> video gönderilemez, sadece image_url çalışır
"""

import base64
import json
import mimetypes
import os
import sys

import requests
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows Türkçe karakter
except Exception:
    pass

load_dotenv()

KEY = os.getenv("API_URL")
BASE = os.getenv("BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1")
if not KEY:
    raise SystemExit(
        "API_URL boş. .env dosyasına anahtarını yaz:\n"
        "  copy .env.example .env\n"
        "  API_URL=evren_llm_..."
    )
H = {"X-API-Key": KEY, "Authorization": f"Bearer {KEY}"}


# ---------------------------------------------------------------- şartlar

def terms_status() -> dict:
    """Kullanım şartları kabul edildi mi."""
    r = requests.get(f"{BASE}/terms/status", headers=H, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def terms_text() -> dict:
    """Kullanım şartları metnini oku."""
    r = requests.get(f"{BASE}/terms/text", headers=H, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(data.get("content", data))
    return data


def accept_terms(version: int | None = None) -> dict:
    """Şartları onayla (sürüm verilmezse sunucudaki güncel sürüm)."""
    if version is None:
        version = requests.get(f"{BASE}/terms/status", headers=H, timeout=30).json() \
            .get("current_version", 1)
    r = requests.post(f"{BASE}/terms/accept", headers=H, json={"version": version}, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return data


YES = {"e", "evet", "y", "yes", "kabul", "kabul ediyorum"}


def _ask_accept(version: int) -> None:
    """Şart metnini göster, E/h sor, kabul edilirse onayla.

    Red verilirse ya da etkileşim kurulamazsa (EOF) çıkılır.
    """
    print("=" * 70)
    print("EVREN LLM GATEWAY — KULLANIM ŞARTLARI (v%s)" % version)
    print("=" * 70)
    try:
        text = requests.get(f"{BASE}/terms/text", headers=H, timeout=30).json()
        print(text.get("content", text))
    except Exception as exc:  # metin alınamazsa sessiz geçme: uyar
        print(f"[!] Şart metni alınamadı ({exc}). Yeniden deneyin: python main.py terms_text")
    print("=" * 70)

    try:
        answer = input("Kabul ediyor musunuz? (E/h): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(
            "şartlar kabul edilmedi (etkileşim kurulamadı).\n"
            "terminalden çalıştırıp onaylayın: python main.py accept_terms"
        )

    if answer not in YES:
        raise SystemExit(
            "şartlar kabul edilmedi, çıkılıyor.\n"
            "okumak için: python main.py terms_text"
        )

    accept_terms(version)


def ensure_terms() -> None:
    """Şartlar kabul edilmiş mi kontrol et; değilse SOR, kendiliğinden kabul etme.

    Tüm API fonksiyonları bunu çağırır. Sunucu tarafında `accepted=false` ise
    ya da yeni bir şart sürümü (is_material) varsa kullanıcıya E/h sorulur.
    """
    try:
        data = requests.get(f"{BASE}/terms/status", headers=H, timeout=30).json()
    except Exception as exc:
        raise SystemExit(f"şartlar durumu alınamadı: {exc}")

    if data.get("accepted"):
        return
    _ask_accept(data.get("current_version", 1))


# ---------------------------------------------------------------- modeller

def list_models() -> dict:
    """Hesaba tanımlı modelleri listele."""
    ensure_terms()
    r = requests.get(f"{BASE}/models", headers=H, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(f"object: {data.get('object')}  count: {len(data.get('data', []))}\n")
    for m in data.get("data", []):
        mods = "/".join(m.get("modalities", []))
        free = m.get("pricing", {}).get("free_until", "")
        print(f"{m.get('id'):<24} {m.get('task', ''):<20} [{mods}] free_until={free}")
    return data


# ---------------------------------------------------------------- sohbet

CHAT_MODELS = ["auto", "glm-5.3", "deepseek-v4-flash", "gemma-4-31b",
               "qwen3.8-flash-next", "qwen3-vl-30b"]


def _chat_models() -> list:
    """Canlı model listesinden sohbet modellerini al; olmazsa sabit liste."""
    try:
        r = requests.get(f"{BASE}/models", headers=H, timeout=30)
        r.raise_for_status()
        ids = [m["id"] for m in r.json().get("data", []) if m.get("task") in ("chat", "vision_chat")]
        return ids or CHAT_MODELS
    except Exception:
        return CHAT_MODELS


def _pick_model(model: str | None = None) -> str:
    """model verilmişse onu kullan; yoksa menüden seçtir."""
    if model:
        return model
    models = _chat_models()
    print("Model seç:")
    for i, name in enumerate(models, 1):
        mark = " (varsayılan)" if name == "auto" else ""
        print(f"  {i}) {name}{mark}")
    try:
        raw = input(f"numara [1={models[0]}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return models[0]
    if not raw:
        return models[0]
    if raw.isdigit() and 1 <= int(raw) <= len(models):
        return models[int(raw) - 1]
    return raw  # elle yazılan id


def _pick_prompt(prompt: str | None = None) -> str:
    """prompt verilmişse onu kullan; yoksa kullanıcıdan al."""
    if prompt:
        return prompt
    while True:
        try:
            text = input("Sen: ").strip()
        except EOFError:
            raise SystemExit(0)
        if text:
            return text


def _post_chat(prompt: str, model: str, stream_mode: bool):
    return requests.post(
        f"{BASE}/chat/completions",
        headers=H,
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream_mode,
        },
        stream=stream_mode,
        timeout=180,
    )


def chat(prompt: str | None = None, model: str | None = None) -> str:
    """Tek seferlik sohbet. prompt/model yoksa interaktif sorar."""
    ensure_terms()
    model = _pick_model(model)
    prompt = _pick_prompt(prompt)
    r = _post_chat(prompt, model, False)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    print(f"{model}> {content}")
    return content


def stream(prompt: str | None = None, model: str | None = None) -> str:
    """Akışlı (SSE) sohbet. prompt/model yoksa interaktif sorar."""
    ensure_terms()
    model = _pick_model(model)
    prompt = _pick_prompt(prompt)
    print(f"{model}> ", end="", flush=True)
    full = []
    with _post_chat(prompt, model, True) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            text = line.decode("utf-8")
            if not text.startswith("data: "):
                continue
            payload = text[6:]
            if payload == "[DONE]":
                break
            choices = json.loads(payload).get("choices") or []
            if not choices:
                continue  # usage-only / boş kuyruk
            delta = choices[0].get("delta", {}).get("content", "")
            full.append(delta)
            sys.stdout.write(delta)
            sys.stdout.flush()
    print()
    return "".join(full)


def repl(model: str | None = None) -> None:
    """Sürekli sohbet döngüsü. Çıkış: /quit  (model değiştir: /model)"""
    ensure_terms()
    model = _pick_model(model)
    print(f"model: {model}  |  çıkış: /quit  |  model değiştir: /model  |  akış: /stream")
    stream_mode = False
    history: list[dict] = []

    def send(text: str) -> None:
        payload = {"model": model, "messages": history + [{"role": "user", "content": text}],
                   "stream": stream_mode}
        r = requests.post(f"{BASE}/chat/completions", headers=H, json=payload,
                          stream=stream_mode, timeout=180)
        r.raise_for_status()
        if stream_mode:
            print(f"{model}> ", end="", flush=True)
            reply = []
            for line in r.iter_lines():
                if not line or not line.decode("utf-8").startswith("data: "):
                    continue
                body = line.decode("utf-8")[6:]
                if body == "[DONE]":
                    break
                choices = json.loads(body).get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta", {}).get("content", "")
                reply.append(delta)
                sys.stdout.write(delta)
                sys.stdout.flush()
            print()
            reply = "".join(reply)
        else:
            reply = r.json()["choices"][0]["message"]["content"]
            print(f"{model}> {reply}")
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})

    while True:
        try:
            text = input("Sen: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text in ("/quit", "/exit", "/q"):
            break
        if text == "/model":
            model = _pick_model()
            print(f"model: {model}")
            continue
        if text == "/stream":
            stream_mode = not stream_mode
            print(f"akış: {'açık' if stream_mode else 'kapalı'}")
            continue
        if text == "/reset":
            history.clear()
            print("geçmiş temizlendi")
            continue
        send(text)


# ---------------------------------------------------------------- görüş (vision)

def _data_url(path: str) -> str:
    """Dosyayı data: URL'ye çevir (görsel -> base64)."""
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return f"data:{mime};base64,{b64}"


def vision(prompt: str = "Bu resimde ne var?", image_path: str = "test_gorsel.png",
           model: str = "qwen3-vl-30b") -> str:
    """Görsel sorusu (qwen3-vl-30b). image_url data-URL olarak gönderilir.

    Örnek:
        python main.py vision "Şu belgede ne yazıyor?" belge.png
        python main.py vision "Resmi özetle" -m qwen3-vl-30b

    NOT: video (video_url / frame listesi) Wave-1'de kapalı:
         400 feature_not_enabled "Wave 1 yalnız metin kabul eder".
    """
    ensure_terms()
    if not os.path.exists(image_path):
        raise SystemExit(f"dosya yok: {image_path}")
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": _data_url(image_path)}},
                {"type": "text", "text": prompt},
            ],
        }],
    }
    r = requests.post(f"{BASE}/chat/completions", headers=H, json=payload, timeout=300)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    print(f"{model}> {content}")
    return content


# ---------------------------------------------------------------- diğer uçlar

def embeddings(text: str = "merhaba dünya", model: str = "qwen3-embedding-8b") -> dict:
    """Metin(ler) için gömme vektörü üret.

    text: tek metin ya da metin listesi.
    Örnek:
        python main.py embeddings "merhaba dünya"
        python main.py embeddings "kedi" "köpek" "kuş"
    """
    ensure_terms()
    if isinstance(text, (list, tuple)):
        payload = list(text)
    else:
        payload = text
    r = requests.post(
        f"{BASE}/embeddings", headers=H, json={"model": model, "input": payload}, timeout=120
    )
    r.raise_for_status()
    data = r.json()
    vecs = data.get("data", [])
    if len(vecs) == 1:
        vec = vecs[0]["embedding"]
        print(f"boyut: {len(vec)}  ilk 5: {vec[:5]}")
    else:
        print(f"{len(vecs)} metin için vektör üretildi")
        for item in vecs:
            print(f"  [{item.get('index', 0)}] boyut {len(item['embedding'])}  ilk 5: {item['embedding'][:5]}")
    return data


def _load_docs(docs: list | None, docs_file: str | None) -> list:
    """--docs ve --docs-file girdilerini tek belge listesinde birleştir."""
    out = list(docs or [])
    if not docs_file:
        return out
    if not os.path.exists(docs_file):
        raise SystemExit(f"belge dosyası yok: {docs_file}")
    with open(docs_file, encoding="utf-8") as fh:
        raw = fh.read()
    if docs_file.lower().endswith(".json"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{docs_file} geçerli JSON değil: {exc}")
        if isinstance(parsed, str):
            parsed = [parsed]
        if not isinstance(parsed, list):
            raise SystemExit(f"{docs_file} bir JSON dizisi ya da metin olmalı")
        out += [str(x) for x in parsed]
    else:
        out += [line.strip() for line in raw.splitlines() if line.strip()]
    return out


def rerank(query: str | None = None, documents: list | None = None,
           model: str = "qwen3-reranker-8b", docs_file: str | None = None) -> dict:
    """Belgeleri sorguya alaka düzeyine göre yeniden sırala.

    documents: belge listesi. docs_file: .txt (her satır bir belge) veya .json (dizi).
    Belge verilmezse örnek belgeler kullanılır ve uyarı basılır.
    Örnek:
        python main.py rerank "kedi" --docs "kedi hayvandır" "araba hızlıdır"
        python main.py rerank "fatura kesimi" --docs-file test_belgeler.txt
    """
    ensure_terms()
    documents = _load_docs(documents, docs_file)
    if query is None:
        try:
            query = input("Sorgu: ").strip()
        except (EOFError, KeyboardInterrupt):
            raise SystemExit("sorgu gerekli: python main.py rerank \"sorgun\" --docs \"belge 1\" \"belge 2\"")
    if not query:
        raise SystemExit("sorgu boş olamaz")
    if not documents:
        documents = ["kedi hayvandır", "araba hızlıdır"]
        print("uyarı: örnek belgeler kullanılıyor. kendi belgelerin için --docs veya --docs-file kullan.")
    r = requests.post(
        f"{BASE}/rerank",
        headers=H,
        json={"model": model, "query": query, "documents": documents},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def transcribe(file_path: str = "test_ses.wav", model: str = "qwen3-asr-1.7b",
               language: str = "tr", response_format: str = "json") -> dict:
    """Ses dosyasını metne çevir (qwen3-asr-1.7b).

    response_format: json | text | srt | verbose_json | diarized_json
    Örnek:
        python main.py transcribe test_ses.wav
        python main.py transcribe sark.mp3 --lang en --format verbose_json
    """
    ensure_terms()
    if not os.path.exists(file_path):
        raise SystemExit(f"dosya yok: {file_path}")
    data = {"model": model, "response_format": response_format}
    if language:
        data["language"] = language
    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    with open(file_path, "rb") as fh:
        # MIME türü açıkça verilmeli; yoksa sunucu dosyayı tanıyamayabilir
        r = requests.post(
            f"{BASE}/audio/transcriptions",
            headers=H,
            data=data,
            files={"file": (os.path.basename(file_path), fh, mime)},
            timeout=300,
        )
    r.raise_for_status()
    out = r.json() if response_format != "text" else {"text": r.text}
    print(out.get("text", out) if isinstance(out, dict) else out)
    return out


OCR_PROMPT = ("Bu görseldeki tüm metni OLDUĞU GİBİ çıkar - "
              "yorum, özet veya açıklama ekleme, sadece metnin kendisini yaz.")


def ocr(file_path: str = "test_fatura.png", model: str = "dots-ocr",
        prompt: str | None = None) -> dict:
    """Belge/görselden metin çıkar.

    Tecrübeyle ölçülen davranış (canlı test):
      - dots-ocr        : gerçek belgede (fatura/sayfa) tutarlı ve doğru.
                          Az yazı içeren görselde HALÜSİNASYON üretebilir;
                          aynı görselde farklı sonuç dönebilir.
      - deepseek-ocr-2  : testlerde kullanılabilir sonuç vermedi (çöp metin).

    ÖNEMLİ 1: multipart'ta MIME türü açıkça gönderilmeli; düz dosya nesnesi
              400 "OCR dosyası bir görsel olmalıdır" hatası verir.
    ÖNEMLİ 2: /v1/ocr bir görsel-dil modeli; `prompt` gönderilirse çıktıyı
              yönlendirir (varsayılan OCR_PROMPT uygundur).

    Örnek:
        python main.py ocr test_fatura.png
        python main.py ocr belge.pdf
    """
    ensure_terms()
    if not os.path.exists(file_path):
        raise SystemExit(f"dosya yok: {file_path}")
    mime = mimetypes.guess_type(file_path)[0] or "image/png"
    with open(file_path, "rb") as fh:
        r = requests.post(
            f"{BASE}/ocr",
            headers=H,
            data={"model": model, "prompt": prompt or OCR_PROMPT},
            files={"file": (os.path.basename(file_path), fh, mime)},
            timeout=300,
        )
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if not (data.get("text") or "").strip():
        print("uyarı: OCR boş metin döndü (görselde okunacak yazı yok veya model halüsine etti)")
    return data


# ---------------------------------------------------------------- guard (kısıtlı)

GUARD_NOTE = """qwen3-guard-4b şu an KULLANILAMIYOR (canlı test edilmiştir):
  - POST /v1/guard            -> 404 (uç yok)
  - POST /v1/chat/completions -> 400 "bu model sohbet ucunu desteklemiyor (görev: guard)"
Guard çağrısı sunucu tarafında Wave-2'de açılacak görünüyor; o zam dek bu
modeli chat/vision/ocr/embeddings gibi uçlarda kullanamazsınız."""


def guard_note() -> None:
    """qwen3-guard-4b kullanım durumunu yazdır."""
    print(GUARD_NOTE)


# ---------------------------------------------------------------- CLI

COMMANDS = {
    "terms_status": terms_status,
    "terms_text": terms_text,
    "accept_terms": accept_terms,
    "ensure_terms": ensure_terms,
    "list_models": list_models,
    "chat": chat,
    "stream": stream,
    "repl": repl,
    "vision": vision,
    "embeddings": embeddings,
    "rerank": rerank,
    "transcribe": transcribe,
    "ocr": ocr,
    "guard_note": guard_note,
}

HELP = """kullanım: python main.py <komut> [argümanlar] [seçenekler]

  list_models                     modelleri listele
  repl                            sürekli sohbet (menülü model seçimi)
  chat ["prompt"]                 tek sohbet
  stream ["prompt"]               akışlı sohbet
  vision ["soru"] [görsel]        görsel sorusu (qwen3-vl-30b)
  embeddings "metin" ["metin2" ...]  vektör (qwen3-embedding-8b)
  rerank "sorgu" [--docs ...]     yeniden sırala (qwen3-reranker-8b)
  transcribe [dosya]              ses -> metin (qwen3-asr-1.7b)
  ocr [dosya]                     belge/görsel -> metin (dots-ocr)
  guard_note                      qwen3-guard-4b durumu (şu an kapalı)
  terms_status | terms_text | accept_terms

seçenekler:
  -m, --model <id>     model seç (örn: -m glm-5.3)
  --prompt <metin>     ocr yönergesi (varsayılan: metni aynen çıkar)
  --lang <kod>         transcribe dili (varsayılan tr)
  --format <biçim>     transcribe: json|text|srt|verbose_json|diarized_json
  --docs "b1" "b2"     rerank belgeleri (birden çok değer alır)
  --docs-file <dosya>  rerank: .txt (her satır bir belge) | .json (dizi)

örnekler:
  python main.py chat "Merhaba" -m glm-5.3
  python main.py vision "Bu resimde ne var?" test_gorsel.png
  python main.py ocr test_fatura.png
  python main.py transcribe test_ses.wav --lang tr --format json
  python main.py embeddings "kedi" "köpek"
  python main.py rerank "kedi" --docs "kedi hayvandır" "araba hızlıdır"
  python main.py rerank "fatura" --docs-file test_belgeler.txt

not: ocr için belge görseli ver (fatura/sayfa). Az yazılı görselde model
     halüsine edebilir. deepseek-ocr-2 testlerde kullanılabilir sonuç vermedi.
"""


def _parse(argv: list) -> tuple:
    """Argümanlardan (positional, opts) çıkar."""
    opts = {"model": None, "language": None, "response_format": None,
            "prompt": None, "docs": [], "docs_file": None}
    positional = []
    i = 0
    while i < len(argv):
        if argv[i] in ("-m", "--model"):
            if i + 1 >= len(argv):
                raise SystemExit("hata: -m için model id gerekli")
            opts["model"] = argv[i + 1]
            i += 2
        elif argv[i] == "--lang":
            if i + 1 >= len(argv):
                raise SystemExit("hata: --lang için dil kodu gerekli")
            opts["language"] = argv[i + 1]
            i += 2
        elif argv[i] == "--format":
            if i + 1 >= len(argv):
                raise SystemExit("hata: --format için biçim gerekli")
            opts["response_format"] = argv[i + 1]
            i += 2
        elif argv[i] == "--prompt":
            if i + 1 >= len(argv):
                raise SystemExit("hata: --prompt için metin gerekli")
            opts["prompt"] = argv[i + 1]
            i += 2
        elif argv[i] in ("--docs", "--documents"):
            i += 1
            start = i
            while i < len(argv) and not argv[i].startswith("-"):
                opts["docs"].append(argv[i])
                i += 1
            if i == start:
                raise SystemExit("hata: --docs için en az bir belge gerekli")
        elif argv[i] in ("--docs-file", "--documents-file"):
            if i + 1 >= len(argv):
                raise SystemExit("hata: --docs-file için dosya yolu gerekli")
            opts["docs_file"] = argv[i + 1]
            i += 2
        else:
            positional.append(argv[i])
            i += 1
    return positional, opts


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(HELP)
        sys.exit(0 if len(sys.argv) > 1 else 1)

    command = sys.argv[1]
    if command not in COMMANDS:
        print(f"bilinmeyen komut: {command}\n")
        print(HELP)
        sys.exit(1)

    args, opts = _parse(sys.argv[2:])
    model = opts["model"]

    if command in ("chat", "stream", "repl"):
        COMMANDS[command](*args, model=model)
    elif command == "transcribe":
        kw = {}
        if model:
            kw["model"] = model
        if opts["language"] is not None:
            kw["language"] = opts["language"]
        if opts["response_format"]:
            kw["response_format"] = opts["response_format"]
        COMMANDS[command](*args, **kw)
    elif command == "ocr":
        kw = {}
        if model:
            kw["model"] = model
        if opts["prompt"]:
            kw["prompt"] = opts["prompt"]
        COMMANDS[command](*args, **kw)
    elif command == "rerank":
        kw = {}
        if model:
            kw["model"] = model
        if opts["docs"]:
            kw["documents"] = opts["docs"]
        if opts["docs_file"]:
            kw["docs_file"] = opts["docs_file"]
        query = args[0] if args else None
        COMMANDS[command](query, **kw)
    elif command == "embeddings":
        kw = {"model": model} if model else {}
        if len(args) > 1:
            COMMANDS[command](list(args), **kw)
        elif args:
            COMMANDS[command](args[0], **kw)
        else:
            COMMANDS[command](**kw)
    elif model:
        COMMANDS[command](*args, model=model)
    else:
        COMMANDS[command](*args)
