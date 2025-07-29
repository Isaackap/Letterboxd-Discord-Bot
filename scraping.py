from bs4 import BeautifulSoup
import requests

# url = "https://letterboxd.com/isaackap/films/diary/"
# result = requests.get(url)
# doc = BeautifulSoup(result.text, "html.parser")
# with open("index.html", "w") as file:
#     file.write(result.text)
with open("index.html", "r") as file:
    doc = BeautifulSoup(file, "html.parser")

def filmTitle(data):
    title_name = data.find("a")
    if title_name:
        print(title_name.string)

def filmImage():
    pass

def filmRelease(data):
    release_year = data.find("span")
    if release_year:
        print(release_year.string)

def filmRating(data):
    user_rating_star = data.find("span")
    user_rating_number = data.find("input")
    if user_rating_star:
        print(user_rating_star.string)
    if user_rating_number:
        print(user_rating_number["value"])

def filmReview(data):
    if "icon-status-off" in data.get("class", []):
        print("User has no review")
    


def main():
    try:
        user = doc.find(["title"])
        print((user.string.split("’")[0]).strip())
    except Exception as e:
        print(e)

    tbody = doc.tbody
    trs = tbody.find_all("tr")
    for tr in trs:
        date, details, released, rating, like, rewatch, review = tr.find_all("td")[1:8]
        filmTitle(details)
        filmRelease(released)
        filmRating(rating)
        filmReview(review)
        print()
    

if __name__ == "__main__":
    main()