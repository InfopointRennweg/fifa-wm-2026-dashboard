import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re

# ============================================================
# FIFA WM 2026 Dashboard — Scraper
# Quellen: SRF Sport Fussball (News) + worldcup26.ir (Spielplan)
# ============================================================

# SRF Fussball News-Seite (wird auf WM-Unterseite aktualisiert, sobald verfügbar)
NEWS_URLS = [
    "https://www.srf.ch/sport/fussball/wm",       # WM-spezifische Seite (sobald verfügbar)
    "https://www.srf.ch/sport/fussball/fifa-wm-2026",  # Alternative URL
    "https://www.srf.ch/sport/fussball"            # Fallback: allgemeine Fussball-Seite
]

# Mapping: Englischer Teamname → ISO 3166-1 Alpha-2 Ländercode (für Flaggen)
COUNTRY_CODES = {
    "Switzerland": "ch", "Canada": "ca", "Qatar": "qa",
    "Bosnia and Herzegovina": "ba", "Mexico": "mx", "South Africa": "za",
    "South Korea": "kr", "Czech Republic": "cz", "Brazil": "br",
    "Morocco": "ma", "Haiti": "ht", "Scotland": "gb-sct",
    "United States": "us", "Paraguay": "py", "Australia": "au",
    "Turkey": "tr", "Germany": "de", "Curaçao": "cw",
    "Ivory Coast": "ci", "Ecuador": "ec", "Netherlands": "nl",
    "Japan": "jp", "Sweden": "se", "Tunisia": "tn",
    "Belgium": "be", "Egypt": "eg", "Iran": "ir",
    "New Zealand": "nz", "Spain": "es", "Cape Verde": "cv",
    "Saudi Arabia": "sa", "Uruguay": "uy", "France": "fr",
    "Senegal": "sn", "Iraq": "iq", "Norway": "no",
    "Argentina": "ar", "Algeria": "dz", "Austria": "at",
    "Jordan": "jo", "Portugal": "pt",
    "Democratic Republic of the Congo": "cd",
    "Uzbekistan": "uz", "Colombia": "co", "England": "gb-eng",
    "Croatia": "hr", "Ghana": "gh", "Panama": "pa",
}

# Mapping: Englischer Teamname → Deutscher Teamname
TEAM_NAMES_DE = {
    "Switzerland": "Schweiz", "Canada": "Kanada", "Qatar": "Katar",
    "Bosnia and Herzegovina": "Bosnien-Herzeg.", "Mexico": "Mexiko",
    "South Africa": "Südafrika", "South Korea": "Südkorea",
    "Czech Republic": "Tschechien", "Brazil": "Brasilien",
    "Morocco": "Marokko", "Haiti": "Haiti", "Scotland": "Schottland",
    "United States": "USA", "Paraguay": "Paraguay", "Australia": "Australien",
    "Turkey": "Türkei", "Germany": "Deutschland", "Curaçao": "Curaçao",
    "Ivory Coast": "Elfenbeinküste", "Ecuador": "Ecuador",
    "Netherlands": "Niederlande", "Japan": "Japan", "Sweden": "Schweden",
    "Tunisia": "Tunesien", "Belgium": "Belgien", "Egypt": "Ägypten",
    "Iran": "Iran", "New Zealand": "Neuseeland", "Spain": "Spanien",
    "Cape Verde": "Kap Verde", "Saudi Arabia": "Saudi-Arabien",
    "Uruguay": "Uruguay", "France": "Frankreich", "Senegal": "Senegal",
    "Iraq": "Irak", "Norway": "Norwegen", "Argentina": "Argentinien",
    "Algeria": "Algerien", "Austria": "Österreich", "Jordan": "Jordanien",
    "Portugal": "Portugal", "Democratic Republic of the Congo": "DR Kongo",
    "Uzbekistan": "Usbekistan", "Colombia": "Kolumbien",
    "England": "England", "Croatia": "Kroatien", "Ghana": "Ghana",
    "Panama": "Panama",
}


