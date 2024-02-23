import time as balls
from datetime import datetime, date
import requests, bs4
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


today = date.today()
LINK = ("https://servizi.startromagna.it/corsesoppresse/corsesopp?param1=Forli-Cesena&param2=" + str(today))
TOKEN = "7008079155:AAHAJAZN6jsAMOkw9vtDyOgKlBQeBynOAp0" 


def getVariations():
    response = requests.get(LINK)
    response.raise_for_status()

    soup = bs4.BeautifulSoup(response.text, 'html.parser')
    tab = soup.find('table', class_='table table-bordered table-condensed table-responsive table-hover')
    tab_busses = tab.find_all('td')

    text = ""
    for i in range(len(tab_busses)):
        if(tab_busses[i].text == "3 Cesena"):
            if(tab_busses[i+2].text == "07:00" or tab_busses[i+2].text == "07:15" or tab_busses[i+2].text == "07:30" or tab_busses[i+2].text == "07:45" or tab_busses[i+2].text == "08:00"):
                text += "La corriera delle " + tab_busses[i+2].text + ", in partenza da" + tab_busses[i+1].text + " e diretta verso " + tab_busses[i+3].text + " è stata soppressa" + "\n \n"
    
    return text



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        msg = getVariations()
        await update.message.reply_html(
            rf"Da ora in poi riceverai un messaggio per le variazioni",
            reply_markup=ForceReply(selective=True),
        )
        
        while True:
            
            time = datetime.now().time()
            right_time = str(time)[:-10]
            
            #fai una richiesta all'ora
            if((int(right_time[3])*10 + int(right_time[4])) % 60 == 0):
                 msg = getVariations()

            if( right_time == "6:30" or right_time == "22:00"):
                await update.message.reply_html(
                    rf"{msg}",
                    reply_markup=ForceReply(selective=True),
                )
             
            balls.sleep(60)





application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.run_polling(allowed_updates=Update.ALL_TYPES)





