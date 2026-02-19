# Data is sourced from Best Buy Canada. The data is collected using web scraping techniques

## Laptops: 
Data is retrieved from page: https://www.bestbuy.ca/en-ca/category/laptops-macbooks/20352?path=category%253AComputers%2B%2526%2BTablets%253Bcategory%253ALaptops%2B%2526%2BMacBooks%253Bcustom0productcondition%253ABrand%2BNew&sort=highestRated
1. Page 1: laptop_1.json
2. Page 2: laptop_2.json


#### Added category field to better search and filter products in Pinecone. The category field is an array of strings that contains the category and subcategory of the product. For example, for laptops, the category field would be:
"category": ["computer", "laptop"]


## Data fields are selected and saved into Pinecone:
1. sku
2. name
3. shortDescription
4. customerRating
5. productUrl
6. regularPrice
7. salePrice
8. thumbnailImage
9. categoryName
10. highResImage