from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import time

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["articles360DB"]
collection = db["articles360"]


def init_driver():
    """Initialise le WebDriver avec Chrome ou Firefox si Chrome échoue."""
    driver = None
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(service=ChromeService(
            ChromeDriverManager().install()), options=chrome_options)
        print("[INFO] Navigateur : Chrome")
    except Exception as e:
        print(f"[ERREUR] Chrome a échoué : {e}\n[INFO] Passage à Firefox...")
        try:
            firefox_options = webdriver.FirefoxOptions()
            firefox_options.add_argument("--headless")
            driver = webdriver.Firefox(service=FirefoxService(
                GeckoDriverManager().install()), options=firefox_options)
            print("[INFO] Navigateur : Firefox")
        except Exception as e:
            print(
                f"[ERREUR] Firefox a aussi échoué : {e}\n[CRITIQUE] Aucun navigateur disponible.")
            return None
    return driver


def scrape_le360():
    """Scrape les liens des articles depuis les pages principales."""
    urls = [
        "https://fr.le360.ma/societe", "https://fr.le360.ma/politique", "https://fr.le360.ma/economie",
        "https://fr.le360.ma/sport", "https://fr.le360.ma/culture", "https://fr.le360.ma/monde",
        "https://fr.le360.ma/medias", "https://fr.le360.ma/regions", "https://fr.le360.ma/insolite",
        "https://fr.le360.ma/afrique", "https://fr.le360.ma/education", "https://fr.le360.ma/religion",
        "https://fr.le360.ma/sciences", "https://fr.le360.ma/technologie", "https://fr.le360.ma/sante",
        "https://fr.le360.ma/enquetes", "https://fr.le360.ma/immobilier", "https://fr.le360.ma/entreprise",
        "https://fr.le360.ma/energie", "https://fr.le360.ma/agriculture", "https://fr.le360.ma/transport",
        "https://fr.le360.ma/environnement", "https://fr.le360.ma/tourisme", "https://fr.le360.ma/emploi",
        "https://fr.le360.ma/formation", "https://fr.le360.ma/entreprenariat", "https://fr.le360.ma/finance",
        "https://fr.le360.ma/assurances", "https://fr.le360.ma/bourse", "https://fr.le360.ma/immobilier",
        "https://fr.le360.ma/automobile", "https://fr.le360.ma/industrie", "https://fr.le360.ma/telecom",
        "https://fr.le360.ma/medias", "https://fr.le360.ma/energie", "https://fr.le360.ma/agriculture",
        "https://fr.le360.ma/tourisme", "https://fr.le360.ma/international", "https://fr.le360.ma/medias"
    ]
    
    driver = init_driver()
    if not driver:
        return []

    articles = []
    for url in urls:
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.article-list--headline-container")))
        except Exception as e:
            print(f"[ERREUR] Aucun article détecté sur {url} : {e}")
            continue

        elements = driver.find_elements(By.CSS_SELECTOR, "div.ssa-list-item")[:20]  # 20 premiers articles

        for element in elements:
            try:
                link_element = element.find_element(By.TAG_NAME, "a")
                title = link_element.text.strip()
                article_url = link_element.get_attribute("href")

                image_element = element.find_element(By.CSS_SELECTOR, "div.custom-image-wrapper img")
                image_url = image_element.get_attribute("src") if image_element else "Aucune image"

                articles.append({
                    "title": title,
                    "url": article_url,
                    "image": image_url
                })
            except Exception as e:
                print(f"[ERREUR] Problème avec un article sur {url} : {e}")

    driver.quit()
    return articles


def scrape_article(url):
    """Scrape le contenu détaillé d'un article."""
    driver = init_driver()
    if not driver:
        return None

    driver.get(url)
    time.sleep(15)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    category = soup.select_one("div.overline-container a.overline-link")
    title = soup.select_one("h1.headline-container")
    paragraphs = soup.select(
        "p.default__StyledText-sc-10mj2vp-0.fSEbof.body-paragraph")
    date_published = soup.select_one("div.subheadline-date")

    article_data = {
        "category": category.text.strip() if category else "N/A",
        "title": title.text.strip() if title else "N/A",
        "content": "\n".join(p.text.strip() for p in paragraphs if p.text.strip()),
        "url": url,
        "published_at": date_published.text.strip() if date_published else "N/A",
        "scraped_at": datetime.now()
    }

    driver.quit()
    return article_data


def store_article(article):
    """Stocke l'article dans MongoDB en évitant les doublons."""
    if not collection.find_one({"url": article["url"]}):  # Vérifie si l'article est déjà stocké
        collection.insert_one(article)
        print(f"[✅] Article ajouté : {article['title']}")
    else:
        print(f"[⚠️] Article déjà existant : {article['title']}")


if __name__ == "__main__":
    scraped_articles = scrape_le360()
    for article in scraped_articles:
        article_data = scrape_article(article["url"])
        if article_data:
            store_article(article_data)
