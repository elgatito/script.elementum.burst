Adding providers
================


Adding a custom provider is similar to using overrides, although you'll be
using a JSON file, per provider or with all your custom providers, unless you
add them all in your custom `overrides.py`, which also works.

To add a provider, simply create a file with the ``.json`` extension under the
``providers`` folder in your `userdata`_, ie. as
``~/.kodi/userdata/addon_data/script.quasar.burst/providers/nice_provider.json``,
and make sure it follows the format below (hopefully with
``"subpage": false``):

.. code-block:: js

    {
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
    }

**TODO**: A more detailed description of all the fields and a tutorial on how
to actually create providers will soon be added.

.. _userdata: http://kodi.wiki/view/Userdata
