import pandas as pd
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

class upsl_scraper:
    def __init__(self, base_url, json_file="upsl_data.json"):
        self.base_url = base_url
        self.json_file = json_file
        self.driver = None

    def initialize_driver(self):
        """Initialize the Selenium WebDriver."""
        options = Options()
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        self.driver = webdriver.Chrome(options=options)

    def close_driver(self):
        """Close the Selenium WebDriver."""
        if self.driver:
            self.driver.quit()

    def scrape_team_links(self):
        """Scrape team links and save them to a JSON file."""
        self.initialize_driver()
        self.driver.get(self.base_url)
        time.sleep(2)  # Wait for the page to load

        # Hierarchical data structure
        data = {"Division": {"Premier": {"Conference": {}}}}

        # Extract team details
        team_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.teams__card--container")
        for team_card in team_cards:
            team_id = team_card.get_attribute("data-team-id")
            team_name = team_card.get_attribute("data-team-name").strip()
            team_conference = team_card.get_attribute("data-team-conference").strip()
            team_link = team_card.find_element(By.TAG_NAME, "a").get_attribute("href")

            if team_conference not in data["Division"]["Premier"]["Conference"]:
                data["Division"]["Premier"]["Conference"][team_conference] = {"Teams": {}}
            
            data["Division"]["Premier"]["Conference"][team_conference]["Teams"][team_name] = {
                "team_id": team_id,
                "team_link": team_link
            }

        self.close_driver()

        # Save to JSON
        with open(self.json_file, "w") as file:
            json.dump(data, file, indent=4)
        print(f"Saved team links to {self.json_file}")

    def scrape_roster(self, team_link):
        """Scrape the roster for a given team link."""
        self.initialize_driver()
        self.driver.get(team_link)
        time.sleep(2)

        # Scrape player details
        players = []
        player_names = self.driver.find_elements(By.XPATH, '//span[@class="single-team__roster-player-name"]')
        positions = self.driver.find_elements(By.XPATH, '//span[@class="single-team__roster-player-title"]')
        appearances = self.driver.find_elements(By.XPATH, '//span[@class="single-team__roster-player-appearances"]')

        for i in range(len(player_names)):
            name = ' '.join(player_names[i].text.split('\n'))
            position = positions[i].text if i < len(positions) else "N/A"
            appearances_count = appearances[i].text.split(":")[1].strip() if "Appearances:" in appearances[i].text else "0"
            
            players.append({
                "Player": name,
                "Position": position,
                "Appearances": appearances_count
            })

        self.close_driver()
        return players

    def append_rosters(self):
        """Append rosters to each team in the JSON file."""
        with open(self.json_file, "r") as file:
            data = json.load(file)

        for division_key, division_value in data["Division"].items():
            for conference_key, conference_value in division_value["Conference"].items():
                for team_name, team_info in conference_value["Teams"].items():
                    if team_info["team_link"].startswith("https://premier"):
                        print(f"Scraping roster for {team_name}...")
                        roster = self.scrape_roster(team_info["team_link"])
                        team_info["Roster"] = roster

        # Save updated JSON
        with open(self.json_file, "w") as file:
            json.dump(data, file, indent=4)
        print(f"Updated data saved to {self.json_file}")

    def scrape_match_data(self):
        """Scrape match details from the team schedule/results table and append to the 'Matches' key."""
        with open(self.json_file, "r") as file:
            data = json.load(file)

        # Iterate through all conferences
        for division_key, division_value in data["Division"].items():
            for conference_key, conference_value in division_value["Conference"].items():
                # Only process the Midwest Central Conference
                if conference_key == "Midwest Central":
                    for team_name, team_info in conference_value["Teams"].items():
                        # Check if the roster is not empty
                        if "Roster" in team_info and team_info["Roster"]:
                            print(f"Scraping match details for {team_name}...")
                            self.initialize_driver()
                            self.driver.get(team_info["team_link"])  # Use the team's link to get match details

                            # Wait for the schedule/results toggle to be present
                            WebDriverWait(self.driver, 30).until(
                                EC.presence_of_element_located((By.XPATH, '//h3[@data-toggle="upsl__show__results"]'))
                            )

                            # Click the Results toggle
                            results_toggle = self.driver.find_element(By.XPATH, '//h3[@data-toggle="upsl__show__results"]')
                            results_toggle.click()

                            # Wait for the results table to be present
                            WebDriverWait(self.driver, 30).until(
                                EC.presence_of_element_located((By.XPATH, '//*[@id="single-team-schedule"]/tbody'))
                            )

                            # Print the page source for debugging
                            print(self.driver.page_source)  # Check if the content is loaded correctly

                            # Extract match details from the table
                            match_rows = self.driver.find_elements(By.XPATH, '//*[@id="single-team-schedule"]/tbody/tr')
                            match_details = []

                            for row in match_rows:
                                try:
                                    # Extract relevant details
                                    home_team = row.find_element(By.XPATH, './td[1]/a').text.strip()
                                    away_team = row.find_element(By.XPATH, './td[2]/a').text.strip()
                                    date = row.find_element(By.XPATH, './td[3]').text.strip()
                                    home_score = row.find_element(By.XPATH, './td[4]').text.strip()
                                    away_score = row.find_element(By.XPATH, './td[5]').text.strip()
                                    venue = row.find_element(By.XPATH, './td[6]').text.strip()  # If you want to include the venue
                                    season_element = self.driver.find_element(By.XPATH, '//*[@id="single__select-season"]/option[@selected="selected"]')
                                    season = season_element.text.strip()  # Get the selected season text

                                    match_details.append({
                                        "Date": date,
                                        "Home Team": home_team,
                                        "Away Team": away_team,
                                        "Home Score": home_score,
                                        "Away Score": away_score,
                                        "Venue": venue
                                    })
                                except NoSuchElementException as e:
                                    print(f"Error extracting match details for {team_name}: {e}")

                            self.close_driver()

                            # Create the "Matches" key if it doesn't exist
                            if f"Matches {season}" not in team_info:
                                team_info[f"Matches {season}"] = []

                            # Append match details to the team's Matches key
                            team_info[f"Matches {season}"].extend(match_details)

        # Save updated JSON
        with open(self.json_file, "w") as file:
            json.dump(data, file, indent=4)
        print(f"Match details appended to {self.json_file}")

    def json_to_dataframe(self, csv_file="midwest_central_matches.csv"):
        """Convert Midwest Central Conference match data to a DataFrame and export to CSV."""
        with open(self.json_file, "r") as file:
            data = json.load(file)

        matches_data = []

        # Extract match data for the Midwest Central Conference
        for division_key, division_value in data["Division"].items():
            for conference_key, conference_value in division_value["Conference"].items():
                if conference_key == "Midwest Central":
                    for team_name, team_info in conference_value["Teams"].items():
                        for season_key, matches in team_info.items():
                            if season_key.startswith("Matches"):
                                season = season_key.replace("Matches ", "")
                                for match in matches:
                                    match_details = {
                                        "Division": division_key,
                                        "Conference": conference_key,
                                        "Date": match["Date"],
                                        "Home Team": match["Home Team"],
                                        "Away Team": match["Away Team"],
                                        "Home Score": match["Home Score"],
                                        "Away Score": match["Away Score"],
                                        "Venue": match["Venue"],
                                        "Season": season,
                                        "Video Collected": "",  # Placeholder for future data
                                        "Source": "",  # Placeholder for future data
                                        "Link": ""
                                    }
                                    matches_data.append(match_details)

        # Convert to DataFrame
        df = pd.DataFrame(matches_data)

        # Remove duplicates
        df = df.drop_duplicates(subset=['Division', 'Conference', 'Date', 'Home Team', 'Away Team', 'Home Score', 'Away Score'])

        # Convert date column to datetime
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        # Sort by date
        df = df.sort_values(by='Date')

        # Export to CSV
        df.to_csv(csv_file, index=False)
        print(f"Data exported to {csv_file}")

        return df


# Add the __main__ block at the end of the script
if __name__ == "__main__":
    import sys

    # Create an instance of the scraper
    scraper = upsl_scraper(base_url="https://premier.upsl.com/teams/")

    # Check command-line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "scrape_team_links":
            scraper.scrape_team_links()
        elif command == "append_rosters":
            scraper.append_rosters()
        elif command == "scrape_match_data":
            scraper.scrape_match_data()
        elif command == "convert_to_dataframe":
            df = scraper.json_to_dataframe()
            print(df.head()) # Display first few rows
        else:
            print("Unknown command. Use 'scrape_team_links', 'append_rosters', 'scrape_match_data', 'convert_to_dataframe'.")
    else:
        print("No command provided. Use 'scrape_team_links', 'append_rosters', 'scrape_match_data', 'convert_to_dataframe.")

