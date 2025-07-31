from bs4 import BeautifulSoup
import requests, json


def filmTitle(data):
    title_name = data.find("a")
    if title_name:
        print(title_name.string)

def filmImage(data):
    img_tag = data.find("img")
    print(img_tag["src"])

def filmRelease(data):
    release_year = data.find("span")
    if release_year:
        print(release_year.string)

def filmRating(data):
    user_rating_star = data.find("span")
    user_rating_number = data.find("input")
    if user_rating_star.string != "":
        print(user_rating_star.string)
        if user_rating_number:
            print(user_rating_number["value"])
    else:
        print("User didn't rate the film")

def filmReview(data):
    if "icon-status-off" in data.get("class", []):
        print("User has no review")
    else:
        review_url = data.find("a")
        print(f"User's film review: https://letterboxd.com{review_url["href"]}")
    

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

def main():
    pass
    

if __name__ == "__main__":
    main()