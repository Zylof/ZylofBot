# coding=UTF8

import asyncio
import codecs
import datetime
import glob
import math
import os
import random
import re
import sys
import time
import threading

import discord
import pyimgur
import requests
from lxml import etree, html


#############################
CURRENTFOLDERDIR = os.getcwd()
# This should work for any OS?

#############################

#testing6
# Import settings from different file
sys.path.append(CURRENTFOLDERDIR)

from config import SETTINGS
from botstrings import STRINGS
from folders import FOLDERS
from funstuff import FUN
from localvar import *


client = discord.Client()
Sessions = requests.Session()

listUserID = {}
listCommands = {}

ESCAPE_SEQUENCE_RE = re.compile(r'''
    ( \\U........      # 8-digit hex escapes
    | \\u....          # 4-digit hex escapes
    | \\x..            # 2-digit hex escapes
    | \\[0-7]{1,3}     # Octal escapes
    | \\N\{[^}]+\}     # Unicode characters by name
    | \\[\\'"abfnrtv]  # Single-character escapes
    )''', re.UNICODE | re.VERBOSE)

def SplitString(strText, strSeparator):
    listSplit = []
    strTemp = ""
    
    while strSeparator in strText:
        strTemp = strText[:strText.find(strSeparator)]
        if len(strTemp) > 0:
            while len(strTemp) > 1 and strTemp[0] == " ":
                strTemp = strTemp[1:]
            while len(strTemp) > 1 and strTemp[-1:] == " ":
                strTemp = strTemp[:-1]
            if len(strTemp) > 0 and strTemp != " ":
                listSplit.append(strTemp)
                
        strText = strText[strText.find(strSeparator)+1:]
    
    if len(strText) > 0:
        while len(strText) > 1 and strText[0] == " ":
            strText = strText[1:]
        while len(strText) > 1 and strText[-1:] == " ":
            strText = strText[:-1]
        if len(strText) > 0 and strText != " ":
            listSplit.append(strText)
    
    return listSplit

def EscapeToUTF16(strEscape):
    strEscape = strEscape.replace("\\x", "")
    intParts = [0,0,0,0]
    intUTF16 = 0
    
    def getconst(x):
        # 4 -> 64
        # 6 -> 96
        # 8 -> 112
        a = -1/4
        b = 5/2
        c = 10
        return x*(a*x*x + b*x + c)
    
    # only the first one gets reduced by more than 128, can be found with this function
    # so far no blocks bigger than 4 are used.
    intParts[0] = -1 * getconst(len(strEscape))
    for i in range(0, len(strEscape), 2):
        intParts[int(i/2)] += int(strEscape[i:i+2], 16) - 128
        intUTF16 += int(math.pow(64, (len(strEscape) - i - 2)/2) * intParts[int(i/2)])
    
    hexUTF16 = hex(intUTF16)[2:]
    return hexUTF16

def UTF8toUTF16(strText):
    strText2 = strText
    
    # a very likely overkill, but better safe than sorry
    for i in range(len(strText)):
        intFirstX = strText2.find("\\x")
        intBlockSize = 1
        if strText2[intFirstX+4:intFirstX+6] == "\\x":
            if strText2[intFirstX+2] == "f":
                if strText2[intFirstX+5] != "e" and strText2[intFirstX+5] != "f":
                    intBlockSize = 4
            elif strText2[intFirstX+2] == "e":
                intBlockSize = 3
            elif strText2[intFirstX+2] == "c" or strText2[intFirstX+2] == "d":
                intBlockSize = 2
            
            if intBlockSize > 1:
                strUTF8 = strText2[intFirstX:intFirstX+4*intBlockSize]
                hexUTF16 = EscapeToUTF16(strUTF8)
                
                if len(hexUTF16) == 2:
                    strUTF16 = "\\x" + hexUTF16
                elif len(hexUTF16) == 3:
                    strUTF16 = "\\u0" + hexUTF16
                elif len(hexUTF16) == 4:
                    strUTF16 = "\\u" + hexUTF16
                elif len(hexUTF16) == 5:
                    strUTF16 = "\\U000" + hexUTF16
                elif len(hexUTF16) == 6:
                    strUTF16 = "\\U00" + hexUTF16
                elif len(hexUTF16) == 7:
                    strUTF16 = "\\U0" + hexUTF16
                elif len(hexUTF16) == 8:
                    strUTF16 = "\\U" + hexUTF16
                
                strText = strText.replace(strUTF8, strUTF16)
            
        strText2 = strText2[intFirstX+4*intBlockSize:]
    return strText

def CleanHTML(strhtml):
    p = re.compile(r'<.*?>')
    strhtml = p.sub('', strhtml)
    return strhtml

def CleanHTMLSpecific(strhtml, listTags):
    for tag in listTags:
        p = re.compile(r'<' + re.escape(tag) + '.*?>')
        strhtml = p.sub('', strhtml)

    return strhtml

def FixUnicode(strUni):
    # Let it only be called through FixEscapes()
    def decode_match(match):
        return codecs.decode(match.group(0), 'unicode-escape')
    
    strUni = ESCAPE_SEQUENCE_RE.sub(decode_match, strUni)
    return strUni

