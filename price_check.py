import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

PRODUCT = {
    "name": "Colorful RTX 5070 Ti",
    "query": "Colorful RTX 5070 Ti",
    "target_price": 50000,
    "include": ["colorful", "5070", "ti"],
    "exclude": [
        "5070 sistem",
        "5070 ti sistem",
        "hazır sistem",
        "hazir sistem",
        "oyuncu bilgisayarı",
        "oyuncu bilgisayari",
        "gaming pc",
        "laptop",
        "notebook",
        "ikinci el",
        "2.el",
        "2 el",
        "5080",
        "5070 super"
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


def parse_price(price_text):
    price_text = str(price_text)
    price_text = price_text.replace("₺", "")
    price_text = price_text.replace("TL", "")
    price_text = price_text.replace("tl", "")
    price_text = price_text.strip()

    # 49.999,00 -> 49999.00
    price_text = price_text.replace(".", "").replace(",", ".")

    nums = re.findall(r"\d+(?:\.\d+)?", price_text)

    if not nums:
        return None

    try:
        return float(nums[0])
    except Exception:
        return None


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
            if price and 1000 <= price <= 300000:
                found.append((price, match))

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


def check_store(store):
    query = quote_plus(PRODUCT["query"])
    url = store["search_url"].format(query=query)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        r = requests.get(url, headers=headers, timeout=25)
        r.raise_for_status()
    except Exception as e:
        print(f"{store['name']} hata: {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    for bad in soup(["script", "style", "noscript"]):
        bad.decompose()

    page_text = soup.get_text(" ", strip=True)

    if not product_matches(page_text):
        print(f"{store['name']}: ürün kelimeleri eşleşmedi")
        return None

    prices = extract_prices(page_text)

    if not prices:
        print(f"{store['name']}: fiyat bulunamadı")
        return None

    cheapest = min(prices, key=lambda x: x[0])

    return {
        "store": store["name"],
        "url": url,
        "price": cheapest[0],
        "price_text": cheapest[1]
    }


def main():
    matches = []
    checked_store_names = []

    for store in STORES:
        checked_store_names.append(store["name"])

        result = check_store(store)

        if result:
            matches.append(result)
            print(result)

    if not matches:
        send_telegram(
            "⚠️ Colorful RTX 5070 Ti kontrol edildi ama uygun fiyat/sonuç bulunamadı.\n\n"
            "Kontrol edilen mağazalar:\n"
            + "\n".join(f"- {name}" for name in checked_store_names)
            + "\n\nBu ilk ücretsiz bot sürümü. Bazı mağazalar bot engeli veya farklı sayfa yapısı nedeniyle ayrı düzeltme isteyebilir."
        )
        return

    cheapest = min(matches, key=lambda x: x["price"])

    all_results = "\n".join(
        f"- {item['store']}: {item['price_text']}"
        for item in sorted(matches, key=lambda x: x["price"])
    )

    if cheapest["price"] <= PRODUCT["target_price"]:
        send_telegram(
            "🔥 Hedef fiyat altı veya eşit ürün bulundu!\n\n"
            f"Ürün: {PRODUCT['name']}\n"
            f"Hedef fiyat: {PRODUCT['target_price']:,.0f} TL\n"
            f"Bulunan fiyat: {cheapest['price_text']}\n"
            f"Mağaza: {cheapest['store']}\n\n"
            f"Link:\n{cheapest['url']}\n\n"
            f"Bulunan diğer sonuçlar:\n{all_results}"
        )
    else:
        send_telegram(
            "📊 Fiyat kontrolü tamamlandı.\n\n"
            f"Ürün: {PRODUCT['name']}\n"
            f"En düşük görünen fiyat: {cheapest['price_text']}\n"
            f"Mağaza: {cheapest['store']}\n"
            f"Hedef: {PRODUCT['target_price']:,.0f} TL\n\n"
            f"Link:\n{cheapest['url']}\n\n"
            f"Bulunan sonuçlar:\n{all_results}"
        )


if __name__ == "__main__":
    main()
