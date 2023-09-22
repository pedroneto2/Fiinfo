import requests
from lxml import html

class DataBuilder:
    def __init__(self):
        self.site = 'https://www.fundsexplorer.com.br/funds/'
        self.session = requests.Session()
        self.headers =  {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
    
    def getPrice(self, ticker):
        fullUrl = self.site + ticker
        response = self.session.get(fullUrl, headers = self.headers)
        tree = html.fromstring(response.text)
        rawPrice = tree.xpath('/html/body/section[1]/div/div/div[1]/div[1]/p/text()')
        price = float(rawPrice[0].split('R$ ')[1].replace(',','.'))
        return price