def FixEscapes(strText, boolIsTitle):
    # replace common &... symbols. add to list if any more found
    strText = strText.replace("&quot;", "\"")
    strText = strText.replace("&nbsp;", "")
    strText = strText.replace("&amp;", "&")
    strText = strText.replace("&lt;", "<")
    strText = strText.replace("&gt;", ">")
    strText = strText.replace("&middot;", "•")
    strText = strText.replace("\\n", "")
    
    # fix \x escape sequence groups to single \x, \u or \U
    strText = UTF8toUTF16(strText)

    # turn any &# codes into single \x, \u or \U escapes
    while "&#" in strText:
        intAmpers = strText.find("&#")
        intColon = strText.find(";")
        strColon = strText[intAmpers:intColon+1]
        strUTF16 = strColon.replace("&#","").replace(";","")
        strUTF16 = hex(int(strUTF16))[2:]
        
        if len(strUTF16) == 1:
            strUTF16 = "\\x0" + strUTF16
        elif len(strUTF16) == 2:
            strUTF16 = "\\x" + strUTF16
        elif len(strUTF16) == 3:
            strUTF16 = "\\u0" + strUTF16
        elif len(strUTF16) == 4:
            strUTF16 = "\\u" + strUTF16
        elif len(strUTF16) == 5:
            strUTF16 = "\\U000" + strUTF16
        elif len(strUTF16) == 6:
            strUTF16 = "\\U00" + strUTF16
        elif len(strUTF16) == 7:
            strUTF16 = "\\U0" + strUTF16
        elif len(strUTF16) == 8:
            strUTF16 = "\\U" + strUTF16
        
        strText = strText.replace(strColon, strUTF16)

    # get rid of leftovers
    strText = strText.replace("&#160;", " ")
    strText = strText.replace("( listen)", "")
    
    # turn \x, \u or \U escapes into proper characters
    strText = FixUnicode(strText)
    
    # remove citations/references. eg: [12]
    if not boolIsTitle:
        p = re.compile(r'\[[0-9]{1,2}\]')
        strText = p.sub('', strText)
    
    return strText

def CleanURL(strText):
    strText = strText.replace("%3F", "?")
    strText = strText.replace("%3D", "=")
    strText = strText.replace("%25", "%")
    
    return strText

def CheckMAL(strQuery):
    strSearch = strQuery
    # replace spaces with '+'
    strQuery = strQuery.replace(" ", "+")
    strQuery = "https://myanimelist.net/search/all?q=" + strQuery
    page = Sessions.get(strQuery)
    page = str(page.content)
    intURL1 = page.find("picSurround di-tc thumb")
    if SETTINGS.DEBUG_MODE >= 1:
        print("\tSearching...")
    if intURL1 == -1:
        embedResult = discord.Embed(title="**Searching MAL for \"" + strSearch + "\"**", url=strQuery)
        embedResult.add_field(name="Error", value="Anime or manga not found. Search page: " + strQuery, inline=True)
    else:
        page = page[intURL1:]
        page = page[:page.find("<img")]
        strQuery = page[page.find("http"):page.find("\" class")]
        page = Sessions.get(strQuery)
        strURL = page.url
        
        page = str(page.content)
        page = page[page.find("og:title"):page.find("<link rel=\"manifest\"")] + page[page.find("<h2>Information</h2>"):page.find("<h2>Statistics</h2>")]
        page = page.replace("  ", "").replace("\n", "").replace("\\n", "")

        if SETTINGS.DEBUG_MODE >= 1:
            print("\tAnime/manga found.")
        
        strTitle = page[19:page.find("\">")]
        strTitle = UTF8toUTF16(strTitle)
        strTitle = FixUnicode(strTitle)
        
        page = page[page.find("og:image"):]
        strImageURL = page[19:page.find("\">")]
        
        page = page[page.find("og:description"):]
        strSummary = page[25:page.find("\">")]
        strSummary = FixEscapes(strSummary, False)
        if len(strSummary) > 750:
            strSummary = strSummary[:750] + "..."

        if SETTINGS.DEBUG_MODE >= 1:
            print("\t" + strTitle)
            print("\t" + strImageURL)
            print("\t" + strSummary)
        
        embedResult = discord.Embed(title=strTitle, url=strURL)
        embedResult.set_thumbnail(url=strImageURL)
        embedResult.add_field(name="Summary", value=strSummary, inline=False)
        
        while "<div" in page:
            intDivEnd = page.find("</div>") + 6
            strTemp = page[page.find("<div"):intDivEnd]
            strTemp = strTemp.replace(":", ": ")
            strTemp = CleanHTML(strTemp)
            strTemp = FixEscapes(strTemp, False)

            if strTemp[:strTemp.find(":")] in SETTINGS.MAL_INFO:
                embedResult.add_field(name=strTemp[:strTemp.find(":")], value=strTemp[strTemp.find(":")+1:], inline=True)
            
            page = page[intDivEnd:]
    
    return embedResult

