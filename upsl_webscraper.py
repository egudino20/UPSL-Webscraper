import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

class upsl_scraper:
    def __init__(self, base_url, json_file="upsl_data.json"):
        self.base_url = base_url
        self.json_file = json_file
        self.driver = None

    def initialize_driver(self):
        """Initialize the Selenium WebDriver."""
        options = Options()
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
        else:
            print("Unknown command. Use 'scrape_team_links' or 'append_rosters'.")
    else:
        print("No command provided. Use 'scrape_team_links' or 'append_rosters'.")

