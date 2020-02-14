from datetime import datetime, timedelta
from random import randint
import re
from discord.ext import commands
from discord import Embed
from constants import *
import parse
import utils


class RSSCrawler:
    """
    Commands dealing with fetching rss feeds

    Supports:
        - ATP (!atp)
        - MECO (!meco)
        - MBMBAM (!mbmbam)
        - Off-Nominal (!on)
        - The Adventure Zone (!taz)
        - We Martians (!wm)
        + xkcd (!xkcd)  <- NOT IMPLEMENTED
    """
    def __init__(self, bot):
        self.bot = bot
        self.feeds = [
            Podcast("Accidental Tech Podcast",
                    "http://atp.fm/episodes?format=rss",
                    color=0x203D65),
            Podcast("KSP History",
                    "https://dwcamp.net/feeds/ksp_history.xml",
                    color=0x339BDC),
            Podcast("Main Engine Cutoff",
                    "https://feeds.simplecast.com/Zg9AF5cA",
                    color=0x9FB1C2),
            Podcast("My Brother My Brother and Me",
                    "https://feeds.simplecast.com/wjQvYtdl",
                    color=0x4B4B4B),
            Podcast("Off-Nominal",
                    "https://feeds.simplecast.com/iyz_ESAp",
                    color=0x716C4F),
            Podcast("The Adventure Zone",
                    "https://feeds.simplecast.com/cYQVc__c"),
            Podcast("We Martians",
                    "https://www.wemartians.com/feed/podcast/",
                    color=0xC4511F),
            Podcast("xkcd",
                    "https://dwcamp.net/feeds/xkcd.xml",
                    color=0xFFFFFF),
        ]

    # Searches for an item in your favorite RSS Feeds
    @commands.command(pass_context=True, help=LONG_HELP['rssfeed'],
                      brief=BRIEF_HELP['rssfeed'], aliases=ALIASES["rssfeed"])
    async def rssfeed(self, ctx):
        try:
            invoking_id = ctx.invoked_with
            for feed in self.feeds:
                if invoking_id in feed.aliases:
                    await self.handle_rss_feed(feed, ctx)
                    return
            await self.bot.say("This command can be used to search for episodes of your favorite feed. It " +
                               "currently supports the following channels:\n" + FEED_TEXT_LIST)
        except Exception as e:
            await utils.report(self.bot, str(e), source="rssfeed command", ctx=ctx)

    async def handle_rss_feed(self, feed, ctx):
        """
        The universal rss feed handler. Takes in an RSSFeed object
        then does all the magic
        :param feed: The RSSFeed
        :param ctx: The ctx object of the inciting message
        """
        try:
            message = parse.stripcommand(ctx.message.content)

            # Oops no parameter
            if message == "":
                await self.bot.say(
                    "Usage: `!" + feed.aliases[0] + " <number>`")
                return

            # Update feed
            feed.refresh_if_stale()

            # check for subcommand and parse it out
            subcommand = ""
            parameter = message
            if message[0] == "-":
                whitespace = utils.first_whitespace(message)
                if whitespace == -1:
                    subcommand = message[1:]
                    parameter = ""
                else:
                    subcommand = message[1:whitespace]
                    parameter = message[whitespace:].strip()

            # Teach the person how to use this thing
            if subcommand == "help":
                await self.bot.say("Search for an item by typing a search term")
                return

            # Check the age
            if subcommand == "age":
                await self.bot.say(f"{feed.fetchtime}\n{feed.is_stale()}")
                return

            # Check the age
            if subcommand == "bozo":
                if feed.feed.bozo:
                    await self.bot.say(f"Detected error: {feed.feed.bozo_exception}")
                else:
                    await self.bot.say("There were no issues parsing this feed")
                return

            # Post all of the keys for the channel dict
            if subcommand == "channel":
                await self.bot.say("Channel Deets:\n" + " | ".join(feed.feed["channel"].keys()))
                return

            # Post all of the keys for the item dict
            if subcommand == "deets":
                await self.bot.say(" | ".join(feed.items[0].keys()))
                return

            # Dump all the info about the feed
            if subcommand == "dump":
                await self.bot.say(feed.to_string())
                return

            # Test an embed for a given feed
            if subcommand == "embed":
                await self.bot.say(embed=feed.get_embed(feed.items[0]))
                return

            # Post all of the keys for the feed dict
            if subcommand == "feed":
                await self.bot.say("Feed Deets:\n" + " | ".join(feed.feed.keys()))
                return

            # Prints the text of the field requested for the first item in the feed
            if subcommand == "print":
                await self.bot.say(utils.trimtolength(feed.items[0][parameter], 1000))
                return

            # If some nerd like Kris or Pat wants to do regex search
            if subcommand == "r":
                episode = feed.search(parameter, regex=True)
                if episode:
                    await self.bot.say(embed=feed.get_embed(episode))
                    return
                await self.bot.say(f"I couldn't find any results for the regex string `{parameter}`")

            # Force a refresh on the feed
            if subcommand == "refresh":
                feed.refresh()
                await self.bot.say(f"Alright, I have refreshed the feed `{feed.feed_id}`")
                return

            # Returns search results that the user can select
            if subcommand == "search":
                await self.bot.say("This has not been implemented yet :sad:")
                return

            # If there was a subcommand but it was unrecognized
            if subcommand != "":
                await self.bot.say(f"I'm sorry, I don't understand the subcommand `{subcommand}`. " +
                                   f"Please consult `-help` for more information")
                return

            # Search for the term
            episode = feed.search(parameter)
            if episode:
                await self.bot.say(embed=feed.get_embed(episode))
                return
            await self.bot.say(f"I couldn't find any results in the {feed.title} feed "
                               f"for the term `{parameter}` :worried:")

        except Exception as e:
            await utils.report(self.bot, str(e), source=f"handle_rss_feed() for '{feed.feed_id}'", ctx=ctx)