def CheckGoogle(strQuery):
    strSearch = strQuery
    strQuery = strQuery.replace("+", "%2B")
    strQuery = strQuery.replace(" ", "+")
    strQuery = "https://www.google.us/search?hl=EN&lr=lang_en&cr=US&q=" + strQuery
    page = Sessions.get(strQuery)
    strURL = str(page.url)
    
    tree = html.fromstring(page.content)
    listResults = tree.xpath("//div[contains(concat(' ', @class, ' '), ' g ')]")
    page = str(page.content)
    page = page[page.find("<div id=gbar>"):page.find("id=\"foot\">")]

    # Check for a series of div, span and table containers for Google card results (Time, weather, calculator, etc.)
    # WIP
    if "_rkc _Peb" in page:
        # TIME AND DATE
        intTimeStart = page.find("_rkc _Peb")
        page = page[intTimeStart + 11:intTimeStart + 290]
        
        page = CleanHTML(page)
        
        strTime = page[:page.find("M")+1]
        strDate = page[page.find("M")+2:page.find("(")-7]
        strLocation = page[page.find("Time in ")+8:page.find("<")]
        strLocation = FixUnicode(strLocation)
        
        if strDate[-1] == "1":
            strDate = strDate + "st"
        elif strDate[-1] == "2":
            strDate = strDate + "nd"
        elif strDate[-1] == "3":
            strDate = strDate + "rd"
        else:
            strDate = strDate + "th"
        
        embedResult = discord.Embed(title=strLocation, url=strQuery)
        embedResult.add_field(name="Time", value=strTime, inline=False)
        embedResult.add_field(name="Date", value=strDate, inline=False)
    elif "class=\"e\">" in page:
        # WEATHER (CARD ONLY)
        page = page[page.find("class=\"e\">")+10:page.find("&deg;F")]
        page = CleanHTMLSpecific(page, ["table", "td", "span", "a", "img", "/", "b", "h3"])
        
        strLocation = page[:page.find("<tr>")]
        strLocation = strLocation[12:]
        strLocation = FixUnicode(strLocation)
        
        floatTempC = page[page.find("<tr>")+4:-8]
        floatTempC = float(floatTempC)
        floatTempF = round(floatTempC * 1.8 + 32.0, 1)
        
        strWeather = str(floatTempC) + "°C / " + str(floatTempF) + "°F"
        
        embedResult = discord.Embed(title=strLocation, url=strQuery)
        embedResult.add_field(name="Weather", value=strWeather)
    elif "std _tLi" in page:
        # CURRENCY
        page = page[page.find("std _tLi"):]
        page = page[page.find("<h2"):page.find("</table>")]
        page = CleanHTML(page)

        currValue1 = str(float(page[:page.find(" ")]))
        currName1 = page[page.find(" ")+1:page.find("=")-1].title()

        page = page[page.find("=")+2:]

        currValue2 = str(float(page[:page.find(" ")]))
        currName2 = page[page.find(" ")+1:].title()

        embedResult = discord.Embed(title="Currency conversion", url=strQuery)
        embedResult.add_field(name=currName1, value=currValue1)
        embedResult.add_field(name=currName2, value=currValue2)
    elif "_Qeb _HOb" in page:
        # UNIT CONVERSION
        page = page[page.find("<div class=\"_Qeb _HOb\""):]
        page = page[:page.find("<h3")]
        page = CleanHTML(page)
        print(page)

        unitValue1 = str(float(page[:page.find(" ")]))
        unitName1 = page[page.find(" ")+1:page.find("=")-1].title()

        page = page[page.find("=")+2:]

        unitValue2 = str(float(page[:page.find(" ")]))
        unitName2 = page[page.find(" ")+1:].title()

        embedResult = discord.Embed(title="Unit conversion", url=strQuery)
        embedResult.add_field(name=unitName1, value=unitValue1)
        embedResult.add_field(name=unitName2, value=unitValue2)
    elif "<table class=\"_tLi\"" in page:
        # CALCULATOR
        page = page[page.find("<table class=\"_tLi\""):]
        page = page[page.find("<h2"):page.find("</h2")]
        page = CleanHTML(page)
        print(page)

        floatOperation = page[:page.find(" =")]
        floatResult = str(float(page[page.find("=")+2:]))

        embedResult = discord.Embed(title="Calculator", url=strQuery)
        embedResult.add_field(name=floatOperation, value=floatResult)
    elif "data-hveid=\"22\"" in page:
        # DEFINITION
        page = page[page.find("data-hveid=\"22\"")-5:]
        page = page[:page.find("</table>")]

        blockWord = page[:page.find("</div>")]
        strWordSplit = FixEscapes(CleanHTML(blockWord[:blockWord.find("</span>")+7]), False)
        blockWord = blockWord[blockWord.find("</span>")+7:]
        strWordPronounce = FixEscapes(CleanHTML(blockWord[:blockWord.find("</span>")+7]), False)
        
        print(strWordSplit)
        print(strWordPronounce)

        embedResult = discord.Embed(title="Definition", url=strQuery)
        embedResult.add_field(name=strWordSplit, value=strWordPronounce, inline=False)

        blockMeaning = page[page.find("<tr>"):]
        while "<tr><td>" in blockMeaning:
            strCategory = blockMeaning[blockMeaning.find("<div"):blockMeaning.find("</div")]
            strCategory = CleanHTML(strCategory)

            strCategoryMeaning = blockMeaning[blockMeaning.find("<ol"):blockMeaning.find("</ol>")]
            strCategoryMeaning = strCategoryMeaning.replace("</li>", "\n")
            strCategoryMeaning = CleanHTML(strCategoryMeaning)

            embedResult.add_field(name=strCategory, value=strCategoryMeaning, inline=True)

            blockMeaning = blockMeaning[blockMeaning.find("</td></tr>")+10:]
    elif "<a href=\"https://translate.google.com/" in page:
        # TRANSLATION
        page = page[page.find("<a href=\"https://translate.google.com/"):]
        page = page[:page.find("</table>")]
        page2 = page

        #strURL = page[9:page.find("&amp;sa=X")].replace("&amp;", "&")

        page = CleanHTML(page)
        page = FixEscapes(page, False)
        print(page)

        strLanguage = page[page.find("\" from")+6:page.find("translate.google.com")]

        strOrig = page[page.find("Translate \"")+11:]
        strOrig = strOrig[:strOrig.find("\"")]

        strTrans = page2[page2.find("- <span class=\"nobr\">")+21:]
        strTrans = CleanHTML(strTrans)
        strTrans = FixEscapes(strTrans, False)

        embedResult = discord.Embed(title="Translation from " + strLanguage, url=strQuery)
        embedResult.add_field(name=strOrig, value=strTrans)
    else:
        if len(listResults) == 0:
            embedResult = discord.Embed(title="Search results for \"" + strSearch + "\"", url=strURL)
            embedResult.add_field(name="Error", value="No results found.")
            return embedResult

        # NORMAL SEARCH RESULTS
        embedResult = discord.Embed(title="Search results for \"" + strSearch + "\"", url=strURL)

        #print(page)
        intResultCount = 0
        intListCounter = 0
        
        while intListCounter < len(listResults) and intResultCount < SETTINGS.MAX_GOOGLE_RESULTS:
            strResultBlock = str(etree.tostring(listResults[intListCounter], pretty_print=False, encoding='UTF-8'))
            intListCounter += 1
            
            # fixes "images for ..." and anything that doesn't have a summary
            if "<span class=\"st\">" in strResultBlock:
                intResultCount += 1
                
                tempURL2 = strResultBlock.find("&amp;sa=U")
                strResultURL = strResultBlock[strResultBlock.find("<a href=\"/url?q=") + 16:tempURL2]
                strResultURL = CleanURL(strResultURL)
                
                strResultBlock = strResultBlock[tempURL2:]
                strResultBlock = strResultBlock[strResultBlock.find("\">")+2:]
                
                strResultTitle = strResultBlock[:strResultBlock.find("</a>")]
                strResultTitle = CleanHTML(strResultTitle)

                # fix for news results
                if strResultTitle == "":
                    strResultBlock = strResultBlock[strResultBlock.find("<a href="):]
                    strResultTitle = strResultBlock[:strResultBlock.find("</a>")]
                    strResultTitle = CleanHTML(strResultTitle)
                
                strResultTitle = FixEscapes(strResultTitle, True)
                
                strResultBlock = strResultBlock[strResultBlock.find("<span class=\"st\">"):]
                tempResult = strResultBlock[:strResultBlock.find("</span>")]
                strResultSumm = tempResult
                
                # fix for youtube (and possibly other) results
                if "<span class=\"f\">" in tempResult:
                    tempResult = strResultBlock.replace("</span>", "").replace("<span class=\"nobr\">", "").replace("<span class=\"f\">", "")
                    strResultSumm = tempResult
                
                strResultSumm = CleanHTML(strResultSumm)
                strResultSumm = FixEscapes(strResultSumm, True)
                
                tempSpaces = strResultTitle.replace(" ", "")
                if len(tempSpaces) > 0:
                    strResultSumm = "*" + strResultURL + "*\n" + strResultSumm
                    embedResult.add_field(name=strResultTitle, value=strResultSumm, inline=False)
        
    return embedResult

