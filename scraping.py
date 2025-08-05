from bs4 import BeautifulSoup
import requests
from time import sleep

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }  


def filmTitle(data, last_entry):
    title_name = data.find("a")
    if title_name and title_name.string:
        if last_entry and title_name.string == last_entry:
            return False
        else:
            return title_name.string
    return False

def filmImage(data):
    img_tag = data.find("img")
    print(img_tag["src"])

def filmRelease(data):
    release_year = data.find("span")
    if release_year:
        return release_year.string

def filmRating(data):
    # user_rating_star = data.find("span")
    user_rating_number = data.find("input")
    if user_rating_number:
        return user_rating_number["value"]
    else:
        return False

def filmReview(data):
    if "icon-status-off" in data.get("class", []):
        return False
    else:
        partial_url = data.find("a")
        full_url = f"https://letterboxd.com{partial_url["href"]}"
        return full_url
    

def scrapeSite(profile):
    url = f"https://letterboxd.com/{profile}/films/diary/"
    try:
        result = requests.get(url, headers=headers)
        doc = BeautifulSoup(result.text, "html.parser")
        # with open("index.html", "w") as file:
            # file.write(result.text)
        # with open("index.html", "r") as file:
        #     doc = BeautifulSoup(file, "html.parser")
        user = doc.find(["title"])
        print((user.string.split("’")[0]).strip())
    except Exception as e:
        print(e)
        return -1
    
    tbody = doc.tbody
    trs = tbody.find_all("tr")
    for tr in trs:
        date, details, released, rating, like, rewatch, review = tr.find_all("td")[1:8]
        filmTitle(details)
        filmRelease(released)
        filmRating(rating)
        filmReview(review)
        filmImage(details)
        print()

# Initial scrape when a new user is added
# Also is used as a verification if the added username exist on Letterboxd
def firstScrape(profile):
    url = f"https://letterboxd.com/{profile}/films/diary/"
    UNMATCHABLE_TITLE = "__UNMATCHABLE__"
    try:
        result = requests.get(url, headers=headers)
        if result.status_code != 200:
                print(f"Failed to fetch page (status {result.status_code})")
                return False
        doc = BeautifulSoup(result.text, "html.parser")
        user = doc.find(["title"])
        if not user or "not found" in user.text.lower():
            print(f"Invalid or non-existent user: {profile}")
            return False
        tbody = doc.tbody
        if tbody:
            trs = tbody.find_all("tr")
            date, details, released, rating, like, rewatch, review = trs[0].find_all("td")[1:8]
            film_title = filmTitle(details, UNMATCHABLE_TITLE)
            film_release = filmRelease(released)
            film_rating = filmRating(rating)
            film_review = filmReview(review)
            #filmImage(details)
            return True, film_title, film_release, film_rating, film_review
        else:
            return "no_entry"
    except Exception as e:
        print(f"Error retrieving {profile} info: ", e)
        return False
    
def diaryScrape(profile, entry):
    url = f"https://letterboxd.com/{profile}/films/diary/"
    film_title = []
    film_release = []
    film_rating = []
    film_review = []
    #sleep(5.0) 

    try:
        result = requests.get(url, headers=headers)
        if result.status_code != 200:
                print(f"Failed to fetch page (status {result.status_code})")
                return False
        doc = BeautifulSoup(result.text, "html.parser")
        user = doc.find(["title"])
        if not user or "not found" in user.text.lower():
            print(f"Invalid or non-existent user: {profile}")
            return False
        
        tbody = doc.tbody
        first = True
        if tbody:
            trs = tbody.find_all("tr")[:5]
            for tr in trs:
                date, details, released, rating, like, rewatch, review = tr.find_all("td")[1:8]
                title = filmTitle(details, entry)
                if not title:
                    if first:
                        #print("No new entries", profile)
                        return False
                    else:
                        break
                first = False
                
                film_title.append(title)
                film_release.append(filmRelease(released))
                film_rating.append(filmRating(rating))
                film_review.append(filmReview(review))
                #filmImage(details)
                
            return True, film_title, film_release, film_rating, film_review
        else:
            return False
        
    except Exception as e:
        print(f"Error retrieving {profile} info: ", e)
        return False

    
def favoriteFilmsScrape(profile):
    url = f"https://letterboxd.com/{profile}/"
    titles = []

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
                print(f"Failed to fetch page (status {response.status_code})")
                return False

        doc = BeautifulSoup(response.text, "html.parser")

        section = doc.find("section", id="favourites")
        if not section:
            print("Couldn't find section")
            return False
        
        ulist = section.find("ul")
        if not ulist:
            return "No favorites"
        else:
            if ulist:
                list_items = ulist.find_all("li", class_="poster-container favourite-film-poster-container")
                for item in list_items:
                    img = item.find("img")
                    title = img["alt"]
                    titles.append(title)
        
    except Exception as e:
            print(f"Error scraping page {url}: {e}")
            return False

    return titles

    
def watchlistScrape(profile):
    base_url = f"https://letterboxd.com/{profile}/watchlist"
    page = 1
    titles = []

    while True:
        url = f"{base_url}/page/{page}/" if page > 1 else base_url
        print(f"Scraping page {page} for {profile}...")

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to fetch page {page} (status {response.status_code})")
                break
            with open("raw_watchlist.html", "w+", encoding="utf-8") as f:
                f.write(response.text)

            doc = BeautifulSoup(response.text, "html.parser")
            
            section = doc.find("section", class_="section col-17 col-main js-watchlist-main-content")
            if not section:
                print("Couldn't find section")
                break

            ulist = section.find("ul", class_="poster-list")
            if not ulist:
                print("Couldn't find ul")
                break

            items = ulist.find_all("li", class_="poster-container")
            if not items:
                print("No list items found")
                break

            for item in items:
                div = item.find("div")
                if div:
                    title = div['data-film-slug'].strip()
                    print(title)
                    titles.append(title)

            page += 1
            sleep(2.0)

        except Exception as e:
            print(f"Error scraping page {page}: {e}")
            break

    return titles

# if __name__ == "__main__":
#     #list = watchlistScrape("isaackap")
    
#     list = favoriteFilmsScrape("isaackap")
#     print(list)