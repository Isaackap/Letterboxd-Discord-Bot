from bs4 import BeautifulSoup
import requests, logging
from time import sleep

my_logger = logging.getLogger("mybot")

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

# Only grabs the image placeholder url, before Javascript can fill in the actual link
# Not currently called anywhere
def filmImage(data):
    img_tag = data.find("img")
    my_logger.debug(img_tag["src"])

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
    
def diaryURL(data):
    partial_url = data.find("a")
    if partial_url:
        full_url = f"https://letterboxd.com{partial_url["href"]}"
        return full_url
    return False

def filmRewatch(data):
    if "icon-status-off" in data.get("class", []):
        return False
    return True

def profileImage(data):
    nav_bar = data.nav
    if nav_bar:
        image_url = nav_bar.find("img")
        return image_url["src"]
    else:
        return False
    

# Initial scrape when a new user is added
# Also is used as a verification if the added username exist on Letterboxd
def firstScrape(profile):
    url = f"https://letterboxd.com/{profile}/films/diary/"
    UNMATCHABLE_TITLE = "__UNMATCHABLE__"
    try:
        result = requests.get(url, headers=headers)
        if result.status_code != 200:
                my_logger.error(f"Failed to fetch page (status {result.status_code})")
                return False
        doc = BeautifulSoup(result.text, "html.parser")
        user = doc.find(["title"])
        if not user or "not found" in user.text.lower():
            my_logger.info(f"Invalid or non-existent user: {profile}")
            return False
        tbody = doc.tbody
        if tbody:
            trs = tbody.find_all("tr")
            date, details, released, rating, like, rewatch, review = trs[0].find_all("td")[1:8]
            film_title = filmTitle(details, UNMATCHABLE_TITLE)
            film_release = filmRelease(released)
            film_rating = filmRating(rating)
            film_review = filmReview(review)
            diary_url = diaryURL(details)
            film_rewatch = filmRewatch(rewatch)
            profile_image = profileImage(doc)
            #filmImage(details)
            return True, film_title, film_release, film_rating, film_review, diary_url, film_rewatch, profile_image
        else:
            return "no_entry"
    except Exception as e:
        my_logger.error(f"Error retrieving {profile} info: {e}")
        return False
    
# Scraping performed during the diary task loop
# Configured to only scrape the 5 most recent entries so to not spam a channel's chat if there are more to grab
def diaryScrape(profile, entry):
    url = f"https://letterboxd.com/{profile}/films/diary/"
    film_title = []
    film_release = []
    film_rating = []
    film_review = []
    diary_url = []
    film_rewatch = []
    throwaway_list = []
    #sleep(5.0) 

    try:
        result = requests.get(url, headers=headers)
        if result.status_code != 200:
                my_logger.error(f"Failed to fetch page (status {result.status_code})")
                return False, None
        doc = BeautifulSoup(result.text, "html.parser")
        user = doc.find(["title"])
        if not user or "not found" in user.text.lower():
            my_logger.info(f"Invalid or non-existent user: {profile}")
            return False, None
        
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
                        return False, None
                    else:
                        break
                first = False
                
                film_title.append(title)
                film_release.append(filmRelease(released))
                film_rating.append(filmRating(rating))
                film_review.append(filmReview(review))
                diary_url.append(diaryURL(details))
                film_rewatch.append(filmRewatch(rewatch))
                throwaway_list.append("pass")
                #filmImage(details)
                
            return True, film_title, film_release, film_rating, film_review, diary_url, film_rewatch, throwaway_list
        else:
            return False, None
        
    except Exception as e:
        my_logger.error(f"Error retrieving {profile} info: {e}")
        return False, None

# Scraping for users' favorite films listed on profile
def favoriteFilmsScrape(profile):
    url = f"https://letterboxd.com/{profile}/"
    titles = []

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
                my_logger.error(f"Failed to fetch page (status {response.status_code})")
                return False

        doc = BeautifulSoup(response.text, "html.parser")

        section = doc.find("section", id="favourites")
        if not section:
            my_logger.info("Couldn't find section")
            return False
        
        ulist = section.find("ul")
        if not ulist:
            return "No favorites"
        else:
            if ulist:
                list_items = ulist.find_all("li", class_="posteritem favourite-production-poster-container")
                for item in list_items:
                    img = item.find("div", class_= "react-component")
                    title = img["data-item-name"]
                    titles.append(title)
        
    except Exception as e:
            my_logger.error(f"Error scraping page {url}: {e}")
            return False

    return titles

# Scrapes a users' entire watchlist
# Should scrape all their pages if they have multiple
# Not currently working, and not called anywhere
def watchlistScrape(profile):
    base_url = f"https://letterboxd.com/{profile}/watchlist"
    page = 1
    titles = []

    while True:
        url = f"{base_url}/page/{page}/" if page > 1 else base_url
        my_logger.debug(f"Scraping page {page} for {profile}...")

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                my_logger.error(f"Failed to fetch page {page} (status {response.status_code})")
                break
            with open("raw_watchlist.html", "w+", encoding="utf-8") as f:
                f.write(response.text)

            doc = BeautifulSoup(response.text, "html.parser")
            
            section = doc.find("section", class_="section col-17 col-main js-watchlist-main-content")
            if not section:
                my_logger.debug("Couldn't find section")
                break

            ulist = section.find("ul", class_="poster-list")
            if not ulist:
                my_logger.debug("Couldn't find ul")
                break

            items = ulist.find_all("li", class_="poster-container")
            if not items:
                my_logger.debug("No list items found")
                break

            for item in items:
                div = item.find("div")
                if div:
                    title = div['data-film-slug'].strip()
                    my_logger.debug(title)
                    titles.append(title)

            page += 1
            sleep(2.0)

        except Exception as e:
            my_logger.error(f"Error scraping page {page}: {e}")
            break

    return titles


# if __name__ == "__main__":
    # list = watchlistScrape("isaackap")
    # list = firstScrape("isaackap")
    # list = favoriteFilmsScrape("isaackap")
    # print(list)

# Created only for the single-use function in the bot's on_ready()
# Used to grab profile avatar images for database storage
def profileImageOnReady(profile):
    url = f"https://letterboxd.com/{profile}/films/diary/"
    try:
        result = requests.get(url, headers=headers)
        if result.status_code != 200:
                my_logger.error(f"Failed to fetch page (status {result.status_code})")
                return False
        doc = BeautifulSoup(result.text, "html.parser")
        user = doc.find(["title"])
        if not user or "not found" in user.text.lower():
            my_logger.info(f"Invalid or non-existent user: {profile}")
            return False
        
        profile_image = profileImage(doc)
        return profile_image
        
    except Exception as e:
        my_logger.error(f"Error retrieving {profile} info: {e}")
        return False

# Was mostly used to test the scraping before the bot was created
# Currently not called anywhere
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
        my_logger.debug((user.string.split("’")[0]).strip())
    except Exception as e:
        my_logger.error(f"Error in scrapeSite: {e}")
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