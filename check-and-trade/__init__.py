import datetime
import logging
import azure.functions as func
import alpaca_trade_api as alpaca
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import os
import requests

class Statistic:

    def __init__(self, api: alpaca.REST ) -> None:
        self.api = api

    def getMovingAverage(tkr, period) -> float:
        url = 'https://www.alphavantage.co/query?function=SMA&symbol=%s&interval=daily&time_period=%i&series_type=close&apikey=V6V3OG1MINVI8JE9' %(tkr, period)
        
        ## checks if response is good
        r = requests.get(url)
        if not r.ok:
            raise Exception(f'ERROR: Requesting {url}\nStatus Code {r.status_code}') 

        ## gets data from response 
        data = r.json()
        movingAverage = data["Technical Analysis: SMA"]

        ## gets the previous day
        startDate = datetime.date.today()
        delta = datetime.timedelta(1)

        return float(movingAverage[str(startDate-delta)]['SMA'])


    ## returns 0 for rno cross, 1 for small moving above large and -1 for small moving below large
    def getMovingAverageCross(tkr, longPeriod: int, shortPeriod: int) -> int:  
        
        url = 'https://www.alphavantage.co/query?function=SMA&symbol=%s&interval=daily&time_period=%i&series_type=close&apikey=V6V3OG1MINVI8JE9' %(tkr, shortPeriod)
    
        ## checks if response is good
        r = requests.get(url)
        if not r.ok:
            raise Exception(f'ERROR: Requesting {url}\nStatus Code {r.status_code}') 

        ## gets data from response 
        data = r.json()
        shortMovingAverage = data["Technical Analysis: SMA"]



        url = 'https://www.alphavantage.co/query?function=SMA&symbol=%s&interval=daily&time_period=%i&series_type=close&apikey=V6V3OG1MINVI8JE9' %(tkr, longPeriod)

        ## checks if response is good
        r = requests.get(url)
        if not r.ok:
            raise Exception(f'ERROR: Requesting {url}\nStatus Code {r.status_code}') 

        ## gets data from response 
        data = r.json()
        longMovingAverage = data["Technical Analysis: SMA"]

        ## gets the previous day
        startDate = datetime.date.today()
        delta = datetime.timedelta(1)

        SmallMovedToTop =  float(shortMovingAverage[str(startDate-delta)]['SMA']) > float(longMovingAverage[str(startDate-delta)]['SMA']) and float(shortMovingAverage[str(startDate-(2*delta))]['SMA']) < float(longMovingAverage[str(startDate-(2*delta))]['SMA'])
        SmallMovedToBot =  float(shortMovingAverage[str(startDate-delta)]['SMA']) < float(longMovingAverage[str(startDate-delta)]['SMA']) and float(shortMovingAverage[str(startDate-(2*delta))]['SMA']) > float(longMovingAverage[str(startDate-(2*delta))]['SMA'])
        
        if SmallMovedToTop: return 1
        elif SmallMovedToBot: return -1
        else: return 0

    def getMovingAveragePriceCross(api: alpaca.REST, tkr, period):
          
        url = 'https://www.alphavantage.co/query?function=SMA&symbol=%s&interval=daily&time_period=%i&series_type=close&apikey=V6V3OG1MINVI8JE9' %(tkr, period)
    
        ## checks if response is good
        r = requests.get(url)
        if not r.ok:
            raise Exception(f'ERROR: Requesting {url}\nStatus Code {r.status_code}') 

        ## gets data from response 
        data = r.json()
        movingAverage = data["Technical Analysis: SMA"]


        ## gets current price and see's if it crossed the ave
        startDate = datetime.date.today() -  datetime.timedelta(1)
        bars = api.get_bars(symbol=tkr, timeframe=alpaca.TimeFrame(15, alpaca.TimeFrameUnit.Minute),start=startDate.isoformat())

        numDataPoints = len(bars)
        prevPrice = float(bars[numDataPoints-1]._raw['c'])
        currPrice = float(api.get_latest_trade(symbol=tkr)._raw["p"])


        priceMovedAboveAve =  float(movingAverage[str(startDate)]['SMA']) < currPrice and float(movingAverage[str(startDate - datetime.timedelta(1))]['SMA']) > prevPrice
        priceMovedBelowAve =  float(movingAverage[str(startDate)]['SMA']) > currPrice and float(movingAverage[str(startDate - datetime.timedelta(1
        ))]['SMA']) < prevPrice
        
        if priceMovedAboveAve: return 1
        elif priceMovedBelowAve: return -1
        else: return 0

    def getStdvPercentChange(api: alpaca.REST, tkr: str, period: int)-> float:

        startDate = datetime.date.today()
        delta = datetime.timedelta(2*period)

        calenderEntity = api.get_calendar(start=startDate-delta, end=startDate) 
        dateObj = calenderEntity[len(calenderEntity)-period]._raw
        
        bars = api.get_bars(symbol=tkr, timeframe=alpaca.TimeFrame(1, alpaca.TimeFrameUnit.Day),start=dateObj["date"])

        meanChange = Statistic.getAveragePercentChange(api, tkr, period)
        sumOfSquares = 0.0
        
        for i in range(period-1): sumOfSquares += (((float(bars[i+1]._raw['o']) - float(bars[i]._raw['o'])) / float(bars[i]._raw['o']))- meanChange)**2 
        return (sumOfSquares/(period-1))** (1/2)





    def getAveragePercentChange(api: alpaca.REST, tkr: str, period: int) -> float:
       
        startDate = datetime.date.today()
        delta = datetime.timedelta(2*period)

        calenderEntity = api.get_calendar(start=startDate-delta, end=startDate)
        dateObj = calenderEntity[len(calenderEntity)-period]._raw
        
        bars = api.get_bars(symbol=tkr, timeframe=alpaca.TimeFrame(1, alpaca.TimeFrameUnit.Day),start=dateObj["date"])

        sum = 0.0
        for i in range(period-1): sum += (float(bars[i+1]._raw['o']) - float(bars[i]._raw['o'])) / float(bars[i]._raw['o']) 
    
        return sum/(period -1)


    def getAverageTrueRange(self) -> float:
        pass




