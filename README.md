# Contributor's guide to Aligulac.com

## Overview

Contributing to Aligulac can take several forms.

* [Maintaining the database.](#maintaining-the-database)
* [Developing the website.](#developing-the-website)
* [Other types of work.](#other)

These are described in the relevant sections below.

## Meeting places

The most active forum for Aligulac contributors to meet and coordinate is our
Skype chat. To get in, just add TheBB on Skype. His username is *evfonn*.

There is also an IRC channel on quakenet: #aligulac. It is not as active, but
favored by some.

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

**NOTE:** If you are very unsure about a player's identity when you add a new
match, it is probably best to create a new player than to add to an existing
one. It is easy to merge players later ([here](http://aligulac.com/add/misc/)),
but hard to separate them.

**NOTE:** Players can be automatically created when submitting matches. It's not
necessary to do this manually.

### Events

The events system is one of the most complicated parts of Aligulac, and also one
of the things that separate it from its "competitors".

Every match should be assigned to one and only one event. This means that the
term *event* has a somewhat broader usage here than elsewhere. Particularly,
events may represent both rounds and organizers.

Events are organized in a tree structure. For example:

GSL → 2013 → Season 1 → Code S → Ro16 → Group A  
Proleage → 2011-2012 Hybrid Season 2 → Round 2 → Week 4 → Samsung KHAN vs. CJ
Entus

Matches are assigned **only** to the leaf nodes, i.e. those events who have no
children. When they are displayed anywhere on the site, the full name of the
event is the concatenation of the whole chain back to the root. Thus, a match
assigned to the Group A given above, will be shown as "GSL 2013 Season 1 Code S
Ro16 Group A" on the site.

The event tree can be manipulated via 
[this tool](http://aligulac.com/add/events/), or directly on an event page. It
is strongly discouraged to use the admin interface for this. Even so, bugs or
consistency errors may occur. In these cases, always restore the NSM and the
event name cache [here](http://aligulac.com/add/misc/) before attempting
anything else. These buttons will fix 99% of all errors.

#### How do I set up an event tree?

Use the [event manager tool](http://aligulac.com/add/events/). Try to name your
events so that the full names will flow as easily as possible. However, remember
that the hierarchy must be maintained. If it helps, you can set an event as
**noprint**. This will "hide" it from the names of subevents.

Some common issues and naming conventions:

* If a tournament has qualifiers and a main part, split it into "Qualifiers" and
  "Main Tournament", the latter of which should be set to **noprint**.
* Qualifiers → NA/EU/Korea, instead of "NA/EU/Korean qualifiers".
* Similarly, if you want to split an event into "Group Stage" and "Playoffs",
  both should be set to **noprint**.
* Ro16 with small o.
* "Third place match", not "3rd".

**NOTE:** When an event is finished, it is closed. That means it will no longer
show up in the events manager or the drop-down boxes around the site. This is
done to prevent cluttering. If you need to reopen an event, navigate to it and
open it from the admin interface.

#### What are event types?

Each event has one of three possible types: category, event (yes, this one is
confusing) and round. The idea is that events of type "event" represent a
tournament with an attached prize pool. Parents of event type events must be
categories, and they represent such things as seasons, years, organizers, etc.
Children of event type events must be rounds, and they represent... well...
rounds.

**NOTE:** Only events of type "event" can have associated prize pools.

#### How do I add or change a prize pool?

Navigate to the event page. You should see buttons to add or change ranked or
unranked prize pools. You will be asked how many slots, and then you can enter
the prize in a given currency, as well as the winners.

**NOTE:** Historical exchange rates are automatically used for conversion. Prize
pools should always be added in the actual currency used.

### Matches

Most of the time spent maintaining the database is in adding results. This is
done [here](http://aligulac.com/add/). This page is also available to the public
(with slightly different options). When someone unauthenticated adds results,
they are filed away to review [here](http://aligulac.com/add/review/). The
process for adding new matches and reviewing them is fairly similar.

The syntax for adding matches is described in depth on the submission page.

**NOTE:** Try to verify game was actually played if possible, do not add walkover games.

### Other

#### Aliases

All teams and players have **aliases**, or **AKA**s, which can be modified
directly on the player or team page. When you add an alias, that player or team
will be searchable under that alias.

Many of the bigger teams will have one or more aliases, e.g. "tl", "liquid",
"im", "lgim" and "lg-im". For players it's less common, but sometimes useful,
for example with common fan names such as "DRG", and when players change names
(BaBy → TY as well as a host of other examples).

If you find looking up a player or team is awkward, consider adding an alias
instead of working around the issue.

#### Match → Event assignment

One of our largest long-term projects involves the assignment of historical
matches to the event tree. At the time of writing, 9305 matches remain
unassigned ([exact number here](http://aligulac.com/db/)). It's a stated goal of
ours to push this number to zero.

The most useful tool in this project is the 
[results search](http://aligulac.com/results/search/). Just restrict it to
unassigned matches, and set a reasonable timeframe (so that the search set isn't
too large). Pick a set of events that you would like to categorize, create the
event tree and get cracking!

While you are doing this, you will probably note inconsistencies that have to be
fixed, such as:

* The offline/online status of a match must be updated.
* Some duplicate entries probably exist.
* Dates are wrong.

This form of digging in the archives involves a fair amount of detective work,
where Liquipedia and TLPD can be extremely helpful. It can be both tedious and
interesting. However, in most cases, the matches already have event information,
and all you need to do is create the event tree and assign them.

## Developing the website

(Unfinished section.)

This is the source code for the website http://aligulac.com

The requirements are described in the requirements.txt file. It can be used directly with pip.

Needs:

- Python 2.6 or 2.7
- Django 1.8.x
- A MySQL server
- Python modules:
    * ccy
    * dateutil
    * markdown
    * mysqldb
    * numpy
    * pyparsing
    * scipy
    * simplejson

The repository does **not** contain the Django settings file or the database dumps. Templates are provided in [default.settings.py](aligulac/aligulac/default.settings.py) and [template.local.py](aligulac/aligulac/template.local.py)

## Other

(Unfinished section.)