class RSSFeed:
    """
    Creates an object representing a podcast feed

    :param feed_id: The id used to store information about the feed
    :param url: The url of the feed
    :param color: The color of the embed for episodes
    :param ttl: A timedelta object representing how long the cache
        can last before it is considered "stale". Defaults to 1 minute
    """
    def __init__(self, feed_id, url, color=EMBED_COLORS["default"], ttl=timedelta(hours=1)):
        self.feed_id = feed_id
        self.feed_url = url
        self.aliases = FEED_ALIAS_LIST[feed_id]
        self.color = color
        self.ttl = ttl

        # RSS Info. These values are not defined at init and
        # must be fetched by refreshing the feed

        self.feed = None  # The feed dictionary
        self.fetch_time = None  # When the item was fetched
        self.title = feed_id  # The title of the feed (temporarily set to feed_id)
        self.description = None  # The description of the feed
        self.image = None  # The covert art for the feed
        self.link = None  # The website associated with the feed
        self.items = None  # The list of items in the feed

    def __len__(self):
        """
        Support len(RSSFeed)
        :return:
        """
        return len(self.items)

    def search(self, term, regex=False):
        """
        Finds the most recent item in the feed whose title contains the search term
        This search is for whole words only (unless using regex search)

        :param term: The term being searched for
        :param regex: Whether to regex escape the search term. For the true nerds
            Defaults to False
        :return: If it finds an appropriate episode, it returns it.
            If it can't find any matching episode, it returns null
        """
        if regex:
            pattern = re.compile(term)
        else:
            pattern = re.compile("(?<!\w)" + re.escape(term) + "(?!\w)", re.IGNORECASE)

        for item in self.items:
            if re.search(pattern, item["title"]):
                return item
        return

    def to_string(self):
        string = f"""
Title: {self.title}
Item Count: {len(self.items)}
Fetch time: {self.fetch_time}
"""
        return string

    def is_stale(self):
        """
        Checks if the information is stale (older than 24 hours)
        :return: Returns 'True' if the stored data was cached more than 24 hours ago
        """
        if self.feed is None:
            return True
        return datetime.today() > self.fetch_time + self.ttl

    def refresh(self):
        """
        Updates the cached data
        :return:
        """
        self.feed = utils.get_rss_feed(self.feed_url)
        self.fetch_time = datetime.today()
        if "channel" in self.feed:
            self.title = self.feed["channel"]["title"]
            self.description = self.feed["channel"]["description"]
            if "image" in self.feed["channel"]:
                self.image = self.feed["channel"]["image"]["url"]
            self.link = self.feed["channel"]["link"]
        self.items = self.feed["items"]

    def refresh_if_stale(self):
        """
        Helper method. Only refreshes information if cache is 'data' (i.e. data is older than max_age)
        """
        if self.is_stale():
            self.refresh()

    def get_embed(self, item):
        """
        Generates an embed containing information about the provided item
        :param item: An item from this feed
        :return: An embed of information about it
        """
        embed = Embed()
        embed.colour = self.color
        if self.image:
            embed.set_author(name=self.title, url=self.link, icon_url=self.image)
        else:
            embed.set_author(name=self.title, url=self.link)
        embed.title = item["title"]
        embed.url = self.link
        if "image" in item.keys():
            embed.set_image(url=item["image"])
            embed.set_footer(text=utils.trimtolength(f"{self.title} - {self.description}", 256))
        return embed


class Podcast(RSSFeed):

    def get_embed(self, episode):
        """
        Generates an embed for a given episode of a podcast

        :param episode: ([str : Any]) The dictionary of information for the episode
        :return: Embed
        """
        embed = Embed()

        # Appearance
        embed.colour = self.color
        description = episode["subtitle"] if "subtitle" in episode else episode["summary"]
        embed.description = utils.trimtolength(description, 2048)
        embed.set_thumbnail(url=self.image)

        # Data
        embed.title = episode["title"]
        embed.url = episode["link"]
        embed.set_author(name=self.title, url=self.link)

        time_obj = episode["published_parsed"]
        pub_str = f"{time_obj.tm_mon}/{time_obj.tm_mday}/{time_obj.tm_year}"

        embed.add_field(name="Published", value=pub_str)
        embed.add_field(name="Quality", value=f"{randint(20, 100) / 10}/10")

        # Image enclosure
        # Discord just ignores URLs it can't handle
        if episode.enclosures:
            embed.set_image(url=episode.enclosures[0].href)

        return embed


def setup(bot):
    bot.add_cog(RSSCrawler(bot))
