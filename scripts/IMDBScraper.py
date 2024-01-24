#!/usr/bin/env python
# coding: utf-8

# In[1]:


from imdb import Cinemagoer
import imdb
import pandas as pd
import time
import os

ia = imdb.IMDb("https", languages="en-EN")


def isIMDBCode(code):
    code = str(code)
    if code.isdigit() and len(code) >= 7:
        return True
    return False


def findIMDBResultbyName(name, year=None):
    functionName = "findIMDBResultbyName"
    search = ia.search_movie(name)
    print(f"{functionName}::: Searching {name} {year}") if year != None else print(
        f"{functionName}::: Searching {name}"
    )
    for result in search:
        print(f"{functionName}::: Result: {result}, {result.get('year')}")
        if year == None or (year != None and int(result.get("year")) == int(year)):
            print(f"{functionName}::: Title found.")
            return result
        print(f"{functionName}::: Unmatched, next.")
    print(f"{functionName}::: No results found. Results below:")
    # printSearch(search)
    print(f"{functionName}::: Function is terminating")
    return None


def setDateTimeNuances(df):
    def custom_date_parser(row):
        date_str = row["episodeDate"]
        title = row[
            "episodeTitle"
        ]  # Assuming 'episodeTitle' is another column you want to use
        try:
            # Try to parse the date using the provided format
            return pd.to_datetime(date_str, format="%a, %b %d, %Y")
        except ValueError:
            try:
                print(
                    f"Different date format in '{title}'. Original date from IMDB: '{date_str}' typed as ",
                    end="'",
                )
                print(pd.to_datetime(date_str, format="%Y"), end="'\n")
                # If the provided format fails, try an alternative format
                return pd.to_datetime(date_str, format="%Y")
            except ValueError:
                print(pd.NaT, end="'\n")
                # If both formats fail, return NaT
                return pd.NaT

    df["episodeDate"] = df.apply(lambda row: custom_date_parser(row), axis=1)
    df["episodeDateTimestamp"] = pd.to_datetime(
        df["episodeDate"], format="%a, %b %d, %Y"
    ).apply(lambda x: x.timestamp())
    df["episodeDateTimestamp"] = df["episodeDateTimestamp"].astype(int)
    df["episodeDateString"] = df["episodeDate"]
    df["episodeDate"] = pd.to_datetime(df["episodeDate"], format="%a, %b %d, %Y")
    return df


def addRow(
    df,
    title,
    episodeTitle,
    seasonNo,
    episodeNo,
    episodeRating,
    episodeDate,
    episodeID,
    posterURL,
    showRating,
):
    temp_episode_dict = {}
    temp_episode_dict["title"] = title
    temp_episode_dict["episodeTitle"] = episodeTitle
    temp_episode_dict["season"] = int(seasonNo)
    temp_episode_dict["episode"] = int(episodeNo)
    if episodeRating == None:
        temp_episode_dict["episodeRating"] = None
    else:
        temp_episode_dict["episodeRating"] = float(episodeRating)
    temp_episode_dict["episodeDate"] = episodeDate
    temp_episode_dict["episodeID"] = str(episodeID)
    temp_episode_dict["posterURL"] = posterURL
    temp_episode_dict["showRating"] = showRating
    df = pd.concat([df, pd.DataFrame([temp_episode_dict])], ignore_index=True)
    return df