def scrape_news():
    """Scrape die neuesten Fussball-WM-News von SRF Sport."""
    for url in NEWS_URLS:
        try:
            print(f"  Versuche News von: {url}")
            response = requests.get(url, timeout=15)
            
            # Wenn die Seite nicht existiert (404), nächste URL probieren
            if response.status_code == 404:
                print(f"  [SKIPPED] 404, ueberspringe...")
                continue
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            news_list = []

            # Alle Teaser-Artikel auf der Seite finden
            teasers = [a for a in soup.find_all('a') 
                       if a.get('href') and '/sport/fussball' in a.get('href') 
                       and 'teaser' in a.get('class', [])]

            for t in teasers:
                # Titel und Kicker (Über-Titel) auslesen
                kicker_el = t.find(class_='teaser__kicker-text')
                title_el = t.find(class_='teaser__title')

                kicker = kicker_el.text.strip() if kicker_el else ""
                title = title_el.text.strip() if title_el else ""

                full_title = f"{kicker} - {title}" if kicker and title else (title or kicker or "Kein Titel")

                # Bild URL auslesen
                image_url = ""
                img = t.find('img')
                if img is not None:
                    image_url = img.get('src') or img.get('data-src') or ""
                    if image_url.startswith('/'):
                        image_url = f"https://www.srf.ch{image_url}"

                # Veröffentlichungsdatum
                pub_date = "Aktuell"
                meta = t.find(class_='teaser__meta')
                if meta is not None:
                    published_at = meta.get('data-teaser-meta-published-at')
                    if published_at:
                        try:
                            date_str = published_at[:10]
                            dt = datetime.strptime(date_str, "%Y-%m-%d")
                            pub_date = dt.strftime("%d.%m.%Y")
                        except:
                            pass

                news_list.append({
                    "title": full_title,
                    "date": pub_date,
                    "image": image_url
                })

                # Max. 2 News-Artikel
                if len(news_list) >= 2:
                    break

            if news_list:
                print(f"  [OK] {len(news_list)} News gefunden auf {url}")
                return news_list
            else:
                print(f"  [SKIP] Keine passenden Teaser gefunden, naechste URL...")
                continue

        except Exception as e:
            print(f"  Fehler bei {url}: {e}")
            continue

    # Fallback: Keine News gefunden
    print("  [WARN] Keine News gefunden, verwende Fallback.")
    return [{"title": "Keine WM-News auf SRF gefunden.", "date": datetime.now().strftime("%d.%m.%Y"), "image": ""}]


def convert_et_to_mesz(date_str):
    """Konvertiert US Eastern Time (ET) zu Mitteleuropäischer Sommerzeit (MESZ).
    Eingabe: 'MM/DD/YYYY HH:MM' (ET = UTC-4 im Sommer)
    MESZ = UTC+2, also +6 Stunden zu ET.
    """
    try:
        dt = datetime.strptime(date_str, "%m/%d/%Y %H:%M")
        dt_mesz = dt + timedelta(hours=6)  # ET (UTC-4) → MESZ (UTC+2) = +6h
        return dt_mesz
    except:
        return None


