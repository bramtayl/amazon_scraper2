docker run --name pylucene --mount type=bind,source="$(pwd)",target=/amazon_scraper coady/pylucene python3 /amazon_scraper/test.py
docker rm pylucene
