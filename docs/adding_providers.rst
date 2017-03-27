Adding providers
----------------


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


Provider fields
===============

name
""""
The provider's name as displayed to the user, typically with color.

color
"""""
The color of the provider name using Kodi's ARGB (alpha-red-green-blue) color
format.

base_url
""""""""
The ``base_url`` is the part of the provider's URL that is **always** found in
your browser bar when you visit or more importantly, search the site. It may or
may not contain the ``QUERY`` part (more on that later); it really only depends
on the **common** part of the different search queries.

language
""""""""
Forces a language preference for translations if they're available, eg. ``es``

private
"""""""
Boolean flag to mark this provider as private, see PrivateProviders_.

separator
"""""""""
Space separator used in URL queries by this provider, typically ``%20`` for an
encoded white-space or ``+``

subpage
"""""""
The most expensive boolean flag, to be avoided as much as possible. This tells
Burst that we have no choice but to open **each and every** link to get to the
torrent or magnet link. As it stands, we also waste the ``torrent`` (more on
that later) definition under ``parser``, which becomes the link to follow, and
the page at that link gets automatically processed to find a magnet or torrent
link in it.

\*_query
""""""""
Second part of the URL after ``base_url`` which will contain the ``QUERY``
keyword if it's not already in the ``base_url``. This typically include
category parameters specific to each provider, ie. ``/movies/QUERY``

\*_extra
""""""""
The most confusing part of queries. Those will contain *extra* parameters,
typically categories also, replacing the ``EXTRA`` keyword often found in the
respective ``*_query`` definition, and often simply for the convenience of
shorter ``*_query`` definitions. Note that this is mostly always just an empty
string and not being used.

\*_keywords
"""""""""""
Keyword definitions for the different search types, with special placeholders
like ``{title}`` for a movie or TV show title.

List of keyword types
^^^^^^^^^^^^^^^^^^^^^
    - ``{title}`` Movie or TV show title
    - ``{year}`` Release date, typically for movies only
    - ``{season}`` Season number. Using ``{season:2}`` pads to 2 characters with
      leading zeros, eg. ``s{season:2}`` would become ``s01`` for an episode of
      season 1.
    - ``{episode}`` Episode number, same formatting as ``{season}`` with regards
      to padding, ie. ``{episode:2}``. Typically used with season as such:
      ``s{season:2}e{episode:2}``


parser
""""""
This is the most important part of every provider, and tells Burst how to
find torrents within search result pages. The first parser definition to be used
is the ``row``, and is also the "parent" to all to the others. It most usually
ends with a ``find_all('tr')``, and tells Burst which HTML tags, typically table
rows, hold the results we're interested in. All other parser definitions will
then look **within** each row for their respective information. Each other
parser definition tells Burst what HTML tag has its information, for example
``item(tag='td', order=1)`` for ``name`` tells Burst that the torrent name is
in the first table column of each row.

**TODO**: A more detailed description of parser fields and a tutorial on how
to actually create providers will soon be added.


.. _PrivateProviders:

Private providers
========================

login_path
""""""""""
The ``login_path`` is the part of the URL used for logging in, typically
something like ``"/login.php"``. This can be found by inspecting the login
form's HTML and taking its ``action`` attribute.

login_object
""""""""""""
The ``login_object`` represents the form elements sent to the ``login_path``.
For built-in private providers, placeholders are used to replace setting values
for the username and password (``USERNAME`` and ``PASSWORD`` respectively).
Custom providers cannot define new settings, and must therefore put the username
and password in the ``login_object`` directly.

login_failed
""""""""""""
String that must **not** be included in the response's content. If this string
is present in the page when trying to login, it returns as having failed and no
search queries will be sent.


.. _userdata: http://kodi.wiki/view/Userdata