def scrape_schedule():
    """Lade den WM-Spielplan über die offizielle SRF/SwissTXT API."""
    try:
        print("  [SPIELPLAN] Lade Spielplan von SRF/SwissTXT API...")
        # HINWEIS: Die genaue phaseId für die FIFA WM 2026 wird von SRF kurz vor Turnierbeginn aktiviert.
        # Dies ist die Architektur, die auch das Hockey-Dashboard verwendet.
        url = "https://sport.api.swisstxt.ch/v1/eventItems?phaseIds=9999-999&lang=de"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        raw_games = response.json()
        
        all_games = []
        for g in raw_games:
            # 1. Teams & Länder extrahieren
            c1 = g.get("competitor1", {})
            c2 = g.get("competitor2", {})
            
            t1 = c1.get("name", "Unbekannt")
            t1_country = c1.get("country", "")
            t2 = c2.get("name", "Unbekannt")
            t2_country = c2.get("country", "")
            
            # 2. Datum & Uhrzeit
            dt_info = g.get("dateTimeInfo", {})
            full_date = dt_info.get("fullDateTime", "")
            time_str = dt_info.get("time", "")
            
            date_str = ""
            if full_date:
                try:
                    dt = datetime.strptime(full_date[:19], "%Y-%m-%dT%H:%M:%S")
                    weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
                    months = ["Jan", "Feb", "März", "April", "Mai", "Juni", "Juli", "Aug", "Sept", "Okt", "Nov", "Dez"]
                    date_str = f"{weekdays[dt.weekday()]}, {dt.day}. {months[dt.month-1]}"
                except:
                    date_str = dt_info.get("date", "")
            else:
                date_str = dt_info.get("date", "")
                
            # 3. Match Details
            venue = g.get("stadium", "Gruppe")
            state = g.get("state", "Planned")
            
            main_score = g.get("scores", {}).get("main", {})
            score = main_score.get("formatted", "- : -")
            if score == "- : -":
                score = None
                
            all_games.append({
                "team1": t1,
                "team1_country": t1_country,
                "team2": t2,
                "team2_country": t2_country,
                "date_str": date_str,
                "time": time_str,
                "venue": venue,
                "state": state,
                "score": score,
                "full_date": full_date
            })
            
        if len(all_games) == 0:
            raise ValueError("API gab eine leere Liste zurück (PhaseId nicht aktiv).")
            
        print(f"  [OK] {len(all_games)} Spiele von SRF geladen")
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_games = [g for g in all_games if g.get("full_date", "").startswith(today_str)]
        
        if not today_games:
            future_games = [g for g in all_games if g.get("full_date", "") > today_str]
            if future_games:
                next_date_str = min(g.get("full_date", "")[:10] for g in future_games)
                today_games = [g for g in all_games if g.get("full_date", "").startswith(next_date_str)]
                
        today_games.sort(key=lambda x: x.get("full_date", ""))
        
        past_results = [g for g in all_games if g["state"] == "Finished"]
        past_results.sort(key=lambda x: x.get("full_date", ""), reverse=True)

        swiss_games = [g for g in all_games if g["team1"] == "Schweiz" or g["team2"] == "Schweiz"]
        swiss_games.sort(key=lambda x: x.get("full_date", ""))
        
        return {
            "today_games": today_games,
            "past_results": past_results[:8],
            "swiss_games": swiss_games
        }
        
    except Exception as e:
        print(f"  [WARN] SRF Spielplan noch nicht verfuegbar oder API Fehler: {e}")
        print("  [WARN] Verwende interne SRF-Fallback-Daten für die Gruppenphase.")
        # Sichere Rückfalldaten, bis das Turnier startet und die SRF API die Daten liefert
        return {
            "today_games": [
                {"team1": "Katar", "team1_country": "qa", "team2": "Schweiz", "team2_country": "ch",
                 "date_str": "Sa, 13. Juni", "time": "18:00", "venue": "Gruppe B",
                 "state": "Planned", "score": None, "full_date": "2026-06-13T18:00:00",
                 "group": "B", "type": "group"}
            ],
            "past_results": [],
            "swiss_games": [
                {"team1": "Katar", "team1_country": "qa", "team2": "Schweiz", "team2_country": "ch",
                 "date_str": "Sa, 13. Juni", "time": "18:00", "venue": "Gruppe B",
                 "state": "Planned", "score": None, "full_date": "2026-06-13T18:00:00",
                 "group": "B", "type": "group"},
                {"team1": "Schweiz", "team1_country": "ch", "team2": "Bosnien-Herzeg.", "team2_country": "ba",
                 "date_str": "Do, 18. Juni", "time": "18:00", "venue": "Gruppe B",
                 "state": "Planned", "score": None, "full_date": "2026-06-18T18:00:00",
                 "group": "B", "type": "group"},
                {"team1": "Schweiz", "team1_country": "ch", "team2": "Kanada", "team2_country": "ca",
                 "date_str": "Mi, 24. Juni", "time": "18:00", "venue": "Gruppe B",
                 "state": "Planned", "score": None, "full_date": "2026-06-24T18:00:00",
                 "group": "B", "type": "group"}
            ]
        }


if __name__ == "__main__":
    print("=" * 50)
    print("FIFA WM 2026 Dashboard - Scraper")
    print("=" * 50)
    
    print("\n[NEWS] Lade SRF Fussball News...")
    news = scrape_news()
    
    print("\n[SPIELPLAN] Lade WM-Spielplan...")
    schedule = scrape_schedule()
    
    # Countdown-Ziel: Eröffnungsspiel am 11. Juni 2026, 19:00 MESZ
    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "countdown_target": "2026-06-11T19:00:00",
        "news": news,
        "schedule": schedule
    }
    
    with open("data.js", "w", encoding="utf-8") as f:
        f.write("const dashboardData = ")
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write(";")
    
    print(f"\n[OK] data.js erfolgreich erstellt!")
    print(f"  News: {len(news)} Artikel")
    print(f"  Spiele heute/naechster Spieltag: {len(schedule['today_games'])}")
    print(f"  Abgeschlossene Spiele: {len(schedule['past_results'])}")
    print(f"  Schweizer Spiele: {len(schedule['swiss_games'])}")

