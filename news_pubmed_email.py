import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import time
from urllib.parse import quote_plus
import os

# 发送邮件的配置信息
sender_email = os.environ.get('SENDER_EMAIL')
sender_password = os.environ.get('SENDER_PASSWORD')
receiver_email = os.environ.get('RECEIVER_EMAIL')
smtp_server = "smtp.163.com"
smtp_port = 465

# Google搜索的URL模板
URL_SEARCH = "https://www.google.com/search?hl={language}&gl=us&q={query}&tbs=qdr:w&btnG=Search&gbv=1"
URL_NUM = "https://www.google.com/search?hl={language}&gl=us&q={query}&tbs=qdr:w&btnG=Search&gbv=1&num={num}"

def search_page(query, language='en', num=None, pause=2):
    """
    Google search
    :param query: Keyword
    :param language: Language
    :param num: Number of results
    :param pause: Delay between requests
    :return: result HTML
    """
    time.sleep(pause)
    if num is None:
        url = URL_SEARCH.format(language=language, query=quote_plus(query))
    else:
        url = URL_NUM.format(language=language, query=quote_plus(query), num=num)

    try:
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        r = requests.get(url, allow_redirects=False, verify=False, timeout=30)
        r.raise_for_status()
        # 打印HTML内容以便调试
        print(r.text)
        return r.text
    except Exception as e:
        logging.error(e)
        return None

def parse_google_search_results(html):
    soup = BeautifulSoup(html, 'html.parser')
    articles = []

    # 尝试不同的HTML结构
    for item in soup.select('div.kCrYT'):
        title_elem = item.select_one('h3')
        if title_elem:
            title = title_elem.text
            link_elem = item.select_one('a')
            link = link_elem['href'].replace('/url?q=', '').split('&')[0] if link_elem else 'No link'
            snippet_elem = item.select_one('.BNeawe.s3v9rd.AP7Wnd')
            snippet = snippet_elem.text if snippet_elem else 'No snippet'
            articles.append((title, link, snippet, 'No date'))

    # 调试信息
    print(f"Parsed Google Search Results: {articles}")
    
    return articles

def search_google_news(query):
    html = search_page(query, language='en', num=10)
    if html:
        return parse_google_search_results(html)
    return []

def search_pubmed(query, days):
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&reldate={days}&datetype=edat&retmode=json"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    print(f"PubMed Response Status: {response.status_code}")
    if response.status_code != 200:
        print("Error: PubMed API is not available.")
        return []

    data = response.json()
    ids = data.get('esearchresult', {}).get('idlist', [])
    articles = []

    for pubmed_id in ids:
        article_url = f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"
        article_response = requests.get(article_url, headers=headers)
        article_soup = BeautifulSoup(article_response.text, 'html.parser')
        title = article_soup.select_one('h1.heading-title').text.strip() if article_soup.select_one('h1.heading-title') else 'No title'
        snippet = article_soup.select_one('div.abstr p').text.strip() if article_soup.select_one('div.abstr p') else 'No snippet'
        date = article_soup.select_one('span.cit').text.strip() if article_soup.select_one('span.cit') else 'No date'
        articles.append((title, article_url, snippet, date))
    
    # 调试信息
    print(f"PubMed Articles: {articles}")
    
    return articles

def send_email(subject, body, to_email):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())

def main():
    query = "Vertebral Body Tethering"
    days = 7
    google_news = search_google_news(query)
    pubmed_articles = search_pubmed(query, days)

    email_body = "<h2>Latest News and Articles on Vertebral Body Tethering</h2>"
    
    email_body += "<h3>Google News:</h3><ul>"
    for title, link, snippet, date in google_news:
        email_body += f"<li><a href='{link}'>{title}</a><br>{snippet}<br>{date}</li>"
    email_body += "</ul>"
    
    email_body += "<h3>PubMed Articles:</h3><ul>"
    for title, link, snippet, date in pubmed_articles:
        email_body += f"<li><a href='{link}'>{title}</a><br>{snippet}<br>{date}</li>"
    email_body += "</ul>"

    send_email("Latest News and Articles on Vertebral Body Tethering", email_body, receiver_email)

if __name__ == "__main__":
    main()