def getSeriesInfo(
    code, updateFetched="no", year=None, nameorCode=None, seasonorYear="season"
):
    if os.path.exists("..//fetched//" + code + ".xlsx"):
        if updateFetched == "no":
            return pd.read_excel(
                "..//fetched//" + code + ".xlsx", converters={"episodeID": str}
            )
        elif updateFetched == "yes" or updateFetched == "update":
            pass
        else:
            return pd.read_excel(
                "..//fetched//" + code + ".xlsx", converters={"episodeID": str}
            )

    if nameorCode == 1 or (nameorCode == None and not isIMDBCode(code)):
        print(f"#Find IMDB Code by Name: {code}")
        code = findIMDBResultbyName(code, year).getID()
        print(f"#IMDB Code found: {code}")

    if nameorCode == 2 or isIMDBCode(code):
        try:
            result = ia.get_movie(code)
            title = str(result["title"])
            showRating = float(result["rating"])
            posterURL = str(result.get_fullsizeURL())
            if result["kind"] == "tv series":
                ia.update(result, "episodes")

                df = pd.DataFrame()
                for seasonNo in result["episodes"]:
                    for episodeNo in result["episodes"][seasonNo]:
                        temp_episode_dict = {}
                        episode = result["episodes"][seasonNo][episodeNo]
                        episodeTitle = episode["title"]
                        episodeRating = episode["rating"]
                        episodeDate = episode["original air date"]
                        episodeID = str(episode.getID())

                        df = addRow(
                            df,
                            title,
                            episodeTitle,
                            seasonNo,
                            episodeNo,
                            episodeRating,
                            episodeDate,
                            episodeID,
                            posterURL,
                            showRating,
                        )
                df = setDateTimeNuances(df)
                df.to_excel("..//fetched//" + code + ".xlsx", index=False)
                return df
            else:
                print(f"{code} is not a tv series")
        except Exception as err:
            print("Cinemagoer failed, Selenium trying", err)
            return getSeriesInfobySelenium(code, seasonorYear)
    return None


# In[2]:


