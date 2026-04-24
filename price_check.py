import os
import re
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "state.json"

PRODUCT = {
    "name": "Colorful RTX 5070 Ti",
    "query": "Colorful RTX 5070 Ti",
    "target_price": 50000,
    "include": ["colorful", "5070", "ti"],
    "exclude": [
        "hazır sistem",
        "hazir sistem",
        "oyuncu bilgisayarı",
        "oyuncu bilgisayari",
        "gaming pc",
        "sistem",
        "laptop",
        "notebook",
        "ikinci el",
        "2.el",
        "2 el",
        "5080",
        "5070 super",
        "rtx 5070 12gb"
    ]
}

STORES = [
    {
        "name": "Gaming.gen.tr",
        "search_url": "https://www.gaming.gen.tr/?s={query}&post_type=product"
    },
    {
        "name": "İncehesap",
        "search_url": "https://www.incehesap.com/arama/?q={query}"
    },
    {
        "name": "Sinerji",
        "search_url": "https://www.sinerji.gen.tr/arama?kelime={query}"
    },
    {
        "name": "İtopya",
        "search_url": "https://www.itopya.com/arama/{query}/"
    },
    {
        "name": "Teknobiyotik",
        "search_url": "https://www.teknobiyotik.com/catalogsearch/result/?q={query}"
    },
    {
        "name": "Vatan Bilgisayar",
        "search_url": "https://www.vatanbilgisayar.com/arama/{query}"
    },
    {
        "name": "Inventus",
        "search_url": "https://inventus.com.tr/mi_products/ProductList.aspx?text={query}"
    },
    {
        "name": "GameGaraj",
        "search_url": "https://www.gamegaraj.com/?s={query}&post_type=product"
    },
    {
        "name": "Ebrar Bilgisayar",
        "search_url": "https://www.ebrarbilgisayar.com/arama?search={query}"
    },
    {
        "name": "PcKolik",
        "search_url": "https://pckolik.com.tr/arama?search={query}"
    },
    {
        "name": "Amazon Türkiye",
        "search_url": "https://www.amazon.com.tr/s?k={query}"
    },
    {
        "name": "Hepsiburada",
        "search_url": "https://www.hepsiburada.com/ara?q={query}"
    },
    {
        "name": "N11",
        "search_url": "https://www.n11.com/arama?q={query}"
    },
    {
        "name": "Trendyol",
        "search_url": "https://www.trendyol.com/sr?q={query}"
    },
    {
        "name": "Pazarama",
        "search_url": "https://www.pazarama.com/arama?q={query}"
    }
]


def normalize(text):
    text = str(text).lower()
    text = text.replace("ı", "i").replace("İ", "i")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def parse_price(price_text):
    raw = str(price_text)
    raw = raw.replace("₺", "")
    raw = raw.replace("TL", "")
    raw = raw.replace("tl", "")
    raw = raw.strip()

    raw = raw.replace(".", "").replace(",", ".")

    nums = re.findall(r"\d+(?:\.\d+)?", raw)

    if not nums:
        return None

    try:
        price = float(nums[0])
    except Exception:
        return None

    if price < 1000 or price > 300000:
        return None

    return price


def extract_prices(text):
    patterns = [
        r"\d{1,3}(?:\.\d{3})+(?:,\d{2})?\s*TL",
        r"\d{4,6}(?:,\d{2})?\s*TL",
        r"₺\s*\d{1,3}(?:\.\d{3})+(?:,\d{2})?",
        r"₺\s*\d{4,6}(?:,\d{2})?"
    ]

    found = []

    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            price = parse_price(match)
            if price:
                found.append({
                    "price": price,
                    "price_text": match.strip()
                })

    return found


def product_matches(text):
    t = normalize(text)

    for word in PRODUCT["include"]:
        if normalize(word) not in t:
            return False

    for word in PRODUCT["exclude"]:
        if normalize(word) in t:
            return False

    return True


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False
    }

    response = requests.post(url, data=data, timeout=20)

    if response.status_code != 200:
        print("Telegram mesaj hatası:", response.text)


def fetch_store(store):
    query = quote_plus(PRODUCT["query"])
    url = store["search_url"].format(query=query)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        response = requests.get(url, headers=headers, timeout=25)
        response.raise_for_status()
    except Exception as e:
        print(f"{store['name']} hata: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    for bad in soup(["script", "style", "noscript"]):
        bad.decompose()

    page_text = soup.get_text(" ", strip=True)

    if not product_matches(page_text):
        print(f"{store['name']}: ürün eşleşmedi")
        return None

    prices = extract_prices(page_text)

    if not prices:
        print(f"{store['name']}: fiyat bulunamadı")
        return None

    cheapest = min(prices, key=lambda item: item["price"])

    return {
        "store": store["name"],
        "url": url,
        "price": cheapest["price"],
        "price_text": cheapest["price_text"]
    }


def build_alert_key(result):
    raw = f"{PRODUCT['name']}|{result['store']}|{result['price']}|{result['url']}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main():
    state = load_state()
    results = []

    for store in STORES:
        result = fetch_store(store)
        if result:
            results.append(result)

    if not results:
        print("Ürün bulunamadı. Telegram mesajı gönderilmiyor.")
        return

    cheapest = min(results, key=lambda item: item["price"])

    print("En düşük bulunan sonuç:")
    print(cheapest)

    if cheapest["price"] > PRODUCT["target_price"]:
        print("Fiyat hedefin üstünde. Telegram mesajı gönderilmiyor.")
        return

    alert_key = build_alert_key(cheapest)
    last_alert_key = state.get(PRODUCT["name"], {}).get("last_alert_key")

    if alert_key == last_alert_key:
        print("Bu fiyat daha önce bildirildi. Tekrar mesaj gönderilmiyor.")
        return

    sorted_results = sorted(results, key=lambda item: item["price"])

    other_results = "\n".join(
        f"- {item['store']}: {item['price_text']}"
        for item in sorted_results[:5]
    )

    message = (
        "🔥 Hedef fiyat yakalandı!\n\n"
        f"Ürün: {PRODUCT['name']}\n"
        f"Hedef fiyat: {PRODUCT['target_price']:,.0f} TL\n"
        f"Bulunan fiyat: {cheapest['price_text']}\n"
        f"Mağaza: {cheapest['store']}\n\n"
        f"Link:\n{cheapest['url']}\n\n"
        f"Bulunan diğer sonuçlar:\n{other_results}"
    )

    send_telegram(message)

    state[PRODUCT["name"]] = {
        "last_alert_key": alert_key,
        "last_price": cheapest["price"],
        "last_store": cheapest["store"],
        "last_url": cheapest["url"]
    }

    save_state(state)


if __name__ == "__main__":
    main()
