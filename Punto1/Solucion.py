from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time

client = MongoClient("mongodb://"something here"")
db = client["MercadoLibre"]
collection = db["Productos"] 

service = Service('/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service)
wait = WebDriverWait(driver, 10)


def buscar_producto(palabra_clave, paginas):
    driver.get('https://www.mercadolibre.com.co/')
    productos_Amongo=[]
    # Buscar producto
    search_box = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cb1-edit"]')))
    search_box.clear()
    search_box.send_keys(palabra_clave)
    search_box.send_keys(Keys.ENTER)

    paginacion=49
    i=1
    while i< (paginas+1):
        time.sleep(5)  
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li.ui-search-layout__item')))
        
        # Parsear con BeautifulSoup
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        # Selecciona todos los items
        items = soup.select('li.ui-search-layout__item')
        for item in items:
            link = item.select_one('a.poly-component__title')
            if link:
                titulo = link.text.strip()
                href = link.get('href')
                price= item.select_one('span.andes-money-amount__fraction')
                print('Título:', titulo)
                print('Precio:', int(price.text.strip().replace('.', '')) if price else 0)
                print('URL:', href)
                producto={'titulo': titulo, 'precio': int(price.text.strip().replace('.', '')) if price else 0, 'url': href, 'categoria': palabra_clave}
                productos_Amongo.append(producto)


        # Ir a la siguiente página
        print(f"Página {i} de {paginas}")
        i+=1
       
        if i< (paginas+1):
            if(palabra_clave=='bicicleta'):
                driver.get(f'https://listado.mercadolibre.com.co/deportes-fitness/ciclismo/bicicleta_Desde_{paginacion}_NoIndex_True')
            else:
                driver.get(f'https://listado.mercadolibre.com.co/computacion/computador_Desde_{paginacion}_NoIndex_True')
            paginacion+=48

    # Inserta documentos
    result = collection.insert_many(productos_Amongo)
    print("IDs insertados:", result.inserted_ids)


palabras=['computador', 'bicicleta']
for palabra in palabras:
    buscar_producto(palabra, 5)
driver.quit()


# Consultas y Resultados
print("¿Cuántos productos de cada categoría (computador / bicicleta) se extrajeron?")

pipeline = [
    {"$group": {"_id": "$categoria", "total": {"$sum": 1}}}
]
resultado = {doc["_id"]: doc["total"] for doc in collection.aggregate(pipeline)}
print(resultado)

print("¿Cuál es el producto más barato de cada categoría?")

pipeline = [
    {"$sort": {"precio": 1}}, 
    {"$group": {"_id": "$categoria", 
                "mas_barato": {"$first": "$titulo"}, 
                "precio": {"$first": "$precio"}}}
]
resultado = {doc["_id"]: {"producto": doc["mas_barato"], "precio": doc["precio"]} 
             for doc in collection.aggregate(pipeline)}
print(resultado)

print("¿Cuál es el precio promedio de los productos en cada categoría?")

pipeline = [
    {"$group": {"_id": "$categoria", "precio_promedio": {"$avg": "$precio"}}}
]
resultado = {doc["_id"]: doc["precio_promedio"] for doc in collection.aggregate(pipeline)}
print(resultado)

print("Lista de todos los productos con precio mayor a 1.000.000 COP")

resultado = [doc["titulo"] for doc in collection.find({"precio": {"$gt": 1000000}})]
print(resultado)