def getSeriesInfobySelenium(code, seasonorYear="season"):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By

    def moreorAll(driver):
        if (
            driver.find_element(By.CLASS_NAME, "fXtoQb")
            .find_elements(By.TAG_NAME, "button")[1]
            .text
            == "All"
        ):
            return "All"
        else:
            return "More"

    def checkMore(driver):
        if len(driver.find_elements(By.CLASS_NAME, "fXtoQb")) >= 1:
            return True
        else:
            return False

    def is_element_visible_in_viewpoint(driver, element) -> bool:
        return driver.execute_script(
            "var elem = arguments[0],                 "
            "  box = elem.getBoundingClientRect(),    "
            "  cx = box.left + box.width / 2,         "
            "  cy = box.top + box.height / 2,         "
            "  e = document.elementFromPoint(cx, cy); "
            "for (; e; e = e.parentElement) {         "
            "  if (e === elem)                        "
            "    return true;                         "
            "}                                        "
            "return false;                            ",
            element,
        )

    def loadMore(driver):
        driver.find_element(By.CLASS_NAME, "fXtoQb").find_elements(
            By.TAG_NAME, "button"
        )[1].get_attribute("aria-disabled")
        print("Load More")
        while checkMore(driver):
            try:
                if (
                    moreorAll(driver) == "All"
                    and driver.find_element(By.CLASS_NAME, "fXtoQb")
                    .find_elements(By.TAG_NAME, "button")[1]
                    .get_attribute("aria-disabled")
                    == "false"
                ):
                    print("Listing all episodes")
                    driver.find_element(By.CLASS_NAME, "fXtoQb").find_elements(
                        By.TAG_NAME, "button"
                    )[1].click()
                elif (
                    moreorAll(driver) == "More"
                    and driver.find_element(By.CLASS_NAME, "fXtoQb")
                    .find_elements(By.TAG_NAME, "button")[0]
                    .get_attribute("aria-disabled")
                    == "false"
                ):
                    print("Listing more episodes")
                    driver.find_element(By.CLASS_NAME, "fXtoQb").find_elements(
                        By.TAG_NAME, "button"
                    )[0].click()
            except:
                pass
            time.sleep(1)
        print("All episodes are listed")

    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    url = f"https://www.imdb.com/title/tt{code}/"
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    if driver.find_elements(By.CLASS_NAME, "cMEQkK")[0].text != "":
        showRating = float(driver.find_elements(By.CLASS_NAME, "cMEQkK")[0].text)
    else:
        showRating = float(driver.find_elements(By.CLASS_NAME, "iZlgcd")[1].text)

    if len(driver.find_elements(By.CLASS_NAME, "dRCGjd")) >= 1:
        driver.find_element(By.CLASS_NAME, "dRCGjd").click()

    url = f"https://www.imdb.com/title/tt{code}/episodes/"
    driver.get(url)

    upperMenu = driver.find_element(By.CLASS_NAME, "iZwhod")
    seasons_years_toprated = upperMenu.find_elements(By.CLASS_NAME, "jAOkal")[1]
    if seasonorYear == "season":
        pass
    elif seasonorYear == "year":
        for i in seasons_years_toprated.find_elements(By.TAG_NAME, "a"):
            if i.text == "Years":
                i.click()
                while i.get_attribute("aria-selected") == "false":
                    pass
    else:
        return None
    seasonElements = (
        upperMenu.find_elements(By.TAG_NAME, "div")[1]
        .find_elements(By.TAG_NAME, "ul")[0]
        .find_elements(By.TAG_NAME, "a")
    )

    df = pd.DataFrame()
    for seasonElement in seasonElements:
        if seasonElement.text == "" or seasonElement.text == "Unknown":
            continue
        while not ("ipc-tab--active" in seasonElement.get_attribute("class")):
            try:
                if len(driver.find_elements(By.CLASS_NAME, "nprogress-busy")) < 1:
                    seasonElement.click()
            except:
                pass
            time.sleep(1)

        time.sleep(1)
        print(f"Season {seasonElement.text} Fetching")

        episodeElements = driver.find_element(By.CLASS_NAME, "hOJNkT").find_elements(
            By.TAG_NAME, "article"
        )
        if checkMore(driver):
            loadMore(driver)

        episodeElements = driver.find_element(By.CLASS_NAME, "hOJNkT").find_elements(
            By.TAG_NAME, "article"
        )
        title = driver.find_element(By.CLASS_NAME, "dcErWY").text
        for episodeElement in episodeElements:
            temp_episode_dict = {}
            episodeTitle = str(
                episodeElement.find_element(By.TAG_NAME, "h4").text
            ).split(" ∙ ")[1]
            seasonNo = int(
                episodeElement.find_element(By.TAG_NAME, "h4")
                .text.split(" ∙ ")[0]
                .split(".")[0][1:]
            )
            episodeNo = int(
                episodeElement.find_element(By.TAG_NAME, "h4")
                .text.split(" ∙ ")[0]
                .split(".")[1][1:]
            )

            if episodeElement.find_element(By.CLASS_NAME, "bXuGWE").text != "":
                episodeRating = episodeElement.find_element(
                    By.CLASS_NAME, "bXuGWE"
                ).text.split("\n")[0]
            else:
                episodeRating = None

            if len(episodeElement.find_elements(By.CLASS_NAME, "fyHWhz")) >= 1:
                episodeDate = episodeElement.find_element(By.CLASS_NAME, "fyHWhz").text
            else:
                episodeDate = None

            episodeID = str(
                episodeElement.find_element(By.TAG_NAME, "a")
                .get_attribute("href")
                .split("/")[4][2:]
            )
            tempImgURL = episodeElement.find_element(By.TAG_NAME, "img").get_property(
                "src"
            )
            posterURL = (
                tempImgURL[: tempImgURL[: tempImgURL.rfind(".")].rfind(".")]
                + tempImgURL[tempImgURL.rfind(".") :]
            )
            df = addRow(
                df,
                title,
                episodeTitle,
                seasonNo,
                episodeNo,
                episodeRating,
                episodeDate,
                episodeID,
                posterURL,
                showRating,
            )
        print("Season fetching completed")
    df = setDateTimeNuances(df)
    print(df)
    df.to_excel("..//fetched//" + code + ".xlsx", index=False)
    print(code + ".xlsx saved to " + os.path.abspath("..//fetched//" + code + ".xlsx"))
    return df

