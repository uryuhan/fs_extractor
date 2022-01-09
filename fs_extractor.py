import re
import math 
import time
import pandas as pd
import numpy as np
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def obtain_stock_code_list(target_file):
    code_list = []
    with open(target_file, "r") as f:
        for line in f.readlines():
            line = line.strip("\n")
            code_list.append(line)
    return code_list

def open_browser(stock_code):
    browser_option = Options()
    #browser_option.add_argument("--headless")
    browser = webdriver.Chrome(ChromeDriverManager().install(), options=browser_option)
    browser.get('https://emweb.securities.eastmoney.com/PC_HSF10/FinanceAnalysis/Index?type=web&code=' + stock_code)
    return browser

def format_data(string):
    num = re.findall(r"\d+\.?\d*", string)

    num += re.findall(r"[\u4e00-\u9fa5]+", string)
    if len(num) > 2:
        num[0] = '-'.join(num)
    elif len(num) == 2:
        if '亿' == num[-1]:
            num[0] =float(num[0]) * (10**4)
        elif '万亿' == num[-1]:
            num[0] = float(num[0]) * (10 **8)
    elif num ==[]:
        num.append(0)
    return num[0]
        
def grasp_data(browser,data_id):
    elem = browser.find_element(By.ID, data_id).text
    td = elem.split("\n")
    row_name = []
    lst = []
    for rows in td:      
        rows = rows.split(' ')
        row_name.append(rows[0])
        
        for index in range(len(rows)):
            
            rows[index] = format_data(rows[index])
            
        lst.append(rows)
    return_dict = {row[0]:row[1:] for row in lst}
    return return_dict

def click_next_page(browser, sheet_type):
    click = WebDriverWait(browser, 1).until(EC.presence_of_element_located((By.XPATH, '//*[@id="'+sheet_type +'_next"]')))
    print(click.get_attribute("style"))
    if "inline" in click.get_attribute("style"):
        click.click()
        return 0
    else:
        print("Here comes to the last page!")
        return 1
    
def make_perfect_rows(row_1, row_2):
    row = row_1
    for index in range(len(row_2)):
        if row_1 == []:
            row = row_2
        if row_2[index] not in row:
            anchor = row.index(row_2[index-1])
            row_1.insert(anchor, row_2[index])
    return row

def rearrange_rows(table,row):
    try:
        row_len = len(table[list(table)[0]])    
    except IndexError:
        row_len = 0
    return table.get(row) or [0 for _ in range(row_len)]

def wash_data(df):
    header_row = 0
    df.columns = df.iloc[header_row]
    df = df.drop(df.index[header_row])
    new_df = df.T.drop_duplicates().T
    return new_df
    
def generate_sheet(browser, stock_code, sheet_type, sheet_length):
    sheet_start_time = time.time()
    output_dict = {}
    row_lst = []
    for i in range(math.ceil(sheet_length/5)):
        page_start_time = time.time()    
        temp_dict =grasp_data(browser, data_id=str("report_" + sheet_type))       
        row_lst_2 = list([x for x in temp_dict] )
        row_lst = make_perfect_rows(row_lst, row_lst_2)
        output_dict = {
            row_lst[index]: rearrange_rows(output_dict,row_lst[index]) + rearrange_rows(temp_dict,row_lst[index])
            for index in range(len(row_lst))
        }
        if click_next_page(browser, sheet_type=sheet_type):
            break
        time.sleep(1)

        page_end_time = time.time()

        print("time for grasping "+ sheet_type +" page "+ str(i+1) +": ", page_end_time - page_start_time)
    output_dataframe = pd.DataFrame(output_dict).T
    output_dataframe = wash_data(output_dataframe)
    
    try:
        writer = pd.ExcelWriter("financial_statement\\"+stock_code + ".xlsx", mode='a', engine='openpyxl')
    except FileNotFoundError:
        writer = pd.ExcelWriter("financial_statement\\"+stock_code + ".xlsx", engine='openpyxl')  

    
    output_dataframe.to_excel(writer, sheet_name=sheet_type)
    writer.save()
    
    sheet_end_time = time.time()
    print("time for grasping " + stock_code +' '+sheet_type + " sheet: ", sheet_end_time - sheet_start_time)
    

if __name__ == "__main__":
    begin_time = time.time()
    code_list = obtain_stock_code_list(target_file= "stock_code_list.txt")
    print(code_list)
    all_type = ["zcfzb", "lrb", "xjllb"]
    for stock in code_list:
        browser = open_browser(stock)
        for sheet_type in  all_type:
            generate_sheet(browser, stock, sheet_type, sheet_length=2)
    end_time = time.time()
    print("total time: ", end_time - begin_time)
    
