import unittest

from discord import Message

from embed_generator import AmazonEmbedGenerator


class TestEmbedGenerator(unittest.TestCase):
    def _test_regex_match(self, embed_generator, content, expected):
        test_message = Message(content=content, reactions=[])
        generator = embed_generator(test_message)
        self.assertEqual(generator.get_regex_matches(), expected)

    def test_amazon(self):
        self._test_regex_match(AmazonEmbedGenerator,
                               "test",
                               [])

        self._test_regex_match(AmazonEmbedGenerator,
                               "https://www.amazon.com/dp/product/B00008S2V6/",
                               ["https://www.amazon.com/dp/product/B00008S2V6"])

        self._test_regex_match(AmazonEmbedGenerator,
                               "Try out this link! https://www.amazon.com/Plate-Bracket-Ecobee-Thermostat-White-Ecobee4/dp/B0757D95SB/ref=b2b_gw_d_simh_1/133-0853113-5387851?_encoding=UTF8&pd_rd_i=B0757D95SB&pd_rd_r=6c63793e-bdf5-4601-b3a3-e4656671dcce&pd_rd_w=DPBi4&pd_rd_wg=vssa0&pf_rd_p=3f97c4f2-7cd8-4441-ac9a-df77ca233406&pf_rd_r=N6Q52A4HT118Q7AVHNRJ&psc=1&refRID=1FRR284PJ2MTDT439T60, okay, man!",
                               ["https://www.amazon.com/Plate-Bracket-Ecobee-Thermostat-White-Ecobee4/dp/B0757D95SB"])

        self._test_regex_match(AmazonEmbedGenerator,
                               "Try https://www.amazon.com/dp/product/B00008S2V6/ and https://www.amazon.com/Plate-Bracket-Ecobee-Thermostat-White-Ecobee4/dp/B0757D95SB",
                               ["https://www.amazon.com/dp/product/B00008S2V6",
                                "https://www.amazon.com/Plate-Bracket-Ecobee-Thermostat-White-Ecobee4/dp/B0757D95SB"])


if __name__ == '__main__':
    unittest.main()