def CheckWiki(strQuery):
    strSearch = strQuery
    strQuery = strQuery.replace(" ", "%20")
    strQuery = "https://en.wikipedia.org/wiki/Special:Search?search=" + strQuery
    page = Sessions.get(strQuery)
    strURL = page.url
    page = str(page.content)
    
    if " page lists articles associated with the title " in page:
        intTitleStart = page.find("<h1")
        intTitleEnd = page.find("</h1>")
        strTitle = page[intTitleStart:intTitleEnd]
        strTitle = CleanHTML(strTitle)
        strTitle = FixEscapes(strTitle, True)
        strTitle = "**" + strTitle + "**"
        
        embedResult = discord.Embed(title=strTitle, url=strURL)
        embedResult.add_field(name="Disambiguation", value=strURL, inline=True)
        return embedResult
    
    intSummStart = page.find("</table>\\n<p>")
    if intSummStart == -1:
        embedResult = discord.Embed(title="**Searching for \"" + strSearch + "\"**", url=strURL)
        embedResult.add_field(name="Error", value="Search did not return any automatic results. Search page: " + strURL, inline=True)
    else:
        intTitleStart = page.find("<h1")
        intTitleEnd = page.find("</h1>")
        strTitle = page[intTitleStart:intTitleEnd]
        strTitle = CleanHTML(strTitle)
        strTitle = FixEscapes(strTitle, True)
        strTitle = "**" + strTitle + "**"
        
        page = page[intSummStart + 13:]
        intSummEnd = page.find("</p>")
        strExtract = page[:intSummEnd]
        strExtract = CleanHTML(strExtract)
        strExtract = FixEscapes(strExtract, False)
        
        embedResult = discord.Embed(title=strTitle, url=strURL)
        embedResult.add_field(name="Extract", value=strExtract, inline=True)
    
    return embedResult

def CheckPanda(strURL):
    cookie = {'ipb_member_id': '549876', 'ipb_pass_hash': '15019f9882cbe59483980e9f86bf67cb'}
    page = Sessions.get(strURL, cookies=cookie)
    page = str(page.content)
    
    intTitle1 = page.find("<title>")
    
    if intTitle1 != -1:
        strImageURL = page[page.find("url(")+4:]
        strImageURL = strImageURL[:strImageURL.find(")")]
        r = Sessions.get(strImageURL)
        open(CURRENTFOLDERDIR + FOLDERS.THUMBNAIL_DOWNLOAD[os.name] + "panda.jpg", 'wb').write(r.content)
        
        im = pyimgur.Imgur(SETTINGS.IMGUR_ID)
        uploaded_image = im.upload_image(CURRENTFOLDERDIR + FOLDERS.THUMBNAIL_DOWNLOAD[os.name] + "panda.jpg")
        print(uploaded_image.link)
        
        page = page[intTitle1:page.find("<div id=\"tagmenu_act\"")]
        
        intTitle2 = page.find("</title>") - 15
        strTitle = page[7:intTitle2]
        strTitle = FixUnicode(strTitle)
        
        embedResult = discord.Embed(title=strTitle, url=strURL)
        
        page = page[intTitle2+8:]
        strTagBlock = page[page.find("<td class=\"tc\">"):]
        
        while "td class=\"tc\"" in strTagBlock:
            intBlockEnd = strTagBlock.find("</tr>") + 5
            strLocalBlock = strTagBlock[:intBlockEnd]
            
            if strLocalBlock[0:4] == "<tr>":
                intCat = 19
            else:
                intCat = 15
            
            strCategory = strLocalBlock[intCat:strLocalBlock.find("</td>")]
            strTags = ""
            
            while "<div" in strLocalBlock:
                strTempTag = strLocalBlock[strLocalBlock.find("<div"):strLocalBlock.find("</a>")]
                strTempTag = CleanHTML(strTempTag)
                strTags = strTags + " " + strTempTag + ","
                strLocalBlock = strLocalBlock[strLocalBlock.find("</a>")+4:]
            
            strTags = strTags[:-1]
            embedResult.add_field(name=strCategory, value=strTags)
            
            strTagBlock = strTagBlock[intBlockEnd:]
        
        embedResult.set_thumbnail(url=uploaded_image.link)
        return embedResult

