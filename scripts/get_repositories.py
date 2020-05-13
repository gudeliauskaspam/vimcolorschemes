import base64
import json
import math
import re
import requests
import requests_cache
import sys
import time


requests_cache.install_cache("github_cache", backend="sqlite")


class colors:
    SUCCESS = "\033[92m"
    ERROR = "\033[91m"
    WARNING = "\033[33m"
    NORMAL = "\033[0m"


TIMEOUT = 5
SLEEP_TIME = 70

BASE_URL = "https://api.github.com"


def get(url, params={}):
    try:
        print("\nRequest for url:", url, "...")
        response = requests.get(url, params=params, timeout=TIMEOUT)
        print("Response status:", response.status_code)
        response.raise_for_status()

        used_cache = response.from_cache
        print(f"Request used cache: {used_cache}")

        data = response.json()
        print(f"{colors.SUCCESS}Successfully fetched data{colors.NORMAL}\n",)

        if not used_cache:
            print("Sleeping a little...")
            for i in range(1, SLEEP_TIME + 1):
                print(f"{i}/{SLEEP_TIME}")
                sys.stdout.write("\033[F")
                time.sleep(1)
            sys.stdout.write("\033[F")
            sys.stdout.write("\033[F")

        return data
    except requests.exceptions.HTTPError as errh:
        if response.status_code == 404:
            print(f"{colors.WARNING}Warning: 404 Not found for {url}{colors.NORMAL}")
            return None
        print(f"{colors.ERROR}Http Error:{colors.NORMAL}", errh)
    except requests.exceptions.ConnectionError as errc:
        print(f"{colors.ERROR}Error Connecting:{colors.NORMAL}", errc)
    except requests.exceptions.Timeout as errt:
        print(f"{colors.ERROR}Timeout Error:{colors.NORMAL}", errt)
    except requests.exceptions.RequestException as err:
        print(f"{colors.ERROR}Request error:{colors.NORMAL}", err)
    except ValueError as errv:
        print(f"{colors.ERROR}Error decoding JSON response:{colors.NORMAL}", errv)
    except Exception as e:
        print(f"{colors.ERROR}Unexpected error{colors.NORMAL}:", e)
    print("\nExiting system...")
    sys.exit()


def map_response_item_to_repository(response_item):
    return {
        "id": response_item["id"],
        "name": response_item["name"],
        "description": response_item["description"],
        "github_url": response_item["html_url"],
        "homepage_url": response_item["homepage"],
        "stargazers_count": response_item["stargazers_count"],
        "owner": {
            "name": response_item["owner"]["login"],
            "avatar_url": response_item["owner"]["avatar_url"],
        },
    }


def search_repositories():
    search_path = "search/repositories"
    url = f"{BASE_URL}/{search_path}"
    query = "vim color scheme language:vim sort:stars"
    items_per_page = 100
    base_search_params = {"per_page": items_per_page}
    items = []

    first_page_data = get(url, {"q": query, **base_search_params})
    items.extend(first_page_data["items"])
    total_count = first_page_data["total_count"]

    page_count = math.ceil(total_count / items_per_page)

    for page in range(2, page_count + 1):
        data = get(url, {"q": query, "page": page, **base_search_params})
        items.extend(data["items"])

    map_result = map(map_response_item_to_repository, items)
    repositories = list(map_result)

    return total_count, repositories


def decode_file_content(data):
    base64_bytes = data.encode("utf-8")
    bytes = base64.b64decode(base64_bytes)
    return bytes.decode("utf-8")


def get_readme_file(owner, name):
    get_readme_path = f"repos/{owner}/{name}/readme"
    url = f"{BASE_URL}/{get_readme_path}"

    data = get(url)

    if not data:
        return ""

    return decode_file_content(data["content"])


def find_image_urls(readme):
    return re.findall(r"(https?:\/\/.*\.(?:png|jpg|jpeg|webp|gif))", readme)


def save_repository_file(repository):
    output_file = open(
        f"data/{repository['owner']['name']}__{repository['name']}.json", "w"
    )
    json.dump(repository, output_file, indent=2)
    output_file.close()


if __name__ == "__main__":
    total_count, repositories = search_repositories()

    print("total_count:", total_count)
    print("repositories count:", len(repositories))

    for index, repository in enumerate(repositories):
        repository["readme"] = get_readme_file(
            repository["owner"]["name"], repository["name"]
        )
        repository["image_urls"] = find_image_urls(repository["readme"])
        save_repository_file(repository)
