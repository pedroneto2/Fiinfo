import requests
import re
import ssl
import json
import math
import copy
import functools
import urllib.request
from lxml import html

class DataBuilder:
    def __init__(self):
        self.site = 'https://www.fundsexplorer.com.br/funds/'
        self.session = requests.Session()
        self.ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.ctx.options |= 0x4
        self.baseDataHeaders =  {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        self.dividendsHeaders = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            "X-Fiis-Nonce": "61495f60b533cc40ad822e054998a3190ea9bca0d94791a1da"
        }
        
        self.ntnbTax = float(self.getNtnbTax())
        self.ipca = float(self.getIPCA12())
    
    def getIPCA12(self):
        site = 'https://www.ibge.gov.br/explica/inflacao.php'
        response = urllib.request.urlopen(site, context=self.ctx)
        tree = html.fromstring(response.read())
        rawIpca = tree.xpath('/html/body/header/div[4]/ul/li[2]/p[1]/text()')
        ipca = float(rawIpca[0].split('%')[0].replace(',','.'))
        return ipca
    
    def getNtnbTax(self):
        response = requests.get('https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/service/api/treasurybondsinfo.json')
        json = response.json()
        trsrList = json['response']['TrsrBdTradgList']
        for i in trsrList:
            if i['TrsrBd']['cd'] == 138:
                ntnbTax = i['TrsrBd']['anulInvstmtRate']
        return round(float(ntnbTax), 2)
    
    def getBaseData(self, ticker, premio):
        fullUrl = self.site + ticker
        response = self.session.get(fullUrl, headers = self.baseDataHeaders)
        tree = html.fromstring(response.text)
        rawValorAtual = tree.xpath('/html/body/section[1]/div/div/div[1]/div[1]/p/text()')
        rawYield12 = tree.xpath('/html/body/section[5]/div/div[2]/div/div/div/div/div/div[3]/div[5]/text()')
        rawPVp = tree.xpath('/html/body/section[2]/div/div[7]/p[2]/b/text()')
        valorAtual = float(rawValorAtual[0].split('R$ ')[1].replace(',','.'))
        yield12 = float(re.search("\d+.\d+", rawYield12[0]).group().replace(',','.'))
        pVp = float(re.search("\d+.\d+", rawPVp[0]).group().replace(',','.'))
        return [round(valorAtual, 2), round(yield12, 2), round(pVp, 2)]
    
    def calculateBaseData(self, yield12, premio, addIpcaToPremio, valorAtual):
        valorAtual = float(valorAtual)
        ipca = self.ipca if bool(addIpcaToPremio) else 0
        precoTeto = (float(yield12) / (self.ntnbTax + float(premio) + ipca)) * valorAtual
        tetoValor = precoTeto / valorAtual
        return [round(precoTeto, 2), round(tetoValor, 2)]
    
    def calculateProjectedData(self, rendimento12Projected, premio, addIpcaToPremio, valorAtual):
        valorAtual = float(valorAtual)
        ipca = self.ipca if bool(addIpcaToPremio) else 0
        yield12Projected = float(rendimento12Projected) * 100 / valorAtual
        precoTetoProjected = (yield12Projected / (self.ntnbTax + float(premio) + ipca)) * valorAtual
        tetoProjetadoValor = precoTetoProjected / valorAtual
        return [round(yield12Projected, 2), round(precoTetoProjected, 2), round(tetoProjetadoValor, 2)]
        
    def getNext12MProjectedIncome(self, ticker):
        url = f"https://fiis.com.br/wp-json/fiis/v1/funds/{ticker}/incomes"
        response = self.session.get(url, headers=self.dividendsHeaders)
        parsedResponse = json.loads(response.json())
        incomesObj = parsedResponse['incomes']
        def extractIncomes(incomeObj, field):
            return float(incomeObj[field])
        incomes = list(map(lambda a : extractIncomes(a, 'rendimento'), incomesObj))
        copiedIncomes = copy.copy(incomes)
        yearIncomes = []
        def filterOutliers(array):
            if len(array) < 4:
                return array
            copiedArray = copy.copy(array)
            copiedArray.sort()
            q1 = copiedArray[math.floor(len(copiedArray) / 4)]
            q3 = copiedArray[math.ceil(len(copiedArray) * 3/ 4)]
            iqr = q3 - q1
            maxValue = q3 + iqr * 0.6
            minValue = q1 - iqr * 0.6
            def filterMaxMin(value):
                return value >= minValue and value <= maxValue
            return list(filter(filterMaxMin, copiedArray))
        def calculatMediums(values):
            return functools.reduce(lambda a, b: a+b, values) / len(values)
        if len(incomes) >= 3 * 12:
            incomesYearsCount = math.trunc(len(incomes)/12)
            for i in range(incomesYearsCount):
                yearIncomes.append(copiedIncomes[-12:])
                copiedIncomes[-12:] = []
            mediumIncomes = list(map(calculatMediums, yearIncomes))
        else:
            mediumIncomes = filterOutliers(incomes)
        def simpleLinearRegression(y):
            n = len(y)
            sumX, sumY, sumXY, sumXX, sumYY = 0, 0, 0, 0, 0
            for i in range(n):
                sumX += i + 1
                sumY += y[i]
                sumXY += (i+1) * y[i]
                sumXX += (i+1) ** 2
                sumYY += y[i] ** 2
            meanX = sumX / n
            meanY = sumY / n
            slope = (sumXY - n * meanX * meanY) / (sumXX - n * meanX * meanX)
            intercept = meanY - slope * meanX
            return [slope, intercept]
        def simpleLinearRegressionPredict(slope, intercept, x):
            return slope * x + intercept
        mediumIncomes.reverse()
        incomesSlope, incomesIntercept = simpleLinearRegression(mediumIncomes)
        if len(incomes) >= 3 * 12:
            incomesNextPointPredictium = len(mediumIncomes) + 1
            next12MMediumIncome = simpleLinearRegressionPredict(incomesSlope, incomesIntercept, incomesNextPointPredictium) * 12
        else:
            next12points = []
            for i in range(12):
                incomesNextPointPredictium = len(mediumIncomes) + i + 1
                pointIncome = simpleLinearRegressionPredict(incomesSlope, incomesIntercept, incomesNextPointPredictium)
                next12points.append(pointIncome)
            next12MMediumIncome = functools.reduce(lambda a, b: a+b, next12points)
        return next12MMediumIncome