def CheckBooru(strTags, strSite, strRating):
    # Determine website and tag query
    if strRating[:3] == "not":
        strRating = "-rating:" + strRating[4:]
    elif strRating == "explicit" or strRating == "safe" or strRating == "questionable":
        strRating = "rating:" + strRating
    else:
        strRating = ""
    
    if strSite == "Gelbooru":
        strURL = "https://gelbooru.com/index.php?page=post&s=list&tags=" + strTags
    elif strSite == "Danbooru":
        strURL = "https://danbooru.donmai.us/posts?tags=" + strTags

    if strRating != "":
        strURL = strURL + "+" + strRating

    # Request the website
    page = Sessions.get(strURL)
    page = str(page.content)

    if "<h1>Nobody here but us chickens!</h1>" in page:
        # no results
        resultImage = "No images found for these tags."
    else:
        # get number of pages
        blockPages = page[page.find("<div id=\"paginater\">"):]
        blockPages = blockPages[:blockPages.find("</div>")]

        if "last page" in blockPages:
            intPages = blockPages[blockPages.find("alt=\"last page\"")-30:]
            intPages = int(intPages[intPages.find("pid=")+4:intPages.find("\"")])

            # search at most 16 pages due to gelbooru limitations
            if intPages >= 630:
                intPages = 16
            else:
                intPages = intPages/42 + 1
        else:
            intPages = blockPages[blockPages.find("</div>")-8:]
            intPages = int(intPages[intPages.find(">")+1:intPages.find("</")])

        # only get random page if number of pages is more than 1
        # small optimization
        if intPages > 1:
            randomPage = random.randint(1, intPages)
        else:
            randomPage = 1

        # get page url if page is different from first
        # prevents loading the same page (first one) twice
        if randomPage > 1:
            randomPage = (randomPage - 1) * 42
            strURL = strURL + "&pid=" + str(randomPage)

            page = Sessions.get(strURL)
            page = str(page.content)
        
        blockImages = page[page.find("<div class=\"thumbnail-preview\">"):]
        blockImages = blockImages[:blockImages.find("<script")]
        blockImages = blockImages.replace("\\r", "").replace("\\t", "").replace("\\n", "").replace("<center><br />", "")
        blockImages = CleanHTMLSpecific(blockImages, ["img", "div", "span", "/"])

        # get the url of all the images in the page
        listImages = []
        while "href=\"" in blockImages:
            blockImages = blockImages[blockImages.find("href=\"")+6:]
            tempImage = "https:" + blockImages[:blockImages.find("\"")]
            tempImage = tempImage.replace("amp;", "")
            listImages.append(tempImage)

        randomImagePage = random.choice(listImages)
        print("\t" + randomImagePage)

        page = Sessions.get(randomImagePage)
        page = str(page.content)

        randomImageURL = page[page.find("og:image")+19:]
        randomImageURL = randomImageURL[:randomImageURL.find("\"")]

        resultImage = "<" + randomImagePage + ">\n" + randomImageURL
    
    return resultImage

def ModifyRikaPoints(strTargetID, intAmount):
    FUN.LIST_RIKAPOINTS[strTargetID] = FUN.LIST_RIKAPOINTS[strTargetID] + intAmount

    rikapfile = open('RikaPoints.txt', 'w+')
    for userid in listUserID:
        rikapfile.write(str(userid) + " = " + str(FUN.LIST_RIKAPOINTS[userid]) + "\n")
    rikapfile.close()

    msg = "<@" + strTargetID + "> has "
    if intAmount >= 0:
        msg = msg + "received "
    else:
        msg = msg + "lost "
    msg = msg + str(abs(intAmount)) + " Rika Points:tm:"

    return msg

