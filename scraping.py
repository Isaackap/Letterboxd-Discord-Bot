from bs4 import BeautifulSoup
import requests


def filmTitle(data):
    title_name = data.find("a")
    if title_name:
        #print(title_name.string)
        return title_name.string

def filmImage(data):
    img_tag = data.find("img")
    print(img_tag["src"])

def filmRelease(data):
    release_year = data.find("span")
    if release_year:
        #print(release_year.string)
        return release_year.string

def filmRating(data):
    # user_rating_star = data.find("span")
    user_rating_number = data.find("input")
    # if user_rating_star.string != "":
    #     print(user_rating_star.string)
    #     if user_rating_number:
    #         print(user_rating_number["value"])
    if user_rating_number:
        return user_rating_number["value"]
    else:
        #print("User didn't rate the film")
        return False

def filmReview(data):
    if "icon-status-off" in data.get("class", []):
        # print("User has no review")
        return False
    else:
        partial_url = data.find("a")
        full_url = f"https://letterboxd.com{partial_url["href"]}"
        #print(f"User's film review: {full_url}")
        return full_url
    

def scrapeSite(profile):
    url = f"https://letterboxd.com/{profile}/films/diary/"
    try:
        result = requests.get(url)
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
    try:
        result = requests.get(url)
        doc = BeautifulSoup(result.text, "html.parser")
        user = doc.find(["title"])
        if not user or "not found" in user.text.lower():
            print(f"Invalid or non-existent user: {profile}")
            return False
        #print((user.string.split("’")[0]).strip())
        tbody = doc.tbody
        trs = tbody.find_all("tr")
        date, details, released, rating, like, rewatch, review = trs[0].find_all("td")[1:8]
        film_title = filmTitle(details)
        film_release = filmRelease(released)
        film_rating = filmRating(rating)
        film_review = filmReview(review)
        #filmImage(details)
        return True, film_title, film_release, film_rating, film_review
    except Exception as e:
        print(f"Error retrieving {profile} info: ", e)
        return False

def main():
    pass
    

if __name__ == "__main__":
    main()