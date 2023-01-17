from contextlib import suppress
import time
import keyboard
from requests_html import HTMLSession, HTMLResponse, HTML, _Find


class NSClient(HTMLSession):
    def __init__(
        self, script_name: str, script_version: str, dev_nation: str, user_nation: str
    ):
        """Initializes the specialized client for NationStates

        Args:
            script_name (str): Name of your script (e.g. "Shine")
            script_version (str): Version of your script (e.g. "2.0.0")
            dev_nation (str): You, the developer's, nation name on NationStates (e.g. "Sweeze")
            user_nation (str): Nation of whoever is running your script (e.g. "The Chariot")

        """
        super().__init__()  # inherit the structures and methods of HTMLSession
        self.headers[
            "User-Agent"
        ] = f"{script_name}/{script_version} (by:{dev_nation}; usedBy:{user_nation})"
        # storing various NS-specific things about the current session
        self.nation: str = "Not saved"
        self.chk: str = "Not saved"
        self.localid: str = "Not saved"
        self.region: str = "Not saved"

    def req(self, url: str, data: dict = {}, msg: str = "Press space to continue...", allow_redirects: bool = False) -> HTMLResponse:
        # sourcery skip: default-mutable-arg
        if "api.cgi" in url:
            response: HTMLResponse = self.post(url, data, allow_redirects=allow_redirects)
            if int(response.headers["x-ratelimit-requests-seen"]) >= 55:
                time.sleep(1.2)
                # this is probably safe in 99% of cases but i should
                # move this to a proper bucket rate limiter someday
            return response
        elif "nationstates.net" not in url:
            return self.post(url, data, allow_redirects=allow_redirects)
        data |= {"localid": self.localid, "chk": self.chk}
        self._wait_for_input(msg)
        response: HTMLResponse = self.post(url, data, allow_redirects=allow_redirects)
        # setting values
        with suppress(Exception):
            self.nation = response.html.find("body")[0].attrs["data-nname"]
        with suppress(Exception):
            self.localid = response.html.find("input[name=localid]")[0].attrs["value"]
        with suppress(Exception):
            self.chk = response.html.find("input[name=chk]")[0].attrs["value"]
        with suppress(Exception):
            temp_region = self._get_region(response.html)
            if temp_region is not None:
                self.region = temp_region
        return response
    
    def check_user_agent(self):
        url = "https://www.nationstates.net/cgi-bin/api.cgi"
        data = {"a": "useragent"}
        response = self.req(url, data)
        print(response.text)

    def _print_vals(self):
        print(f"Nation: {self.nation}")
        print(f"CHK: {self.chk}")
        print(f"Localid: {self.localid}")
        print(f"Region: {self.region}")

    def _wait_for_input(self, message):
        print(message)
        keyboard.wait("space")
        while keyboard.is_pressed("space"):
            pass

    def _get_region(self, html: HTML):
        region = None
        with suppress():  # change region page
            if "Change Region" in html.text:
                info = html.find("p.info")[0]
                region = info.find("a.rlink")[0].attrs["href"].split("region=")[1]
                return region
        with suppress():  # antiquity/century
            region = html.find(".STANDOUT")[1].attrs["href"].split("region=")[1]
            return region
        with suppress():  # rift
            region_sidebar = html.find("#panelregionbar")[0]
            region = region_sidebar.find("a")[0].attrs["href"].split("region=")[1]
            return region
        with suppress():  # current region page
            if "Tired of life in " in html.text:
                region = (
                    html.find("a[href=page=change_region]")[0]
                    .text.split("life in ")[1]
                    .replace("?", "")
                )
                return region
        return region

    def login(self, nation: str, password: str):
        """Given a nation and it's password, logs into it and stores CHK, localid, nation name and region name

        Args:
            nation (str): _description_
            password (str): _description_
        """
        url: str = "https://antiquity.nationstates.net/region=rwby"
        # this trick lets me get chk, localid *and* pin in one pageload! insane
        data: dict[str, str] = {
            "logging_in": "1",
            "nation": nation,
            "password": password,
        }
        self.req(url, data, f"Press space to log in to {nation}")

    def refresh(self):
        url: str = "https://antiquity.nationstates.net/region=rwby"
        self.req(url, msg="Press space to refresh authentication values")

    def move_to_region(self, region: str):
        url: str = (
            "https://www.nationstates.net/template-overall=none/page=change_region"
        )
        data: dict = {"move_region": "1", "region_name": region}
        response = self.req(url, data, f"Press space to move to {region}")
        return "Success!" in response.text

    def join_wa(self, nation: str, app_id: str):
        url: str = "https://www.nationstates.net/cgi-bin/join_un.cgi"
        data: dict = {"nation": nation, "appid": app_id}
        response = self.req(url, data, f"Press space to join the WA on {nation}")
        if "email_in_use" in response.headers["location"]:
            print("In the WA on another nation")
            return False
        elif "already_member" in response.headers["location"]:
            print("Already in the WA")
            return False
        elif "bad_request" in response.headers["location"]:
            print("Bad App")
            return False
        return True

    def resign_wa(self):
        url = "https://www.nationstates.net/template-overall=none/page=UN_status"
        data = {"action": "leave_UN", "submit": "1"}
        response = self.req(url, data, f"Press space to resign WA on {self.nation}")
        return "on its own." in response.text
