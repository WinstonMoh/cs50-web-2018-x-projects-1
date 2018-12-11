import requests

KEY = "WO7q04Tc6gtQsFYndPkIDw"
isbn = "1416949658"
res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns": isbn})

data = res.json()
ratings_count = data['books'][0]['work_ratings_count']
average_score = data['books'][0]['average_rating']

print("reviews count: " + str(ratings_count))
print("average rating: " + str(average_score))
print(data)
