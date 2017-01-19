# Quasar Burst

A burst of providers.


### Features
- Fast, very fast
- Compatible with Magnetic/Magnetizer, but **disable the Quasar Connector**
- Can extract providers, parsers and settings from Magnetic
- No extra add-ons to install, all providers are included
- No extra service running in the background
- Easy settings to enable or disable providers and filters
- First-class support with Quasar, and only Quasar (don't even ask)
- Simple definitions-based architecture with overrides
- Clean, PEP8 compliant code


### Installation

**IMPORTANT: Disable the Magnetic Quasar Connector before anything else.**

Install the add-on and enjoy.


### Adding / editing providers

**Do NOT add definitions to the `definitions.json` file**, it is generated automatically by the Magnetic extraction script.

A mechanism to easily add extra definitions will soon be implemented. Until then,
add your definitions in `libs/providers/definitions.py`. This is also where overrides
and fixes are added.

This is the format of a provider's definitions:
```
    "1337x": {
        "anime_extra": "",
        "anime_keywords": "{title} {episode}",
        "anime_query": "EXTRA",
        "base_url": "http://www.1337x.to/search/QUERY/1/",
        "color": "FFF14E13",
        "general_extra": "",
        "general_keywords": "{title}",
        "general_query": "EXTRA",
        "language": null,
        "login_failed": "",
        "login_object": "",
        "login_path": null,
        "movie_extra": "",
        "movie_keywords": "{title} {year}",
        "movie_query": "EXTRA",
        "name": "1337x",
        "parser": {
            "infohash": "",
            "name": "item('a', order=2)",
            "peers": "item(tag='td', order=3)",
            "row": "find_once(tag='body').find_all('tr')",
            "seeds": "item(tag='td', order=2)",
            "size": "item(tag='td', order=5)",
            "torrent": "item(tag='a', attribute='href', order=2)"
        },
        "private": false,
        "season_extra": "",
        "season_extra2": "",
        "season_keywords": "{title} Season {season:2}",
        "season_keywords2": "{title} Season{season}",
        "season_query": "EXTRA",
        "separator": "+",
        "show_query": "",
        "subpage": true,
        "tv_extra": "",
        "tv_extra2": "",
        "tv_keywords": "{title} s{season:2}e{episode:2}",
        "tv_keywords2": ""
    }
```
