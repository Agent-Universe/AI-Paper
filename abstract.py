import requests
from bs4 import BeautifulSoup
import json
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 读取本地 JSON 文件
try:
    with open('papers.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f"Successfully loaded papers.json with {len(data)} items")
except Exception as e:
    logger.error(f"Error loading papers.json: {e}")
    exit(1)

# 新建一个空列表，用于存储提取的信息
extracted_data = []

# 遍历每个数据项
for i, item in enumerate(data):
    try:
        logger.info(f"Processing item {i+1}/{len(data)}: {item['Link']}")
        
        # 发送HTTP GET请求 with headers and timeout
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(item['Link'], headers=headers, timeout=30)
        
        # 检查请求是否成功
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题 - with error handling
            title_element = soup.find('h1')
            if title_element:
                title = title_element.get_text().strip()
            else:
                title = "Title not found"
                logger.warning(f"Title not found for {item['Link']}")
            
            # 提取摘要 - try multiple possible elements
            abstract = None
            
            # Try to find abstract in blockquote with class 'abstract'
            abstract_blockquote = soup.find('blockquote', class_='abstract')
            if abstract_blockquote:
                # Remove the "Abstract:" descriptor if present
                descriptor = abstract_blockquote.find('span', class_='descriptor')
                if descriptor:
                    descriptor.extract()
                abstract = abstract_blockquote.get_text().strip()
            
            # If not found, try the original selector
            if not abstract:
                abstract_p = soup.find('p', class_='text-gray-700 dark:text-gray-400')
                if abstract_p:
                    abstract = abstract_p.get_text().strip()
            
            # Try other common abstract containers
            if not abstract:
                abstract_containers = [
                    soup.find('div', class_='abstract'),
                    soup.find('section', class_='abstract'),
                    soup.find('div', id='abstract'),
                    soup.find('p', class_='abstract')
                ]
                
                for container in abstract_containers:
                    if container:
                        abstract = container.get_text().strip()
                        break
            
            # If still not found, look for any paragraph that might be an abstract
            if not abstract:
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    if len(p.get_text()) > 100:  # Assuming abstracts are reasonably long
                        abstract = p.get_text().strip()
                        break
            
            if not abstract:
                abstract = "Abstract not found"
                logger.warning(f"Abstract not found for {item['Link']}")
            
            # 找到包含ArXiv链接的<a>标签
            arxiv_link = soup.find('a', href=lambda href: href and 'arxiv.org/abs' in href)
            arxiv_url = arxiv_link['href'] if arxiv_link else None
            
            # 找到包含PDF链接的<a>标签
            pdf_link = soup.find('a', href=lambda href: href and 'arxiv.org/pdf' in href)
            pdf_url = pdf_link['href'] if pdf_link else None
            
            # 构造新的数据项
            extracted_item = {
                'Title': title,
                'Abstract': abstract,
                'ArXiv Link': arxiv_url,
                'PDF Link': pdf_url,
                'Upvotes': item.get('Upvotes', 0),
                'Original Link': item['Link']
            }
            
            # 将新数据项添加到提取的数据列表中
            extracted_data.append(extracted_item)
            logger.info(f"Successfully extracted data for item {i+1}")
        else:
            logger.warning(f"Failed to fetch {item['Link']}, status code: {response.status_code}")
            # Add item with error information
            extracted_data.append({
                'Title': 'Error fetching page',
                'Abstract': f'HTTP Error: {response.status_code}',
                'ArXiv Link': None,
                'PDF Link': None,
                'Upvotes': item.get('Upvotes', 0),
                'Original Link': item['Link']
            })
        
        # Add a small delay to avoid overwhelming the server
        time.sleep(1)
        
    except Exception as e:
        logger.error(f"Error processing item {i+1}: {e}")
        # Add item with error information
        extracted_data.append({
            'Title': 'Error processing item',
            'Abstract': f'Error: {str(e)}',
            'ArXiv Link': None,
            'PDF Link': None,
            'Upvotes': item.get('Upvotes', 0),
            'Original Link': item['Link'] if 'Link' in item else 'Unknown'
        })

# 将提取的数据保存到新的 JSON 文件中
try:
    with open('extracted_data.json', 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)
    logger.info(f"Successfully saved extracted_data.json with {len(extracted_data)} items")
except Exception as e:
    logger.error(f"Error saving extracted_data.json: {e}")

# Print summary
success_count = sum(1 for item in extracted_data if 'Error' not in item['Title'])
logger.info(f"Completed processing {len(data)} items. Success: {success_count}, Failed: {len(data) - success_count}")