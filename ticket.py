# coding: utf-8
from json import loads
from os.path import exists
from pickle import dump, load
from time import sleep, time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class Concert(object):
    def __init__(self, session, price, date, real_name, nick_name, ticket_num, damai_url, target_url, browser):
        self.session = session  # priority of session (list of session numbers)
        self.price = price  # priority of price (list of price sequence numbers)
        self.date = date # date of the performance
        self.real_name = real_name  # real name information
        self.status = 0  # status for ticket process: [0,6]
        self.time_start = 0  # start time to buy ticket
        self.time_end = 0  # end time to buy ticket
        self.num = 0  # number of times to try to purchase
        self.type = 0  # type of target website (specified below)
        self.ticket_num = ticket_num  # number of tickets to purchase
        self.nick_name = nick_name  # username on the website
        self.damai_url = damai_url  # url of the website
        self.target_url = target_url  # url of target website of ticket
        self.browser = browser # browser type for selenium: 0 is Chrome, 1 is Firefox, default 0
        self.total_wait_time = 3 # total wait time before throwing exception
        self.refresh_wait_time = 0.3 # total wait time before refresh
        self.intersect_wait_time = 0.5 # wait time to buy ticket, mimic human behaviro

        # only type 1 and type 2 of website have purchasable tickets
        if self.target_url.find("detail.damai.cn") != -1:
            self.type = 1
        elif self.target_url.find("piao.damai.cn") != -1:
            self.type = 2
        else:
            self.type = 0
            self.driver.quit()
            raise Exception("***Error:Unsupported Target Url Format:{}***".format(self.target_url))

            
    def isClassPresent(self, item, name, ret=False):
        try:
            result = item.find_element_by_class_name(name)
            if ret:
                return result
            else:
                return True
        except:
            return False

    # opens website, user needs to login to get cookies
    def get_cookie(self):
        self.driver.get(self.damai_url)
        print("Please click to login")
        while self.driver.title.find('大麦网-全球演出赛事官方购票平台') != -1:  # wait for webpage to load
            sleep(1)
        print("Please scan QR code")
        while self.driver.title == '大麦登录':  # wait for QR code scan verification
            sleep(1)
        dump(self.driver.get_cookies(), open("cookies.pkl", "wb"))
        print("Cookies saved")

    # load cookies to webdriver
    def set_cookie(self):
        try:
            cookies = load(open("cookies.pkl", "rb"))
            for cookie in cookies:
                cookie_dict = {
                    'domain': '.damai.cn',
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    "expires": "",
                    'path': '/',
                    'httpOnly': False,
                    'HostOnly': False,
                    'Secure': False}
                self.driver.add_cookie(cookie_dict)
            print('Cookies loaded')
        except Exception as e:
            print(e)

            
    def login(self):
        # if cookies does not exist, create webdriver and load cookies
        if not exists('cookies.pkl'):
            if self.browser == 0: # Chrome
                self.driver = webdriver.Chrome()
            elif self.browser == 1: # Firefox
                self.driver = webdriver.Firefox()
            else:
                raise Exception("Unknown browser type")
            self.get_cookie()
            self.driver.quit()
        print('Entering website')
        # If cookies are loaded successfully
        if self.browser == 0:   # Chrome
            options = webdriver.ChromeOptions()
            prefs = {"profile.managed_default_content_settings.images":2}
            options.add_experimental_option("prefs",prefs)  # does not load image (speed up)
            self.driver = webdriver.Chrome(options=options)
        elif self.browser == 1: # Firefox
            options = webdriver.FirefoxProfile()
            options.set_preference('permissions.default.image', 2)  
            self.driver = webdriver.Firefox(options)
        else: 
            raise Exception("Unknown browser type")
        self.driver.get(self.target_url)
        self.set_cookie()
        self.driver.refresh()
        
        
    def enter_concert(self):
        self.login()
        try:
            if self.type == 1:  # detail.damai.cn
                locator = (By.XPATH, "/html/body/div[1]/div/div[3]/div[1]/a[2]/div")
            elif self.type == 2:  # piao.damai.cn
                locator = (By.XPATH, "/html/body/div[1]/div/ul/li[2]/div/label/a[2]")
            WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                EC.text_to_be_present_in_element(locator, self.nick_name))
            self.status = 1
            print("Login success")
        except Exception as e:
            print(e)
            self.status = 0
            self.driver.quit()
            raise Exception("Login failed! Please check nick_name or delete cookie.pkl and try again")

            
    def choose_ticket_1(self):  # choose ticket for type 1, i.e., detail.damai.cn
        self.time_start = time()
        print("Selecting date and ticket")

        while self.driver.title.find('确认订单') == -1:  # ticket purchase success
            self.num += 1
            
            if self.date != 0: # if a date is specified
                calendar = WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "functional-calendar")))
                datelist = calendar.find_elements_by_css_selector("[class='wh_content_item']") # find available date
                datelist = datelist[7:] # first 7 elements are days of the week, not needed
                datelist[self.date - 1].click() # choose date
            
            # find one session and price of a performance
            selects = self.driver.find_elements_by_class_name('perform__order__select')
            for item in selects:
                if item.find_element_by_class_name('select_left').text == '场次':
                    session = item
                elif item.find_element_by_class_name('select_left').text == '票档':
                    price = item

            session_list = session.find_elements_by_class_name('select_right_list_item')
            print('Number of available sessions:{}'.format(len(session_list)))
            if len(self.session) == 1:
                j = session_list[self.session[0] - 1].click()
            else:
                for i in self.session:  # find session acording to priority of sessions
                    j = session_list[i - 1]
                    k = self.isClassPresent(j, 'presell', True)
                    if k:
                        if k.text == '无票':  # no ticket
                            continue
                        elif k.text == '预售':   # presale
                            j.click()
                            break
                    else:
                        j.click()
                        break

            price_list = price.find_elements_by_class_name('select_right_list_item')
            print('Number of available prices:{}'.format(len(price_list)))
            if len(self.price) == 1:
                j = price_list[self.price[0] - 1].click()
            else:
                for i in self.price:
                    j = price_list[i - 1]
                    k = self.isClassPresent(j, 'notticket')
                    if k:
                        continue
                    else:
                        j.click()
                        break

            buybutton = self.driver.find_element_by_class_name('buybtn')
            buybutton_text = buybutton.text
            # print(buybutton_text)
            
            def add_ticket(): # increment number of tickets to buy
                try:
                    for i in range(self.ticket_num - 1):  
                        addbtn = WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                            EC.presence_of_element_located((By.XPATH, "//div[@class='cafe-c-input-number']/a[2]")))
                        addbtn.click()
                except:
                    raise Exception("***错误：票数增加失败***")

            if buybutton_text == "即将开抢" or buybutton_text == "即将开售":
                self.status = 2
                self.driver.refresh()
                print('---尚未开售，刷新等待---')
                continue

            elif buybutton_text == "立即预订":
                add_ticket()
                buybutton.click()
                self.status = 3

            elif buybutton_text == "立即购买":
                add_ticket()
                buybutton.click()
                self.status = 4

            elif buybutton_text == "选座购买":  # TODO: automically select seat
                # buybutton.click()
                self.status = 5
                print("###请自行选择位置和票价###")
                break

            elif buybutton_text == "提交缺货登记":
                print('###抢票失败，请手动提交缺货登记###')
                break

                
    def choose_ticket_2(self):  # choose ticket for type 2, i.e., piao.damai.cn
        self.time_start = time()
        print("###开始进行日期及票价选择###")

        while self.driver.title.find('订单结算页') == -1:  # ticket purchase success
            self.num += 1
            if self.date != 0:
                datepicker = WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "month")))
                datelist = datepicker.find_elements_by_tag_name("span") # find all dates
                # print(len(datelist))
                validlist = []
                for i in range(len(datelist)): # filter all available dates
                    j = datelist[i]
                    k = j.get_attribute('class')
                    if k == 'itm z-show itm-undefined z-sel' \
                    or k == 'itm z-show itm-undefined' \
                    or k == 'itm itm-end z-show itm-undefined':
                        validlist.append(j)
                # print(len(validlist))
                validlist[self.date - 1].click()
            
            session = WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                EC.presence_of_element_located(
                    (By.ID, "performList")))
            # session = self.driver.find_element_by_id('performList')
            session_list = session.find_elements_by_tag_name('li')
            print('Number of available sessions: {}'.format(len(session_list)))
            for i in self.session:  # find session according to priority of sessions
                j = session_list[i - 1]
                k = j.get_attribute('class').strip()
                if k == 'itm' or k == 'itm j_more':  # cannot select session
                    j.find_element_by_tag_name('a').click()
                    break
                elif k == 'itm itm-sel' or k == 'itm j_more itm-sel':  # selected
                    break
                elif k == 'itm itm-oos':  # cannot select session
                    continue
            
            sleep(self.intersect_wait_time)
            
            price = WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                EC.presence_of_element_located(
                    (By.ID, "priceList")))            
            # price = self.driver.find_element_by_id('priceList')
            price_list = price.find_elements_by_tag_name('li')
            print('可选票档数量为：{}'.format(len(price_list)))
            for i in self.price:
                j = price_list[i - 1]
                k = j.get_attribute('class').strip()
                if k == 'itm' or k == 'itm j_more':  # cannot select session
                    j.find_element_by_tag_name('a').click()
                    break
                elif k == 'itm itm-sel' or k == 'itm j_more itm-sel':  # selected
                    break
                elif k == 'itm itm-oos':  # cannot select session
                    continue

            buybutton = None
            try:
                buybutton = self.driver.find_element_by_id('btnBuyNow')  # set buybutton to btnBuyNow
                self.status = 3
            except:
                try:
                    buybutton = self.driver.find_element_by_id('btnBuyNow')
                    self.status = 4
                except:
                    print('###无法立即购买，尝试自行选座###')
                    try:
                        buybutton = self.driver.find_element_by_id('btnXuanzuo')
                        self.status = 5
                        print("###请自行选择位置和票价###")
                        break
                    except:
                        print('---尚未开售，刷新等待---')
                        self.status = 2
                        self.driver.refresh()
                        
            # before incrementing number of tickets, check whether there is a buybutton
            if self.ticket_num > 1 and self.status not in [2, 5]:  # add extra tickets
                add = WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "btn-add")))
                for i in range(self.ticket_num - 1):
                    add.click()
            buybutton.click()
    
    # confirm order for type 1 website
    def check_order_1(self):
        if self.status in [3, 4]:
            print('###开始确认订单###')
            button_xpath = " //*[@id=\"confirmOrder_1\"]/div[%d]/button" # submit xpath of the order
            button_replace = 8
            if self.real_name: # real name information is present
                button_replace = 9
                print('###选择购票人信息###')
                try:
                    list_xpath = "//*[@id=\"confirmOrder_1\"]/div[2]/div[2]/div[1]/div[%d]/label/span[1]/input"
                    for i in range(len(self.real_name))
                        WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                            EC.presence_of_element_located((By.XPATH, list_xpath%(i+1)))).click()
                except Exception as e:
                    print(e)
                    raise Exception("***错误：实名信息框未显示，请检查网络或配置文件***")
            submitbtn = WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                    EC.presence_of_element_located(
                        (By.XPATH, button_xpath%button_replace))) # submit order
            submitbtn.click()  
            
            # pay
            try:
                WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                    EC.title_contains('支付宝'))
                self.status = 6
                print('###成功提交订单,请手动支付###')
                self.time_end = time()
            except Exception as e:
                print('---提交订单失败,请查看问题---')
                print(e)

    
    # confirm order for type 2 website
    def check_order_2(self):
        if self.status in [3, 4]:
            print('###开始确认订单###')
            if self.real_name:
                print('###选择购票人信息###')
                try:
                    tb = WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                        EC.presence_of_element_located(
                        (By.CLASS_NAME, 'from-1')))
                    tb.find_element_by_tag_name('a').click() # click button: choose name
                    
                    sleep(self.intersect_wait_time)
                    lb_list = WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                        EC.presence_of_element_located(
                        (By.XPATH, '/html/body/div[3]/div[3]/div[12]/div/div[2]/div/div[2]/div/table/tbody'))) # locate the popup window
                    lb = lb_list.find_elements_by_tag_name('input')
                    for i in range(len(self.real_name)):
                        lb[self.real_name[i] - 1].find_element_by_tag_name('input').click()  # choose real name
                except Exception as e:
                    print(e)
            input('halt')
            WebDriverWait(self.driver, self.total_wait_time, self.refresh_wait_time).until(
                        EC.presence_of_element_located(
                        (By.ID, 'orderConfirmSubmit'))).click() # submit order
            element = WebDriverWait(self.driver, 10, self.refresh_wait_time).until(EC.title_contains('选择支付方式'))
            element.find_element_by_xpath('/html/body/div[5]/div/div/div/ul/li[2]/a').click()
            element.find_element_by_xpath('/html/body/div[5]/div/div/form/div[2]/ul/li[1]/label/input').click()
            element.find_element_by_id('submit2').click()  # complete payment
            self.status = 6
            print('###成功提交订单,请手动支付###')
            self.time_end = time()

    def finish(self):
        if self.status == 6:  # success
            print("###经过%d轮奋斗，共耗时%f秒，抢票成功！请确认订单信息###" % (self.num, round(self.time_end - self.time_start, 3)))
        else:
            self.driver.quit()


if __name__ == '__main__':

    try:
        with open('./config.json', 'r', encoding='utf-8') as f:
                    config = loads(f.read())
        con = Concert(config['sess'], config['price'], config['date'], config['real_name'], config['nick_name'], config['ticket_num'],
                      config['damai_url'], config['target_url'], config['browser'])
    except Exception as e:
        print(e)
        raise Exception("***错误：初始化失败，请检查配置文件***")
    con.enter_concert()
    if True:
        try:
            if con.type == 1:  # detail.damai.cn
                con.choose_ticket_1()
                con.check_order_1()
            elif con.type == 2:  # piao.damai.cn
                con.choose_ticket_2()
                con.check_order_2()
            # break
        except Exception as e:
            print(e)
            con.driver.get(con.target_url)
    con.finish()