def main(mytimer: func.TimerRequest) -> None:

    os.environ['APCA_API_BASE_URL'] = 'https://paper-api.alpaca.markets'


    api = alpaca.REST(key_id=os.environ["apiKey"], secret_key=os.environ["apiSecret"], api_version='v2')


    sender_address = 'alpacatradebot@gmail.com' 
    sender_pass = os.environ["emailPassword"]
    receiver_address = 'fee00003@umn.edu'

    # Setup MIME
    message = MIMEMultipart()
    message['From'] = 'Trading Bot'
    message['To'] = receiver_address
    message['Subject'] = 'Trade'  

    mail_content = ""

    if api.get_clock().is_open:


        crossRes = Statistic.getMovingAveragePriceCross(api, tkr="SPXL", period=5)
        logging.info('Cross result: {cross} \n time: {time}'.format(cross=crossRes, time= datetime.datetime.now()))
        mail_content = 'Cross result: {cross} \n time: {time}'.format(cross=crossRes, time= datetime.datetime.now())

        traded = False
        if crossRes == 1 and api.get_position("SPXL")["qty"] == 0:
            ## buy 
            print ("buy")
            traded = True
            api.submit_order(
                symbol='SPXL',
                qty=5.0,  # fractional shares
                side='buy',
                type='market',
                time_in_force='day',
            )
            
        elif crossRes == -1 and api.get_position("SPXL")["qty"] != 0: 
            ## sell
            traded = True
            print ("sell")
            api.submit_order(
                symbol='SPXL',
                qty=5.0,  # fractional shares
                side='sell',
                type='market',
                time_in_force='day',
            )

        if traded:
                message.attach(MIMEText(mail_content, 'plain'))

                # Create SMTP session for sending the mail
                session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
                session.starttls()  # enable security

                # login with mail_id and password
                session.login(sender_address, sender_pass)
                text = message.as_string()
                session.sendmail(sender_address, receiver_address, text)
                session.quit()
                logging.info("Email sent")  

