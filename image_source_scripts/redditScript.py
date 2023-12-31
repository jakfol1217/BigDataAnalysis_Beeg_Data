import argparse

parser = argparse.ArgumentParser(
    prog="RedditAPIGetter",
    description="Script to retrieve images using the Reddit API"
)
parser.add_argument("-n", "--number",
                    help="Number of images retrieved",
                    type=int,
                    default=5
                    )

parser.add_argument("-id", "--client_id",
                    required=True)

parser.add_argument("-p", "--password",
                    required=True)

parser.add_argument("-s", "--subreddit",
                    default="memes")

args = parser.parse_args()

import praw
import datetime
import time
import json

from loadImage import get_img_from_link

reddit = praw.Reddit(
    client_id=args.client_id,
    client_secret=args.password,
    user_agent="BeegMeem WUT project by /u/NotMeeh",
)

for submission in reddit.subreddit(args.subreddit).hot(limit=args.number):
    s = {
        k:v
        for k, v in submission.__dict__.items()
        if not (k[0]=="_" or k in ["flair", "mod", "subreddit"])
    }
    s["author"] = submission.author.name
    s["datetime_utc"] = datetime.datetime.fromtimestamp(s["created_utc"]).isoformat()
    s["datetime"] = datetime.datetime.fromtimestamp(s["created"]).isoformat()
    get_img_from_link(s['url'], s['id']+'-reddit')
    print(json.dumps(s))