async def WaitForReminder(strAuthorID, strReminder, channelTarget):
    boolIsWaiting = listUserID[strAuthorID]["Reminder"]
    
    if not boolIsWaiting:
        listUserID[strAuthorID]["Reminder"] = True
        listArguments = SplitString(strReminder, "|")
        intH = 0
        intM = 0
        intS = 0
        
        strTime = listArguments[0].lower().replace(" ","")
        strMessage = "<@!" + strAuthorID + ">"
        
        print("\tGiven time: " + strTime)
        i = 0
        while i < len(strTime):
            if strTime[i] == "h":
                tempH = strTime[:i]
                try:
                    int(tempH)
                    tempH = int(tempH)
                    if tempH < 0:
                        tempH = 0
                    intH += tempH
                except ValueError:
                    intH += 0
                
                strTime = strTime[i+1:]
                i = 0
            elif strTime[i] == "m":
                tempM = strTime[:i]
                try:
                    int(tempM)
                    tempM = int(tempM)
                    if tempM < 0:
                        tempM = 0
                    intM += tempM
                except ValueError:
                    intM += 0
                
                strTime = strTime[i+1:]
                i = 0
            elif strTime[i] == "s":
                tempS = strTime[:i]
                try:
                    int(tempS)
                    tempS = int(tempS)
                    if tempS < 0:
                        tempS = 0
                    intS += tempS
                except ValueError:
                    intS += 0
                
                strTime = strTime[i+1:]
                i = 0
            
            i += 1
        
        if intS > 60:
            intM += int(intS / 60)
            intS = intS % 60
        if intM > 60:
            intH += int(intM / 60)
            intM = intM % 60
        
        listUserID[strAuthorID]["Timer"] = intH*3600 + intM*60 + intS
        print("\tInterpreted time: " + str(intH) + "h" + str(intM) + "m" + str(intS) + "s")
        if len(listArguments) >= 2:
            strMessage = strMessage + ": " + listArguments[1]
            print("\tReminder message: " + listArguments[1])
        
        if listUserID[strAuthorID]["Timer"] > 0:
            print("# " + str(datetime.datetime.now())[5:16] + "\tStart reminder for ID " + strAuthorID)
            while listUserID[strAuthorID]["Timer"] > 0:
                #print(listUserID[strAuthorID]["Timer"])
                listUserID[strAuthorID]["Timer"] -= SETTINGS.TIMER_WAIT
                await asyncio.sleep(SETTINGS.TIMER_WAIT)
            
            if listUserID[strAuthorID]["Reminder"]:
                await client.send_message(channelTarget, strMessage)
                listUserID[strAuthorID]["Reminder"] = False
            print("# " + str(datetime.datetime.now())[5:16] + "\tEnd reminder for ID " + strAuthorID)
        else:
            listUserID[strAuthorID]["Reminder"] = False
            await client.send_message(channelTarget, "Something went wrong. Please try again.")

async def CommandCooldown(intCooldown, strCommand):
    if listCommands[strCommand]["Cooldown"] == 0:
        listCommands[strCommand]["Cooldown"] = intCooldown+1

        while listCommands[strCommand]["Cooldown"] >= 1:
            listCommands[strCommand]["Cooldown"] -= 1
            await asyncio.sleep(1)

        listCommands[strCommand]["Cooldown"] = 0

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    
    # setup member id list to prevent fuckery
    tempServer = client.get_server("237325019770912769")
    for tempUsers in tempServer.members:
        listUserID[tempUsers.id] = {"Awaiting":False, "Reminder":False, "Timer":0}

    # load rika points from file
    rikapfile = open('RikaPoints.txt', 'r')
    lines = rikapfile.read().splitlines()
    for line in lines:
        userid = line[:line.find(" =")]
        amount = line[line.find("= ")+2:]
        FUN.LIST_RIKAPOINTS[userid] = int(amount)
    rikapfile.close()

    for command in SETTINGS.COMMAND_LIST:
        listCommands[command] = {"Cooldown":0}

