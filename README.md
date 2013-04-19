# Contributor's guide to Aligulac.com

Contributing to Aligulac can take several forms.

* [Maintaining the database.](#maintaining-the-database)
* [Developing the website.](#developing-the-website)
* [Other types of work.](#other)

These are described in the relevant sections below.

## Maintaining the database

Aligulac maintains a fairly extensive progaming database tracking the following:

* Matches and results (these terms are used interchangeably). By *match* is
  meant a series of games. That is, Aligulac does not track individual games.
* Players
* Teams
* Events, including prizepools.

Essentially, the most routine updates that must be made happen when matches are
played in a tournament, or when team transfers occur. More exceptional cases
include teams forming or disbanding, players changing race or nicknames, or
major changes to tournament structures.

### Players

Most of the information about a player can be changed directly on a player's
page if you are logged in, by clicking the **edit** link above the infobox. If
something can't be changed there, it must be changed in the admin interface (use
the **admin** link).

The most critical pieces of information for a player are

* their in-game tag, which should be updated to reflect the most frequent usage
  by the players themselves.
* their race and nationality.
* their team affiliation.

When changing team, you must use the admin interface. When a player leaves team
A, mark the membership record of team A as **not current** and enter the final
date. When someone joins team B, add a new record with the proper starting date
and with **current** set to true. 

**NOTE:** The rating system will look ONLY at the **current** field to check
whether a membership is in effect, the dates are merely for recordkeeping and
have no impact on anything.

**NOTE:** When changing a player's race, past matches will remain unaffected.

## Developing the website

This is the source code for the website http://aligulac.com

Needs:

- Python 2.6 or 2.7
- Django 1.4.x
- A MySQL server
- Python modules: numpy, scipy, markdown and pyparsing

The repository does **not** contain the Django settings file or the database dumps.

## Other
