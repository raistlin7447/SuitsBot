import re
from typing import List, Optional

from bs4 import BeautifulSoup
from discord import Embed, Message

import utils
from constants import EMBED_COLORS
from embedGenerator import recently_unfurled


class EmbedGenerator(object):
    """
    Given a Discord Message object, generate appropriate embeds to respond with.
    """
    REGEX = None    # The regex to match text for this generator to trigger
    FIELD = None    # The field to extract out of the match

    def __init__(self, message: Message):
        self.message = message
        self.content = self.message.content

    def get_regex_matches(self) -> List[str]:
        """
        Get all matches on message content and return us a list.
        :return: list of matches as strings
        """
        matches = re.findall(self.REGEX, self.content)
        if self.FIELD is None:
            return matches
        else:
            return [match[self.FIELD] for match in matches]

    async def get_embed(self, link: str) -> Optional[Embed]:
        """
        Given a string return an appropriate embed.
        :param link:
        :return: an embed
        """
        raise NotImplementedError()

    async def get_embeds(self) -> List[Embed]:
        """
        Returns a list of embeds generated from the message content.
        :return: A list of embeds
        """
        embed_list = list()
        for match in self.get_regex_matches():
            link = match.strip()
            if await recently_unfurled(f"{self.message.channel.id}-{self.__class__.__name__}-{link}"):
                continue
            embed = await self.get_embed(link)
            if embed is not None:
                if isinstance(embed, list):
                    for item in embed:
                        embed_list.append(item)
                else:
                    embed_list.append(embed)
        return embed_list


class AmazonEmbedGenerator(EmbedGenerator):
    REGEX = re.compile(r'https://www\.amazon\.com/(?:(?:\w+-)+\w+/)?[dg]p/(?:product/)?(?:\w{10})')
    FIELD = None

    async def get_embed(self, url: str) -> Optional[Embed]:
        """
        Generates an embed describing an item listing at an Amazon URL

        :param url: The url of the item listing
        :return: An embed with details about the item
        """
        text = await utils.get_website_text(url)
        if text is None:
            return None
        embed = Embed()

        # ==== Properties

        embed.url = url
        embed.colour = EMBED_COLORS['amazon']
        soup = BeautifulSoup(text, 'html.parser')
        embed.title = soup.find(id='productTitle').text.strip()
        embed.set_thumbnail(url=soup.find(id='landingImage').get('src'))

        # ==== Description

        descdiv = soup.find(id='productDescription')
        if descdiv is not None:
            ptag = descdiv.p
            if ptag is not None:
                embed.description = utils.trimtolength(ptag.text, 2048)

        # ==== Fields

        # Product Vendor
        vendor = soup.find(id='bylineInfo')
        if vendor is not None:
            embed.add_field(name="Vendor", value=vendor.text)

        # Price
        price = soup.find(id='priceblock_ourprice')
        if price is not None:
            embed.add_field(name="Price", value=price.text)
        else:
            price = soup.find(id='priceblock_dealprice')
            if price is not None:
                embed.add_field(name="Price", value=price.text)

        # Star rating
        rating = soup.find(id='acrPopover')
        if rating is not None:
            embed.add_field(name="Rating", value=rating['title'])
        return embed