@client.event
async def on_message(message):
    # - commands
    if not message.author.bot and (not SETTINGS.MAINTENANCE_MODE or message.author.id in SETTINGS.DEV_ID):
        if message.content.startswith("-"):
            # Dev commands
            if message.author.id in SETTINGS.DEV_ID:
                if message.content == "-delrika":
                    def is_me(m):
                        return m.author == client.user
                    
                    deleted = await client.purge_from(message.channel, limit=SETTINGS.MAX_DELETE_SEARCH, check=is_me)
                    print("Deleted " + str(len(deleted)) + " message(s) from bot")
                elif message.content == "-delemoji":
                    # Delete downloaded emoji cache
                    files = glob.glob(CURRENTFOLDERDIR + FOLDERS.EMOJI_DOWNLOAD[os.name] + "*.png")
                    for f in files:
                        os.remove(f)
                elif message.content[:7] == "-delete":
                    if len(message.content) == 7:
                        await client.send_message(message.channel, "Usage: -deltest [user ID]")
                    else:
                        strUser = message.content[9:].replace("<", "").replace("!", "").replace(">", "").replace("@", "")
                        if strUser in SETTINGS.DEV_ID:
                            def is_me(m):
                                return m.author.id == strUser
                            
                            deleted = await client.purge_from(message.channel, limit=SETTINGS.MAX_DELETE_SEARCH, check=is_me)
                            print("Deleted " + str(len(deleted)) + " message(s) from user " + strUser)
                        else:
                            await client.send_message(message.channel, "I'm sorry Dave, I'm afraid I can't do that")
                            print("Can\'t delete this user ID")
            
            # keep imageposting to #image channel to prevent spam
            if message.channel.name == "images" or message.channel.name == "lewd_mood":
                if message.content == "-kek":
                    # random pic from animu folder
                    files = [os.path.join(path, filename)
                        for path, dirs, files in os.walk(CURRENTFOLDERDIR + FOLDERS.ANIME_PICS[os.name])
                        for filename in files ]
                    choice = random.choice(files)
                    await client.send_file(message.channel, choice)
                elif message.content == "-hinamizawa":
                    #random pic from higurashi folder
                    fullPath = CURRENTFOLDERDIR + FOLDERS.RIKA_PICS[os.name]
                    piccy = random.choice(os.listdir(CURRENTFOLDERDIR + FOLDERS.RIKA_PICS[os.name])) #change dir name to whatever
                    fullPath += piccy
                    await client.send_file(message.channel, fullPath)
                elif message.content == "-umu":
                    # umu
                    await client.send_message(message.channel, "https://i.imgur.com/0cAaUfT.jpg")
                elif message.content == "-padoru":
                    # PADORU PADORU
                    await client.send_message(message.channel, "https://i.imgur.com/4wCn5ws.gif")
                elif message.content == "-taiga":
                    files = [os.path.join(path, filename)
                        for path, dirs, files in os.walk(CURRENTFOLDERDIR + FOLDERS.TAIGA_PICS[os.name])
                        for filename in files ]
                    choice = random.choice(files)
                    await client.send_file(message.channel, choice)
            
            # main commands
            if message.content[:3] == "-e " or message.content == "-e":
                # bigger emote
                print("Accepted command: " + message.content)
                if len(message.content) == 2:
                    await client.send_message(message.channel, "Usage: -e [:emote:]")
                else:
                    strEmote = message.content[3:]
                    if "<:" in strEmote:
                        strEmote = strEmote[strEmote.find(":")+1:]
                        strEmote = strEmote[strEmote.find(":")+1:-1]
                        if not os.path.exists(CURRENTFOLDERDIR + FOLDERS.EMOJI_DOWNLOAD[os.name] + strEmote + ".png"):
                            urlEmote = "https://cdn.discordapp.com/emojis/" + strEmote + ".png"
                            r = Sessions.get(urlEmote, allow_redirects=True)
                            open(CURRENTFOLDERDIR + FOLDERS.EMOJI_DOWNLOAD[os.name] + strEmote + ".png", 'wb').write(r.content) 
                    else:
                        strEmote = str(strEmote.encode("utf-8", "replace"))[2:-1]
                        strEmote = EscapeToUTF16(strEmote)
                        if not os.path.exists(CURRENTFOLDERDIR + FOLDERS.EMOJI_DOWNLOAD[os.name] + strEmote + ".png"):
                            urlEmote = "https://assets-cdn.github.com/images/icons/emoji/unicode/" + strEmote + ".png"
                            r = Sessions.get(urlEmote, allow_redirects=True)
                            open(CURRENTFOLDERDIR + FOLDERS.EMOJI_DOWNLOAD[os.name] + strEmote + ".png", 'wb').write(r.content)
                    await client.send_file(message.channel, CURRENTFOLDERDIR + FOLDERS.EMOJI_DOWNLOAD[os.name] + strEmote + ".png")
                    await client.delete_message(message)
            elif message.content == "-lewd":
                # random lewd pic from folder (lewddir)
                files = [os.path.join(path, filename)
                    for path, dirs, files in os.walk(lewddir)
                    for filename in files ]
                choice = random.choice(files)
                await client.send_file(message.channel, choice)
            elif message.content[:9] == "-gelbooru":
                # gelbooru
                print("Accepted command: " + message.content)
                if len(message.content) == 9:
                    await client.send_message(message.channel, "Usage: -gelbooru [tags] | {rating}")
                else:
                    listArgs = SplitString(message.content[10:], "|")
                    listArgs[0] = listArgs[0].replace(" ", "+")

                    if message.channel.id == "311315942355238912":
                        if len(listArgs) == 1:
                            listArgs.append("none")
                    else:
                        listArgs[0].replace("rating:explicit", "").replace("rating:safe", "").replace("rating:questionable", "")
                        if len(listArgs) == 1:
                            listArgs.append("safe")
                        else:
                            if listArgs[1] != "safe":
                                listArgs[1] = "safe"
                                await client.send_message(message.channel, "No lewds allowed outside #lewd_mood. Searching 'safe' results.")
                    
                    if message.channel.id == "237325019770912769":
                        if listCommands["gelbooru"]["Cooldown"] > 0:
                            await client.send_message(message.channel, "Command on cooldown for " + str(listCommands["gelbooru"]["Cooldown"]) + " seconds.")
                        else:
                            strResult = CheckBooru(listArgs[0], "Gelbooru", listArgs[1])
                            await client.send_message(message.channel, strResult)

                            await CommandCooldown(10, "gelbooru")
                    else:
                        strResult = CheckBooru(listArgs[0], "Gelbooru", listArgs[1])
                        await client.send_message(message.channel, strResult)
            elif message.content[:7] == "-google":
                # show top 5 results of google search
                print("Accepted command: " + message.content)
                if len(message.content) == 7:
                    await client.send_message(message.channel, "Usage: -google [search term]")
                else:
                    strSearch = message.content[8:]
                    embedResult = CheckGoogle(strSearch)
                    await client.send_message(message.channel, embed=embedResult)
            elif message.content[:5] == "-help":
                print("Accepted command: " + message.content)
                if len(message.content) == 5:
                    strHelp = STRINGS.HELP_STRING
                    await client.send_message(message.channel, strHelp)
                #else:
                #    embedResult = CommandInfo(strMessage[5:])
                #    await client.send_message(message.channel, embed=embedResult)
            elif message.content == "-imagine":
                choice = random.choice(STRINGS.LIST_IMAGINE)
                await client.send_message(message.channel, choice)
            elif message.content[:4] == "-mal":
                # search MAL for something
                print("Accepted command: " + message.content)
                if len(message.content) == 4:
                    await client.send_message(message.channel, "Usage: -mal [anime/manga]")
                else:
                    strSearch = message.content[5:]
                    embedResult = CheckMAL(strSearch)
                    await client.send_message(message.channel, embed=embedResult)
            elif message.content[:5] == "-pick":
                # pick for you
                print("Accepted command: -pick")
                if len(message.content) == 5:
                    await client.send_message(message.channel, "Usage: -pick [option1] | [option2] | ... | [optionN]")
                else:
                    strArguments = message.content[6:]
                    listOptions = SplitString(strArguments, "|")
                    choice = random.choice(listOptions)
                    print("\tGiven options: ")
                    print(listOptions)
                    await client.send_message(message.channel, choice)
            elif message.content[:9] == "-reminder":
                # reminder/timer
                print("Accepted command: " + message.content)
                if len(message.content) == 9:
                    await client.send_message(message.channel, "Usage: -reminder [Xh][Ym][Zs] | {message}")
                else:
                    strArguments = message.content[10:]
                    if listUserID[message.author.id]["Reminder"]:
                        if strArguments[:6] == "cancel":
                            listUserID[message.author.id]["Timer"] = 0
                            listUserID[message.author.id]["Reminder"] = False
                            await client.send_message(message.channel, "Cancelling reminder")
                        elif strArguments[:9] == "remaining":
                            intS = listUserID[message.author.id]["Timer"]
                            intH = int(intS/3600)
                            intS = intS % 3600
                            intM = int(intS/60)
                            intS = intS % 60
                            strTime = ""
                            if intH > 0:
                                strTime += str(intH) + "h "
                            if intM > 0:
                                strTime += str(intM) + "m "
                            strTime += str(intS) + "s"
                            
                            await client.send_message(message.channel, "Remaining time: " + strTime)
                    else:
                        await client.send_message(message.channel, "Reminder set.")
                        await WaitForReminder(message.author.id, strArguments, message.channel)
            elif message.content[:6] == "-rikap":
                # rika points
                print("Accepted command: " + message.content)
                args = SplitString(message.content[7:], " ")
                # args[0] = target, [1] = action, [2] = amount (if add/rem)
                if args[0] == "self":
                    # allow only check
                    if args[1] == "check":
                        selfid = str(message.author.id)
                        msg = "You have " + str(FUN.LIST_RIKAPOINTS[selfid]) + " Rika Points:tm:"
                        print(msg)
                        await client.send_message(message.channel, msg)
                elif args[0][:2] == "<@":
                    if message.author.id in SETTINGS.DEV_ID:
                        # allow check, add, rem/remove
                        target = args[0][2:-1].replace("!", "")
                        print(target)
                        if args[1] == "check":
                            msg = "<@" + target + "> has " + str(FUN.LIST_RIKAPOINTS[target]) + " Rika Points:tm:"
                            print(msg)
                            await client.send_message(message.channel, msg)
                        elif args[1] == "add":
                            # add rika points
                            amount = int(args[2])
                            msg = ModifyRikaPoints(target, amount)
                            print(msg)
                            await client.send_message(message.channel, msg)
                        elif args[1] == "rem" or args[1] == "remove":
                            # remove rika points
                            amount = int(args[2])
                            msg = ModifyRikaPoints(target, -1*amount)
                            print(msg)
                            await client.send_message(message.channel, msg)
                    else:
                        await client.send_message(message.channel, "You do not have permission to use this function.")

            elif message.content == "-stream":
                # stream link, never used
                print("Accepted command: " + message.content)
                await client.send_message(message.channel, "@everyone http://www.ustream.tv/channel/tbone7160")
            elif message.content[:5] == "-time":
                # get time from google's result
                print("Accepted command: " + message.content)
                if len(message.content) == 5:
                    await client.send_message(message.channel, "Usage: -time [location]")
                else:
                    strLocation = message.content[6:]
                    embedResult = CheckGoogle("Time in " + strLocation)
                    await client.send_message(message.channel, embed=embedResult)
            elif message.content[:8] == "-weather":
                # get weather off google's result
                print("Accepted command: " + message.content)
                if len(message.content) == 8:
                    await client.send_message(message.channel, "Usage: -weather [location]")
                else:
                    strLocation = message.content[9:]
                    embedResult = CheckGoogle("Weather in " + strLocation)
                    await client.send_message(message.channel, embed=embedResult)
            elif message.content[:5] == "-wiki":
                # search wikipedia
                print("Accepted command: " + message.content)
                if len(message.content) == 5:
                    await client.send_message(message.channel, "Usage: -wiki [search term]")
                else:
                    strSearch = message.content[6:]
                    embedResult = CheckWiki(strSearch)
                    await client.send_message(message.channel, embed=embedResult)
            elif message.content[:5] == "-test":
                #strSearch = message.content[6:]
                print("test")
        else:
            strMessage = message.content.lower()
            
            if strMessage == "<@!389619827905527819>":
                print("@Rika")
                strResponse = "<@" + message.author.id + ">"
                await client.send_message(message.channel, strResponse)
            elif strMessage.startswith("https://exhentai.org/g/"):
                embedResult = None #CheckPanda(strMessage)
                if embedResult != None:
                    await client.send_message(message.channel, embed=embedResult)
            elif strMessage.startswith("datgai"):
                # bullying
                await client.send_message(message.channel, "What a homo")
            elif strMessage == "same":
                # same
                await client.send_message(message.channel, "same")
            elif strMessage == "f":
                # F
                await client.send_message(message.channel, "F")
            elif strMessage == "nice":
                # nice
                await client.send_message(message.channel, "nice")
            elif strMessage == "test":
                # test
                await client.send_message(message.channel, "tested")
            elif strMessage == "<:smugbr:269994850030452736>" or strMessage == "<:robobr:424780800551157761>" or strMessage == "<@109082700391936000>" or strMessage == "<@&295346319931998209>":
                # more bullying
                choice = random.choice(STRINGS.LIST_BR)
                if strMessage == "<:robobr:424780800551157761>":
                    bina = ""
                    for i in range(len(choice)):
                        tchar = choice[i]
                        tempbin = ' '.join(format(ord(x), 'b') for x in tchar)
                        tempbin = ("0" * (8 - len(tempbin))) + tempbin
                        bina = bina + tempbin + " "
                    choice = bina
                await client.send_message(message.channel, choice)
            elif "benis" in strMessage:
                # benis :DDD
                await client.send_message(message.channel, "fugggg :DDDD")
            elif "good bot" in strMessage:
                # good bot
                await client.send_message(message.channel, "Nippah")

client.run(botkey)
