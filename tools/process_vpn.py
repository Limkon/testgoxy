import os
import re
import sys
import time
import datetime
import requests
import concurrent.futures
import base64
import multiprocessing

from bs4 import BeautifulSoup


def extract_content(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')

        selectors = [
            '#app',
            '.content',
            'div',
            '.my-class',
            '#my-id',
            '[name="my-name"]',
            '.my-parent .my-child',
        ]

        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text()
                    return content
            except Exception as e:
                pass

        content = soup.get_text()
        return content
    else:
        raise Exception(f"Failed to fetch content from URL: {url}")


def save_content(content, output_dir, url):
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    url_without_protocol = re.sub(r'^(https?://)', '', url)
    url_without_protocol = re.sub(r'[:?<>|\"*\r\n/]', '_', url_without_protocol)
    url_without_protocol = url_without_protocol[:20]
    file_name = os.path.join(output_dir, url_without_protocol + "_" + date + ".txt")

    content_lines = content.splitlines()
    non_empty_lines = [line for line in content_lines if line.strip()]
    cleaned_content = '\n'.join(non_empty_lines)

    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(cleaned_content)
    print(f"网站 {url} 内容已保存至文件：{file_name}")


def process_url(url, output_dir, rest_file, urls_file):
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(extract_content, url)
            content = future.result(timeout=600)

        if content:
            if is_base64_encoded(content):
                decoded_content = base64.b64decode(content).decode('utf-8')
                append_to_file(rest_file, decoded_content)
            elif has_specific_format(content):
                append_to_file(rest_file, content)
            else:
                delete_file(url, output_dir)
                remove_url(url, urls_file)
            return f"处理 {url} 成功"
        else:
            return f"处理 {url} 失败：无法提取内容"
    except concurrent.futures.TimeoutError:
        return f"处理 {url} 超时"
    except Exception as e:
        return f"处理 {url} 失败：{str(e)}"


def is_base64_encoded(content):
    try:
        content.encode('ascii')
        base64.b64decode(content)
        return True
    except (UnicodeEncodeError, base64.binascii.Error):
        return False


def has_specific_format(content):
    formats = ['vmess://', 'trojan://', 'clash://', 'ss://', 'vlss://']
    return any(format in content for format in formats)


def append_to_file(file_path, content):
    with open(file_path, 'a', encoding='utf-8') as file:
        file.write(content + '\n')


def delete_file(url, output_dir):
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    url_without_protocol = re.sub(r'^(https?://)', '', url)
    url_without_protocol = re.sub(r'[:?<>|\"*\r\n/]', '_', url_without_protocol)
    url_without_protocol = url_without_protocol[:20]
    file_name = os.path.join(output_dir, url_without_protocol + "_" + date + ".txt")

    if os.path.exists(file_name):
        os.remove(file_name)
        print(f"删除文件：{file_name}")


def remove_url(url, urls_file):
    with open(urls_file, 'r', encoding='utf-8') as file:
        urls = [line.strip() for line in file]

    urls = [u for u in urls if u != url]

    with open(urls_file, 'w', encoding='utf-8') as file:
        file.write('\n'.join(urls))


def process_urls(urls, output_dir, num_threads, rest_file, urls_file):
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(process_url, url, output_dir, rest_file, urls_file) for url in urls]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            print(result)


def main():
    if len(sys.argv) != 5:
        print("请提供要抓取的 URL 列表文件名、保存提取内容的目录、线程数和 REST 文件的路径")
        print("示例: python extract_urls.py urls.txt data 10 ./share/rest.txt")
        sys.exit(1)

    urls_file = sys.argv[1]
    output_dir = sys.argv[2]
    num_threads = int(sys.argv[3])
    rest_file = sys.argv[4]

    with open(urls_file, 'r', encoding='utf-8') as file:
        urls = [line.strip() for line in file]

    process_urls(urls, output_dir, num_threads, rest_file, urls_file)

    print('所有网站内容保存完成！')


if __name__ == '__main__':
    main()
